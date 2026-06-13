# auth/roles.py
from __future__ import annotations

from settings import Role

SIGNUP_ROLE: Role = Role.OWNER
DEFAULT_INVITE_ROLE: Role = Role.VIEWER

PLATFORM_ROLES: tuple[Role, ...] = (Role.SUPER_ADMIN,)
ORGANIZATION_ROLES: tuple[Role, ...] = (Role.OWNER, Role.ADMIN, Role.DEVELOPER, Role.VIEWER)


def is_platform_admin(role: Role) -> bool:
    return role == Role.SUPER_ADMIN


def is_valid_organization_role(role: Role) -> bool:
    return role in ORGANIZATION_ROLES


def default_role_for_signup() -> Role:
    return SIGNUP_ROLE


def parse_role(value: str) -> Role:
    try:
        return Role(value.strip().lower())
    except ValueError as exc:
        raise ValueError(f"'{value}' is not a valid role") from exc