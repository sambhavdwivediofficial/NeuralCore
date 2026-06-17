# api/routes/organizations.py
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_db

router = APIRouter()


class OrgCreateRequest(BaseModel):
    name: str
    billing_email: Optional[str] = None


@router.get("")
async def list_organizations(user: CurrentUser, db=Depends(get_db)) -> list[dict[str, Any]]:
    if user.organization_id is None:
        return []
    from sqlalchemy import text
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
async def get_organization(org_id: str, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from sqlalchemy import text
    from database.connection import get_engine
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM organizations WHERE id = :id"), {"id": org_id})
        row = result.mappings().first()
    if row is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Organization", org_id)
    return dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_organization(body: OrgCreateRequest, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from multitenancy.tenant_manager import TenantManager
    manager = TenantManager(db)
    org = await manager.create_organization(name=body.name, owner=user, billing_email=body.billing_email)
    await db.commit()
    return {"id": str(org.id), "name": org.name, "slug": org.slug, "plan": org.plan.value, "status": org.status.value}
