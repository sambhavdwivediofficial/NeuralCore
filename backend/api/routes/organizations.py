# backend/api/routes/organizations.py
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text

from api.dependencies import CurrentUser, get_db
from settings import Role

router = APIRouter()


class OrgCreateRequest(BaseModel):
    name: str
    billing_email: Optional[str] = None


class OrgUpdateRequest(BaseModel):
    name: Optional[str] = None
    billing_email: Optional[EmailStr] = None


@router.get("")
async def list_organizations(
    user: CurrentUser,
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    if user.organization_id is None:
        return []
    from database.connection import get_engine
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id, name, slug, plan, status, created_at FROM organizations WHERE id = :id"),
            {"id": str(user.organization_id)},
        )
        rows = result.mappings().all()
    return [dict(row) for row in rows]


@router.get("/{org_id}")
async def get_organization(
    org_id: str,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.connection import get_engine
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM organizations WHERE id = :id"),
            {"id": org_id},
        )
        row = result.mappings().first()
    if row is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Organization", org_id)
    return dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrgCreateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from multitenancy.tenant_manager import TenantManager
    manager = TenantManager(db)
    org = await manager.create_organization(
        name=body.name,
        owner=user,
        billing_email=body.billing_email,
    )
    await db.commit()
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "plan": org.plan.value,
        "status": org.status.value,
    }


@router.patch("/{org_id}")
async def update_organization(
    org_id: str,
    body: OrgUpdateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    if user.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organization context",
        )

    from multitenancy.organizations.organization import Organization

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Organization", org_id)

    is_own_org = str(user.organization_id) == str(org_id)
    is_super_admin = user.role == Role.SUPER_ADMIN if hasattr(user, "role") else False

    if not is_own_org and not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own organization",
        )

    allowed_roles = {Role.OWNER, Role.ADMIN, Role.SUPER_ADMIN}
    user_role = user.role if hasattr(user, "role") else None
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to update organization",
        )

    if body.name is not None:
        stripped = body.name.strip()
        if not stripped:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Organization name cannot be empty",
            )
        org.name = stripped

    if body.billing_email is not None:
        if hasattr(org, "billing_email"):
            org.billing_email = str(body.billing_email)

    await db.commit()
    await db.refresh(org)

    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug if hasattr(org, "slug") else None,
        "billing_email": org.billing_email if hasattr(org, "billing_email") else None,
        "plan": org.plan.value if hasattr(org.plan, "value") else str(org.plan),
        "status": org.status.value if hasattr(org.status, "value") else str(org.status),
        "created_at": org.created_at.isoformat() if hasattr(org, "created_at") else None,
    }
