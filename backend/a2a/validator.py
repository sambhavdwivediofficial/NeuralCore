# a2a/validator.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from a2a.message import A2AMessage, A2AMessageType

_AGENT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{3,128}$")
_MAX_CONTENT_LENGTH = 65536
_MAX_PAYLOAD_KEYS = 64
_ALLOWED_BROADCAST_TYPES = {A2AMessageType.BROADCAST, A2AMessageType.HEARTBEAT}


@dataclass(slots=True, frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]

    @classmethod
    def ok(cls) -> "ValidationResult":
        return cls(valid=True, errors=[])

    @classmethod
    def fail(cls, *errors: str) -> "ValidationResult":
        return cls(valid=False, errors=list(errors))


def validate_agent_id(agent_id: str) -> bool:
    return bool(_AGENT_ID_PATTERN.match(agent_id))


def validate_message(message: A2AMessage) -> ValidationResult:
    errors: list[str] = []

    if not validate_agent_id(message.sender_id):
        errors.append(f"Invalid sender_id format: '{message.sender_id}'")

    if message.recipient_id is not None and not validate_agent_id(message.recipient_id):
        errors.append(f"Invalid recipient_id format: '{message.recipient_id}'")

    if message.recipient_id is None and message.message_type not in _ALLOWED_BROADCAST_TYPES:
        errors.append(f"recipient_id is required for message type '{message.message_type.value}'")

    if not message.content and message.message_type != A2AMessageType.HEARTBEAT:
        errors.append("content cannot be empty")

    if len(message.content) > _MAX_CONTENT_LENGTH:
        errors.append(f"content exceeds max length {_MAX_CONTENT_LENGTH}")

    if len(message.payload) > _MAX_PAYLOAD_KEYS:
        errors.append(f"payload has too many keys (max {_MAX_PAYLOAD_KEYS})")

    if message.is_expired():
        errors.append(f"message '{message.message_id}' has expired (TTL={message.ttl}s)")

    if not (0 <= message.priority.value <= 4):
        errors.append(f"invalid priority value: {message.priority.value}")

    if not errors:
        return ValidationResult.ok()
    return ValidationResult.fail(*errors)


def validate_task_payload(payload: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    if "task_id" in payload and not isinstance(payload["task_id"], str):
        errors.append("task_id must be a string")
    if "timeout" in payload and not isinstance(payload["timeout"], (int, float)):
        errors.append("timeout must be a number")
    return ValidationResult.ok() if not errors else ValidationResult.fail(*errors)
