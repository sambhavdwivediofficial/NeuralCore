# multitenancy/organizations/roles.py
from __future__ import annotations

from settings import Role

ROLE_HIERARCHY: dict[Role, int] = {
    Role.VIEWER: 0,
    Role.DEVELOPER: 1,
    Role.ADMIN: 2,
    Role.OWNER: 3,
    Role.SUPER_ADMIN: 4,
}

ROLE_DISPLAY_NAMES: dict[Role, str] = {
    Role.VIEWER: "Viewer",
    Role.DEVELOPER: "Developer",
    Role.ADMIN: "Admin",
    Role.OWNER: "Owner",
    Role.SUPER_ADMIN: "Super Admin",
}

ASSIGNABLE_ORGANIZATION_ROLES: tuple[Role, ...] = (Role.VIEWER, Role.DEVELOPER, Role.ADMIN, Role.OWNER)


def role_rank(role: Role) -> int:
    return ROLE_HIERARCHY.get(role, 0)


def is_role_at_least(role: Role, minimum: Role) -> bool:
    return role_rank(role) >= role_rank(minimum)


def highest_role(roles: list[Role]) -> Role:
    if not roles:
        return Role.VIEWER
    return max(roles, key=role_rank)


def can_assign_role(actor_role: Role, target_role: Role) -> bool:
    if target_role not in ASSIGNABLE_ORGANIZATION_ROLES:
        return False
    if actor_role == Role.SUPER_ADMIN:
        return True
    return role_rank(actor_role) > role_rank(target_role)


def can_manage_member(actor_role: Role, member_role: Role) -> bool:
    if actor_role == Role.SUPER_ADMIN:
        return True
    return role_rank(actor_role) > role_rank(member_role)