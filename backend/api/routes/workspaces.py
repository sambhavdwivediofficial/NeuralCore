# api/routes/workspaces.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.dependencies import CurrentUser

router = APIRouter()


@router.get("")
async def list_workspaces(user: CurrentUser) -> list[dict[str, Any]]:
    return [{"id": str(user.organization_id) if user.organization_id else "default", "name": "Default Workspace", "is_default": True}]
