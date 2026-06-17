# a2a/security/authorization.py
from __future__ import annotations

from enum import Enum
from typing import Any

from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.security.authz")


class A2APermission(str, Enum):
    SEND_TASK = "a2a:send_task"
    RECEIVE_TASK = "a2a:receive_task"
    BROADCAST = "a2a:broadcast"
    MULTICAST = "a2a:multicast"
    REGISTER = "a2a:register"
    DISCOVER = "a2a:discover"
    HANDOFF = "a2a:handoff"
    ADMIN = "a2a:admin"


_AGENT_TYPE_PERMISSIONS: dict[str, frozenset[A2APermission]] = {
    "planner": frozenset({
        A2APermission.SEND_TASK, A2APermission.RECEIVE_TASK,
        A2APermission.BROADCAST, A2APermission.MULTICAST,
        A2APermission.DISCOVER, A2APermission.HANDOFF, A2APermission.REGISTER,
    }),
    "executor": frozenset({
        A2APermission.SEND_TASK, A2APermission.RECEIVE_TASK,
        A2APermission.DISCOVER, A2APermission.REGISTER,
    }),
    "retrieval": frozenset({
        A2APermission.RECEIVE_TASK, A2APermission.SEND_TASK,
        A2APermission.DISCOVER, A2APermission.REGISTER,
    }),
    "memory": frozenset({
        A2APermission.RECEIVE_TASK, A2APermission.SEND_TASK,
        A2APermission.DISCOVER, A2APermission.REGISTER,
    }),
    "research": frozenset({
        A2APermission.SEND_TASK, A2APermission.RECEIVE_TASK,
        A2APermission.BROADCAST, A2APermission.DISCOVER,
        A2APermission.HANDOFF, A2APermission.REGISTER,
    }),
    "coding": frozenset({
        A2APermission.RECEIVE_TASK, A2APermission.SEND_TASK,
        A2APermission.DISCOVER, A2APermission.REGISTER,
    }),
    "tool": frozenset({
        A2APermission.RECEIVE_TASK, A2APermission.SEND_TASK,
        A2APermission.DISCOVER, A2APermission.REGISTER,
    }),
    "orchestrator": frozenset(A2APermission),
}


def agent_has_permission(agent_type: str, permission: A2APermission) -> bool:
    perms = _AGENT_TYPE_PERMISSIONS.get(agent_type, frozenset())
    return permission in perms or A2APermission.ADMIN in perms


def authorize_message_send(
    sender_type: str,
    message_type_value: str,
) -> bool:
    from a2a.message import A2AMessageType
    broadcast_types = {A2AMessageType.BROADCAST.value, A2AMessageType.MULTICAST.value}
    if message_type_value in broadcast_types:
        return agent_has_permission(sender_type, A2APermission.BROADCAST)
    if message_type_value == A2AMessageType.HANDOFF.value:
        return agent_has_permission(sender_type, A2APermission.HANDOFF)
    return agent_has_permission(sender_type, A2APermission.SEND_TASK)
