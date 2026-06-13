# multitenancy/tenant_resolver.py
from __future__ import annotations

import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User
from multitenancy.organizations.members import MemberStatus, OrganizationMember
from multitenancy.organizations.organization import Organization, OrganizationStatus
from multitenancy.tenant_context import TenantContext
from settings import Role

TENANT_HEADER = "x-organization-id"


async def resolve_tenant_context(request: Request, user: User, db: AsyncSession) -> TenantContext:
    organization_id = _extract_organization_id(request, user)
    if organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization context could be resolved",
        )

    result = await db.execute(select(Organization).where(Organization.id == organization_id))
    organization = result.scalar_one_or_none()
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if organization.status == OrganizationStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization is suspended")
    if organization.status == OrganizationStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Organization subscription is cancelled")

    if user.role == Role.SUPER_ADMIN:
        role = Role.SUPER_ADMIN
    else:
        member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user.id,
            )
        )
        member = member_result.scalar_one_or_none()
        if member is None or member.status != MemberStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization",
            )
        role = member.role

    return TenantContext.build(
        organization_id=organization.id,
        organization_name=organization.name,
        organization_slug=organization.slug,
        plan=organization.plan,
        status=organization.status,
        user_id=user.id,
        role=role,
        settings=organization.settings,
        limit_overrides=organization.limit_overrides,
    )


def _extract_organization_id(request: Request, user: User) -> uuid.UUID | None:
    header_value = request.headers.get(TENANT_HEADER)
    if header_value:
        try:
            return uuid.UUID(header_value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid organization id header"
            ) from exc
    return user.organization_id