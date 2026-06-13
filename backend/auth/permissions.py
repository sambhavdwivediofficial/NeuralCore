# auth/permissions.py
from __future__ import annotations

import enum

from multitenancy.organizations.permissions import Permission as OrganizationPermission
from multitenancy.organizations.permissions import has_permission as has_organization_permission
from settings import Role


class PlatformPermission(str, enum.Enum):
    USERS_MANAGE = "platform:users:manage"
    ORGANIZATIONS_MANAGE = "platform:organizations:manage"
    SYSTEM_SETTINGS_MANAGE = "platform:settings:manage"
    BILLING_OVERRIDE = "platform:billing:override"
    AUDIT_LOG_GLOBAL_VIEW = "platform:audit_log:view"
    FEATURE_FLAGS_MANAGE = "platform:feature_flags:manage"


ROLE_PLATFORM_PERMISSIONS: dict[Role, frozenset[PlatformPermission]] = {
    Role.VIEWER: frozenset(),
    Role.DEVELOPER: frozenset(),
    Role.ADMIN: frozenset(),
    Role.OWNER: frozenset(),
    Role.SUPER_ADMIN: frozenset(PlatformPermission),
}


def role_has_platform_permission(role: Role, permission: PlatformPermission) -> bool:
    return permission in ROLE_PLATFORM_PERMISSIONS.get(role, frozenset())


def role_has_permission(role: Role, permission: str) -> bool:
    if role == Role.SUPER_ADMIN:
        return True
    try:
        platform_permission = PlatformPermission(permission)
    except ValueError:
        platform_permission = None
    if platform_permission is not None:
        return role_has_platform_permission(role, platform_permission)
    try:
        organization_permission = OrganizationPermission(permission)
    except ValueError:
        return False
    return has_organization_permission(role, organization_permission)