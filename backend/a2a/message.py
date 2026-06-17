# a2a/message.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class A2AMessageType(str, Enum):
    TASK_REQUEST = "task_request"
    TASK_RESULT = "task_result"
    TASK_PROGRESS = "task_progress"
    TASK_CANCEL = "task_cancel"
    QUERY = "query"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    MULTICAST = "multicast"
    HEARTBEAT = "heartbeat"
    HANDOFF = "handoff"
    DELEGATE = "delegate"
    NEGOTIATE = "negotiate"
    ACK = "ack"
    ERROR = "error"


class A2AMessagePriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class A2AMessageStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass(slots=True)
class A2AMessage:
    message_id: str
    message_type: A2AMessageType
    sender_id: str
    sender_type: str
    recipient_id: str | None
    recipient_type: str | None
    content: str
    payload: dict[str, Any] = field(default_factory=dict)
    priority: A2AMessagePriority = A2AMessagePriority.NORMAL
    status: A2AMessageStatus = A2AMessageStatus.PENDING
    correlation_id: str | None = None
    reply_to: str | None = None
    conversation_id: str | None = None
    ttl: int = 300
    timestamp: float = field(default_factory=time.time)
    delivered_at: float | None = None
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

    @classmethod
    def create(
        cls,
        message_type: A2AMessageType,
        sender_id: str,
        content: str,
        *,
        sender_type: str = "agent",
        recipient_id: str | None = None,
        recipient_type: str | None = None,
        payload: dict[str, Any] | None = None,
        priority: A2AMessagePriority = A2AMessagePriority.NORMAL,
        correlation_id: str | None = None,
        conversation_id: str | None = None,
        ttl: int = 300,
        metadata: dict[str, Any] | None = None,
    ) -> "A2AMessage":
        return cls(
            message_id=uuid.uuid4().hex,
            message_type=message_type,
            sender_id=sender_id,
            sender_type=sender_type,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            content=content,
            payload=payload or {},
            priority=priority,
            status=A2AMessageStatus.PENDING,
            correlation_id=correlation_id,
            conversation_id=conversation_id or uuid.uuid4().hex,
            ttl=ttl,
            metadata=metadata or {},
        )

    @classmethod
    def task_request(
        cls,
        sender_id: str,
        recipient_id: str,
        task: str,
        payload: dict[str, Any] | None = None,
        priority: A2AMessagePriority = A2AMessagePriority.NORMAL,
    ) -> "A2AMessage":
        return cls.create(
            A2AMessageType.TASK_REQUEST,
            sender_id=sender_id,
            content=task,
            recipient_id=recipient_id,
            payload=payload or {},
            priority=priority,
        )

    @classmethod
    def task_result(
        cls,
        sender_id: str,
        recipient_id: str,
        result: str,
        correlation_id: str,
        payload: dict[str, Any] | None = None,
    ) -> "A2AMessage":
        return cls.create(
            A2AMessageType.TASK_RESULT,
            sender_id=sender_id,
            content=result,
            recipient_id=recipient_id,
            correlation_id=correlation_id,
            payload=payload or {},
        )

    @classmethod
    def broadcast(
        cls,
        sender_id: str,
        content: str,
        payload: dict[str, Any] | None = None,
    ) -> "A2AMessage":
        return cls.create(
            A2AMessageType.BROADCAST,
            sender_id=sender_id,
            content=content,
            payload=payload or {},
        )

    @classmethod
    def heartbeat(cls, sender_id: str, capabilities: list[str] | None = None) -> "A2AMessage":
        return cls.create(
            A2AMessageType.HEARTBEAT,
            sender_id=sender_id,
            content="heartbeat",
            payload={"capabilities": capabilities or [], "timestamp": time.time()},
            ttl=60,
        )

    def is_expired(self) -> bool:
        return (time.time() - self.timestamp) > self.ttl

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def create_reply(
        self,
        sender_id: str,
        content: str,
        message_type: A2AMessageType = A2AMessageType.RESPONSE,
        payload: dict[str, Any] | None = None,
    ) -> "A2AMessage":
        return A2AMessage.create(
            message_type=message_type,
            sender_id=sender_id,
            content=content,
            recipient_id=self.sender_id,
            correlation_id=self.message_id,
            conversation_id=self.conversation_id,
            payload=payload or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "sender_type": self.sender_type,
            "recipient_id": self.recipient_id,
            "recipient_type": self.recipient_type,
            "content": self.content,
            "payload": self.payload,
            "priority": self.priority.value,
            "status": self.status.value,
            "correlation_id": self.correlation_id,
            "reply_to": self.reply_to,
            "conversation_id": self.conversation_id,
            "ttl": self.ttl,
            "timestamp": self.timestamp,
            "delivered_at": self.delivered_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "A2AMessage":
        return cls(
            message_id=data["message_id"],
            message_type=A2AMessageType(data["message_type"]),
            sender_id=data["sender_id"],
            sender_type=data.get("sender_type", "agent"),
            recipient_id=data.get("recipient_id"),
            recipient_type=data.get("recipient_type"),
            content=data["content"],
            payload=data.get("payload", {}),
            priority=A2AMessagePriority(data.get("priority", 2)),
            status=A2AMessageStatus(data.get("status", "pending")),
            correlation_id=data.get("correlation_id"),
            reply_to=data.get("reply_to"),
            conversation_id=data.get("conversation_id"),
            ttl=data.get("ttl", 300),
            timestamp=data.get("timestamp", time.time()),
            delivered_at=data.get("delivered_at"),
            completed_at=data.get("completed_at"),
            metadata=data.get("metadata", {}),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )
    