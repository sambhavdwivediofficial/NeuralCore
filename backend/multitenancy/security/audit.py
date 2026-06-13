# multitenancy/security/audit.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

from multitenancy.tenant_context import TenantContext

_audit_logger = structlog.get_logger("audit")


class AuditAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    PERMISSION_CHANGE = "permission_change"
    EXPORT = "export"
    QUOTA_EXCEEDED = "quota_exceeded"
    SETTINGS_CHANGE = "settings_change"


class AuditEvent:
    __slots__ = (
        "organization_id", "actor_id", "action", "resource_type", "resource_id",
        "metadata", "ip_address", "timestamp",
    )

    def __init__(
        self,
        *,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        action: AuditAction,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        self.organization_id = organization_id
        self.actor_id = actor_id
        self.action = action
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.metadata = metadata or {}
        self.ip_address = ip_address
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "organization_id": str(self.organization_id),
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "metadata": self.metadata,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat(),
        }


class AuditLogger:
    def __init__(self, tenant: TenantContext | None = None) -> None:
        self.tenant = tenant

    def log(self, event: AuditEvent) -> None:
        _audit_logger.info("audit_event", **event.to_dict())

    def record(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        resource_id: str | None = None,
        actor_id: uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> None:
        org_id = organization_id or (self.tenant.organization_id if self.tenant else None)
        actor = actor_id or (self.tenant.user_id if self.tenant else None)
        if org_id is None:
            raise ValueError("organization_id is required to record an audit event")
        event = AuditEvent(
            organization_id=org_id,
            actor_id=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            ip_address=ip_address,
        )
        self.log(event)