# api/routes/admin.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.dependencies import CurrentUser, require_roles
from settings import Role

router = APIRouter()


@router.get("/stats", dependencies=[Depends(require_roles(Role.SUPER_ADMIN.value))])
async def platform_stats(user: CurrentUser) -> dict[str, Any]:
    return {"total_organizations": 0, "total_users": 0, "total_agents": 0, "total_queries": 0}


@router.get("/organizations", dependencies=[Depends(require_roles(Role.SUPER_ADMIN.value))])
async def list_all_organizations(user: CurrentUser) -> list[dict[str, Any]]:
    return []
