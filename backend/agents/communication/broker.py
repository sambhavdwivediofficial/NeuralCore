# agents/communication/broker.py
from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import defaultdict
from typing import Any, Callable, Coroutine

from redis.asyncio import Redis

from agents.communication.messages import AgentMessage, MessagePriority
from monitoring.logging import get_logger

logger = get_logger("neuralcore.agents.broker")

MessageHandler = Callable[[AgentMessage], Coroutine[Any, Any, None]]

_BROKER_PREFIX = "a2a"
_INBOX_TTL = 3600


class AgentMessageBroker:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self._local_handlers: dict[str, list[MessageHandler]] = defaultdict(list)
        self._broadcast_handlers: list[MessageHandler] = []
        self._polling_tasks: dict[str, asyncio.Task[Any]] = {}
        self._running = False

    def _inbox_key(self, agent_id: str) -> str:
        return f"{_BROKER_PREFIX}:inbox:{agent_id}"

    def _broadcast_key(self) -> str:
        return f"{_BROKER_PREFIX}:broadcast"

    async def send(self, message: AgentMessage) -> bool:
        if message.recipient_id is None:
            return await self.broadcast(message)
        inbox = self._inbox_key(message.recipient_id)
        data = json.dumps(message.to_dict())
        score = time.time() - message.priority.value
        await self.redis.zadd(inbox, {data: score})
        await self.redis.expire(inbox, _INBOX_TTL)
        logger.debug("message_sent", from_id=message.sender_id, to_id=message.recipient_id, type=message.message_type.value)
        return True

    async def broadcast(self, message: AgentMessage) -> bool:
        data = json.dumps(message.to_dict())
        score = time.time()
        await self.redis.zadd(self._broadcast_key(), {data: score})
        await self.redis.expire(self._broadcast_key(), _INBOX_TTL)
        return True

    async def receive(self, agent_id: str, max_messages: int = 10) -> list[AgentMessage]:
        inbox = self._inbox_key(agent_id)
        now = time.time()
        raw_items = await self.redis.zrangebyscore(inbox, "-inf", now, start=0, num=max_messages)
        if raw_items:
            await self.redis.zrem(inbox, *raw_items)

        messages: list[AgentMessage] = []
        for raw in raw_items:
            try:
                msg = AgentMessage.from_dict(json.loads(raw))
                if not msg.is_expired():
                    messages.append(msg)
            except (json.JSONDecodeError, KeyError):
                continue
        return messages

    def register_handler(self, agent_id: str, handler: MessageHandler) -> None:
        self._local_handlers[agent_id].append(handler)

    def register_broadcast_handler(self, handler: MessageHandler) -> None:
        self._broadcast_handlers.append(handler)

    async def start_polling(self, agent_id: str, interval: float = 0.5) -> None:
        if agent_id in self._polling_tasks:
            return
        self._polling_tasks[agent_id] = asyncio.create_task(
            self._poll_loop(agent_id, interval)
        )

    async def stop_polling(self, agent_id: str) -> None:
        task = self._polling_tasks.pop(agent_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self, agent_id: str, interval: float) -> None:
        while True:
            messages = await self.receive(agent_id)
            for msg in messages:
                for handler in self._local_handlers.get(agent_id, []):
                    try:
                        await handler(msg)
                    except Exception as exc:
                        logger.warning("message_handler_error", agent_id=agent_id, error=str(exc))
            await asyncio.sleep(interval)
