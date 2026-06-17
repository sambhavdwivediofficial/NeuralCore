# agents/communication/router.py
from __future__ import annotations

import uuid
from typing import Any

from agents.communication.broker import AgentMessageBroker
from agents.communication.channels import ChannelRegistry, ChannelType
from agents.communication.messages import AgentMessage, MessageType
from agents.communication.protocols import AgentProtocol, ProtocolType
from monitoring.logging import get_logger

logger = get_logger("neuralcore.agents.router")


class AgentRouter:
    def __init__(self, broker: AgentMessageBroker, channel_registry: ChannelRegistry) -> None:
        self.broker = broker
        self.channels = channel_registry

    async def route(
        self,
        message: AgentMessage,
        protocol: ProtocolType = ProtocolType.FIRE_AND_FORGET,
    ) -> bool:
        valid, reason = AgentProtocol.validate_message(message, protocol)
        if not valid:
            logger.warning("message_routing_rejected", reason=reason, message_id=message.message_id)
            return False

        if message.message_type == MessageType.BROADCAST:
            await self.broker.broadcast(message)
            logger.debug("message_broadcast", sender=message.sender_id)
            return True

        if message.message_type == MessageType.HANDOFF:
            ack = AgentProtocol.create_ack(message, message.sender_id)
            await self.broker.send(ack)

        return await self.broker.send(message)

    async def send_task(
        self,
        sender_id: str,
        recipient_id: str,
        task: str,
        payload: dict[str, Any] | None = None,
        wait_for_reply: bool = False,
        timeout: float = 30.0,
    ) -> AgentMessage | None:
        message = AgentMessage.create_task(
            sender_id=sender_id,
            recipient_id=recipient_id,
            task_description=task,
            payload=payload or {},
        )
        await self.route(message, ProtocolType.REQUEST_RESPONSE if wait_for_reply else ProtocolType.FIRE_AND_FORGET)

        if not wait_for_reply:
            return None

        import asyncio
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            messages = await self.broker.receive(sender_id)
            for msg in messages:
                if msg.correlation_id == message.message_id:
                    return msg
            await asyncio.sleep(0.2)
        return None

    async def broadcast_to_group(
        self, sender_id: str, channel_id: str, content: str, payload: dict[str, Any] | None = None
    ) -> None:
        channel = self.channels.get(channel_id)
        if channel is None:
            logger.warning("channel_not_found", channel_id=channel_id)
            return
        msg = AgentMessage.create_broadcast(sender_id=sender_id, content=content, payload=payload or {})
        await channel.publish(msg)
