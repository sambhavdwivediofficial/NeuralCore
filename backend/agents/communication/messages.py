# agents/communication/messages.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    HANDOFF = "handoff"


class MessagePriority(int, Enum):
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass(slots=True)
class AgentMessage:
    message_id: str
    message_type: MessageType
    sender_id: str
    recipient_id: str | None
    content: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    correlation_id: str | None = None
    reply_to: str | None = None
    timestamp: float = field(default_factory=time.time)
    ttl: int = 300
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create_task(
        cls,
        sender_id: str,
        recipient_id: str,
        task_description: str,
        payload: dict[str, Any] | None = None,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> "AgentMessage":
        return cls(
            message_id=uuid.uuid4().hex,
            message_type=MessageType.TASK,
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=task_description,
            payload=payload or {},
            priority=priority,
        )

    @classmethod
    def create_result(
        cls,
        sender_id: str,
        recipient_id: str,
        result: str,
        correlation_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> "AgentMessage":
        return cls(
            message_id=uuid.uuid4().hex,
            message_type=MessageType.RESULT,
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=result,
            payload=payload or {},
            correlation_id=correlation_id,
        )

    @classmethod
    def create_broadcast(
        cls, sender_id: str, content: str, payload: dict[str, Any] | None = None
    ) -> "AgentMessage":
        return cls(
            message_id=uuid.uuid4().hex,
            message_type=MessageType.BROADCAST,
            sender_id=sender_id,
            recipient_id=None,
            content=content,
            payload=payload or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "payload": self.payload,
            "priority": self.priority.value,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "timestamp": self.timestamp,
            "ttl": self.ttl,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMessage":
        return cls(
            message_id=data["message_id"],
            message_type=MessageType(data["message_type"]),
            sender_id=data["sender_id"],
            recipient_id=data.get("recipient_id"),
            content=data["content"],
            payload=data.get("payload", {}),
            priority=MessagePriority(data.get("priority", 2)),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            timestamp=data.get("timestamp", time.time()),
            ttl=data.get("ttl", 300),
            metadata=data.get("metadata", {}),
        )

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl
    