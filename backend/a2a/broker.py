# a2a/broker.py
from __future__ import annotations

import asyncio
import time
from typing import Any

from redis.asyncio import Redis

from a2a.message import A2AMessage, A2AMessageType
from a2a.protocol import A2AProtocol
from a2a.registry import A2ARegistry, AgentRecord
from a2a.transport import A2ATransport
from a2a.validator import validate_message
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.broker")


class A2ABroker:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.transport = A2ATransport(redis)
        self.registry = A2ARegistry(redis)

    async def send(self, message: A2AMessage) -> bool:
        result = validate_message(message)
        if not result.valid:
            logger.warning("a2a_message_invalid", errors=result.errors, message_id=message.message_id)
            return False
        if message.recipient_id is not None:
            recipient = await self.registry.get(message.recipient_id)
            if recipient is None:
                logger.warning("a2a_recipient_not_found", recipient_id=message.recipient_id)
        return await self.transport.send(message)

    async def send_to_type(
        self,
        message: A2AMessage,
        target_type: str,
        strategy: str = "least_loaded",
    ) -> bool:
        if strategy == "least_loaded":
            target = await self.registry.find_least_loaded(target_type)
        else:
            targets = await self.registry.find_by_type(target_type)
            target = targets[0] if targets else None

        if target is None:
            logger.warning("a2a_no_agent_of_type", target_type=target_type)
            return False

        message.recipient_id = target.agent_id
        return await self.send(message)

    async def send_with_capability(
        self, message: A2AMessage, capability: str
    ) -> bool:
        targets = await self.registry.find_by_capability(capability)
        if not targets:
            logger.warning("a2a_no_agent_with_capability", capability=capability)
            return False
        best = min(targets, key=lambda r: r.load_factor)
        message.recipient_id = best.agent_id
        return await self.send(message)

    async def request_response(
        self,
        message: A2AMessage,
        timeout: float = 30.0,
    ) -> A2AMessage | None:
        sent = await self.send(message)
        if not sent:
            return None

        sender_id = message.sender_id
        deadline = asyncio.get_event_loop().time() + timeout

        while asyncio.get_event_loop().time() < deadline:
            inbox = await self.transport.receive(sender_id, max_messages=5)
            for msg in inbox:
                if msg.correlation_id == message.message_id:
                    return msg
            await asyncio.sleep(0.2)

        logger.warning("a2a_request_timeout", message_id=message.message_id, timeout=timeout)
        return None

    async def fanout(
        self,
        message: A2AMessage,
        agent_ids: list[str],
    ) -> dict[str, bool]:
        results: dict[str, bool] = {}
        tasks: list[asyncio.Task[bool]] = []
        for agent_id in agent_ids:
            msg_copy = A2AMessage.from_dict({**message.to_dict(), "recipient_id": agent_id, "message_id": __import__("uuid").uuid4().hex})
            tasks.append(asyncio.create_task(self.send(msg_copy)))
        send_results = await asyncio.gather(*tasks, return_exceptions=True)
        for agent_id, result in zip(agent_ids, send_results):
            results[agent_id] = result is True
        return results
    