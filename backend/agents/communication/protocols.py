# agents/communication/protocols.py
from __future__ import annotations

from enum import Enum
from typing import Any

from agents.communication.messages import AgentMessage, MessageType


class ProtocolType(str, Enum):
    REQUEST_RESPONSE = "request_response"
    FIRE_AND_FORGET = "fire_and_forget"
    PUBLISH_SUBSCRIBE = "publish_subscribe"
    PIPELINE = "pipeline"
    AUCTION = "auction"


class AgentProtocol:
    @staticmethod
    def validate_message(message: AgentMessage, protocol: ProtocolType) -> tuple[bool, str]:
        if message.is_expired():
            return False, f"Message {message.message_id} has expired (TTL={message.ttl}s)"

        if protocol == ProtocolType.REQUEST_RESPONSE:
            if message.message_type not in (MessageType.QUERY, MessageType.TASK):
                return False, "Request-response protocol requires QUERY or TASK message type"
            if message.recipient_id is None:
                return False, "Request-response protocol requires a specific recipient"

        if protocol == ProtocolType.PUBLISH_SUBSCRIBE:
            if message.message_type != MessageType.BROADCAST:
                return False, "Pub-sub protocol requires BROADCAST message type"

        return True, ""

    @staticmethod
    def create_ack(original: AgentMessage, sender_id: str) -> AgentMessage:
        from agents.communication.messages import MessagePriority
        return AgentMessage(
            message_id=__import__("uuid").uuid4().hex,
            message_type=MessageType.RESPONSE,
            sender_id=sender_id,
            recipient_id=original.sender_id,
            content="acknowledged",
            correlation_id=original.message_id,
            priority=MessagePriority.HIGH,
        )

    @staticmethod
    def create_handoff(
        sender_id: str,
        target_agent_id: str,
        task: str,
        context: dict[str, Any],
        original_message_id: str | None = None,
    ) -> AgentMessage:
        from agents.communication.messages import MessagePriority
        return AgentMessage(
            message_id=__import__("uuid").uuid4().hex,
            message_type=MessageType.HANDOFF,
            sender_id=sender_id,
            recipient_id=target_agent_id,
            content=task,
            payload=context,
            priority=MessagePriority.HIGH,
            correlation_id=original_message_id,
        )
    