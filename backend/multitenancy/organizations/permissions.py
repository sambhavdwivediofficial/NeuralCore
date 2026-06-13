# multitenancy/organizations/permissions.py
from __future__ import annotations

import enum

from settings import Role


class Permission(str, enum.Enum):
    ORG_VIEW = "organization:view"
    ORG_UPDATE = "organization:update"
    ORG_DELETE = "organization:delete"
    MEMBERS_VIEW = "members:view"
    MEMBERS_INVITE = "members:invite"
    MEMBERS_REMOVE = "members:remove"
    MEMBERS_UPDATE_ROLE = "members:update_role"
    BILLING_VIEW = "billing:view"
    BILLING_MANAGE = "billing:manage"
    PROJECTS_CREATE = "projects:create"
    PROJECTS_VIEW = "projects:view"
    PROJECTS_UPDATE = "projects:update"
    PROJECTS_DELETE = "projects:delete"
    AGENTS_CREATE = "agents:create"
    AGENTS_EXECUTE = "agents:execute"
    AGENTS_DELETE = "agents:delete"
    KNOWLEDGE_BASES_MANAGE = "knowledge_bases:manage"
    DATASETS_MANAGE = "datasets:manage"
    WORKFLOWS_MANAGE = "workflows:manage"
    API_KEYS_MANAGE = "api_keys:manage"
    AUDIT_LOG_VIEW = "audit_log:view"
    QUOTAS_MANAGE = "quotas:manage"


_VIEWER_PERMS: frozenset[Permission] = frozenset({
    Permission.ORG_VIEW,
    Permission.MEMBERS_VIEW,
    Permission.PROJECTS_VIEW,
})

_DEVELOPER_PERMS: frozenset[Permission] = _VIEWER_PERMS | frozenset({
    Permission.PROJECTS_CREATE,
    Permission.PROJECTS_UPDATE,
    Permission.AGENTS_CREATE,
    Permission.AGENTS_EXECUTE,
    Permission.KNOWLEDGE_BASES_MANAGE,
    Permission.DATASETS_MANAGE,
    Permission.WORKFLOWS_MANAGE,
    Permission.API_KEYS_MANAGE,
})

_ADMIN_PERMS: frozenset[Permission] = _DEVELOPER_PERMS | frozenset({
    Permission.ORG_UPDATE,
    Permission.MEMBERS_INVITE,
    Permission.MEMBERS_REMOVE,
    Permission.MEMBERS_UPDATE_ROLE,
    Permission.PROJECTS_DELETE,
    Permission.AGENTS_DELETE,
    Permission.AUDIT_LOG_VIEW,
    Permission.QUOTAS_MANAGE,
})

_OWNER_PERMS: frozenset[Permission] = _ADMIN_PERMS | frozenset({
    Permission.ORG_DELETE,
    Permission.BILLING_VIEW,
    Permission.BILLING_MANAGE,
})

_SUPER_ADMIN_PERMS: frozenset[Permission] = frozenset(Permission)

ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: _VIEWER_PERMS,
    Role.DEVELOPER: _DEVELOPER_PERMS,
    Role.ADMIN: _ADMIN_PERMS,
    Role.OWNER: _OWNER_PERMS,
    Role.SUPER_ADMIN: _SUPER_ADMIN_PERMS,
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())