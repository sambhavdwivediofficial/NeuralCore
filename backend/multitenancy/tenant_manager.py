# multitenancy/tenant_manager.py
from __future__ import annotations

import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User
from multitenancy.organizations.members import MemberStatus, OrganizationMember
from multitenancy.organizations.organization import Organization, OrganizationPlan, OrganizationStatus
from multitenancy.organizations.roles import can_manage_member
from settings import Role

_SLUG_PATTERN = re.compile(r"[^a-z0-9-]+")


class TenantError(Exception):
    pass


class SlugAlreadyExistsError(TenantError):
    pass


class TenantManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def slugify(name: str) -> str:
        slug = name.strip().lower().replace(" ", "-")
        slug = _SLUG_PATTERN.sub("", slug)
        return slug.strip("-") or uuid.uuid4().hex[:8]

    async def slug_exists(self, slug: str) -> bool:
        result = await self.session.execute(select(Organization.id).where(Organization.slug == slug))
        return result.scalar_one_or_none() is not None

    async def generate_unique_slug(self, name: str) -> str:
        base_slug = self.slugify(name)
        slug = base_slug
        suffix = 1
        while await self.slug_exists(slug):
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug

    async def create_organization(
        self,
        *,
        name: str,
        owner: User,
        plan: OrganizationPlan = OrganizationPlan.FREE,
        billing_email: str | None = None,
        trial_days: int = 14,
    ) -> Organization:
        slug = await self.generate_unique_slug(name)
        organization = Organization(
            name=name,
            slug=slug,
            plan=plan,
            status=OrganizationStatus.TRIAL,
            billing_email=billing_email or owner.email,
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=trial_days),
        )
        self.session.add(organization)
        await self.session.flush()

        member = OrganizationMember(
            organization_id=organization.id,
            user_id=owner.id,
            role=Role.OWNER,
            status=MemberStatus.ACTIVE,
            joined_at=datetime.now(timezone.utc),
        )
        self.session.add(member)

        if owner.organization_id is None:
            owner.organization_id = organization.id

        await self.session.flush()
        return organization

    async def get_organization(self, organization_id: uuid.UUID) -> Organization | None:
        result = await self.session.execute(select(Organization).where(Organization.id == organization_id))
        return result.scalar_one_or_none()

    async def update_organization(self, organization_id: uuid.UUID, **fields: object) -> Organization | None:
        organization = await self.get_organization(organization_id)
        if organization is None:
            return None
        for key, value in fields.items():
            setattr(organization, key, value)
        await self.session.flush()
        return organization

    async def change_plan(self, organization_id: uuid.UUID, plan: OrganizationPlan) -> Organization | None:
        return await self.update_organization(organization_id, plan=plan, status=OrganizationStatus.ACTIVE)

    async def suspend_organization(self, organization_id: uuid.UUID, reason: str) -> Organization | None:
        return await self.update_organization(
            organization_id,
            status=OrganizationStatus.SUSPENDED,
            suspended_at=datetime.now(timezone.utc),
            suspension_reason=reason,
        )

    async def reactivate_organization(self, organization_id: uuid.UUID) -> Organization | None:
        return await self.update_organization(
            organization_id, status=OrganizationStatus.ACTIVE, suspended_at=None, suspension_reason=None
        )

    async def cancel_organization(self, organization_id: uuid.UUID) -> Organization | None:
        return await self.update_organization(organization_id, status=OrganizationStatus.CANCELLED)

    async def list_members(self, organization_id: uuid.UUID) -> list[OrganizationMember]:
        result = await self.session.execute(
            select(OrganizationMember).where(OrganizationMember.organization_id == organization_id)
        )
        return list(result.scalars().all())

    async def get_member(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> OrganizationMember | None:
        result = await self.session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def invite_member(
        self, organization_id: uuid.UUID, user_id: uuid.UUID, role: Role, invited_by: uuid.UUID
    ) -> OrganizationMember:
        existing = await self.get_member(organization_id, user_id)
        if existing is not None:
            return existing
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            status=MemberStatus.INVITED,
            invited_by=invited_by,
            invited_at=datetime.now(timezone.utc),
            invite_token=uuid.uuid4().hex,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def accept_invite(self, organization_id: uuid.UUID, user_id: uuid.UUID) -> OrganizationMember | None:
        member = await self.get_member(organization_id, user_id)
        if member is None:
            return None
        member.status = MemberStatus.ACTIVE
        member.joined_at = datetime.now(timezone.utc)
        member.invite_token = None
        await self.session.flush()
        return member

    async def update_member_role(
        self, organization_id: uuid.UUID, user_id: uuid.UUID, new_role: Role, actor_role: Role
    ) -> OrganizationMember | None:
        member = await self.get_member(organization_id, user_id)
        if member is None:
            return None
        if not can_manage_member(actor_role, member.role):
            raise TenantError("Insufficient privileges to modify this member")
        member.role = new_role
        await self.session.flush()
        return member

    async def remove_member(self, organization_id: uuid.UUID, user_id: uuid.UUID, actor_role: Role) -> bool:
        member = await self.get_member(organization_id, user_id)
        if member is None:
            return False
        if not can_manage_member(actor_role, member.role):
            raise TenantError("Insufficient privileges to remove this member")
        member.status = MemberStatus.REMOVED
        await self.session.flush()
        return True