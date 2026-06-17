# a2a/protocol.py
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from a2a.message import A2AMessage, A2AMessageStatus, A2AMessageType


class ProtocolVersion(str, Enum):
    V1 = "1.0"


class CommunicationPattern(str, Enum):
    DIRECT = "direct"
    BROADCAST = "broadcast"
    MULTICAST = "multicast"
    QUEUE = "queue"
    PIPELINE = "pipeline"
    ROUND_ROBIN = "round_robin"
    PUBLISH_SUBSCRIBE = "publish_subscribe"


@dataclass(slots=True, frozen=True)
class ProtocolHandshake:
    agent_id: str
    agent_type: str
    capabilities: list[str]
    supported_patterns: list[str]
    protocol_version: str = ProtocolVersion.V1.value
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "supported_patterns": self.supported_patterns,
            "protocol_version": self.protocol_version,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class A2AProtocol:
    VERSION = ProtocolVersion.V1

    @staticmethod
    def create_ack(message: A2AMessage, sender_id: str) -> A2AMessage:
        return message.create_reply(
            sender_id=sender_id,
            content="ack",
            message_type=A2AMessageType.ACK,
            payload={"acked_message_id": message.message_id, "timestamp": time.time()},
        )

    @staticmethod
    def create_error(
        message: A2AMessage, sender_id: str, error: str, error_code: int = 500
    ) -> A2AMessage:
        return message.create_reply(
            sender_id=sender_id,
            content=error,
            message_type=A2AMessageType.ERROR,
            payload={"error": error, "error_code": error_code, "original_message_id": message.message_id},
        )

    @staticmethod
    def create_progress(
        message: A2AMessage, sender_id: str, progress: float, status_text: str
    ) -> A2AMessage:
        return message.create_reply(
            sender_id=sender_id,
            content=status_text,
            message_type=A2AMessageType.TASK_PROGRESS,
            payload={"progress": min(max(progress, 0.0), 1.0), "status": status_text},
        )

    @staticmethod
    def create_handoff(
        original: A2AMessage,
        sender_id: str,
        target_agent_id: str,
        reason: str,
        carry_context: bool = True,
    ) -> A2AMessage:
        payload = {
            "original_sender": original.sender_id,
            "reason": reason,
            "original_task": original.content,
        }
        if carry_context:
            payload["original_payload"] = original.payload
        return A2AMessage.create(
            A2AMessageType.HANDOFF,
            sender_id=sender_id,
            content=original.content,
            recipient_id=target_agent_id,
            correlation_id=original.message_id,
            conversation_id=original.conversation_id,
            payload=payload,
        )

    @staticmethod
    def mark_delivered(message: A2AMessage) -> A2AMessage:
        message.status = A2AMessageStatus.DELIVERED
        message.delivered_at = time.time()
        return message

    @staticmethod
    def mark_completed(message: A2AMessage) -> A2AMessage:
        message.status = A2AMessageStatus.COMPLETED
        message.completed_at = time.time()
        return message
    