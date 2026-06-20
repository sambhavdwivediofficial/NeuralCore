# multitenancy/tenant_context.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from multitenancy.organizations.organization import OrganizationPlan, OrganizationStatus
from multitenancy.tenant_limits import TenantLimits, get_limits_for_plan, merge_overrides
from settings import Role


@dataclass(slots=True, frozen=True)
class TenantContext:
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    plan: OrganizationPlan
    status: OrganizationStatus
    user_id: uuid.UUID
    role: Role
    limits: TenantLimits
    settings: dict = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        return self.status in (OrganizationStatus.ACTIVE, OrganizationStatus.TRIAL)

    @property
    def is_owner(self) -> bool:
        return self.role in (Role.OWNER, Role.SUPER_ADMIN)

    @property
    def is_super_admin(self) -> bool:
        return self.role == Role.SUPER_ADMIN

    def feature_enabled(self, feature: str, default: bool = False) -> bool:
        flags = self.settings.get("feature_flags", {})
        return bool(flags.get(feature, default))

    @classmethod
    def build(
        cls,
        *,
        organization_id: uuid.UUID,
        organization_name: str,
        organization_slug: str,
        plan: OrganizationPlan,
        status: OrganizationStatus,
        user_id: uuid.UUID,
        role: Role,
        settings: dict | None = None,
        limit_overrides: dict | None = None,
        is_owner_account: bool = False,
    ) -> "TenantContext":
        base_limits = get_limits_for_plan(plan, is_owner_account=is_owner_account)
        limits = merge_overrides(base_limits, limit_overrides or {})
        return cls(
            organization_id=organization_id,
            organization_name=organization_name,
            organization_slug=organization_slug,
            plan=plan,
            status=status,
            user_id=user_id,
            role=role,
            limits=limits,
            settings=settings or {},
        )
