# api/routes/plugins.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.dependencies import CurrentUser

router = APIRouter()


@router.get("")
async def list_plugins(user: CurrentUser) -> list[dict[str, Any]]:
    return [
        {"id": "github", "name": "GitHub", "description": "Connect GitHub repositories", "enabled": True},
        {"id": "slack", "name": "Slack", "description": "Connect Slack channels", "enabled": True},
        {"id": "notion", "name": "Notion", "description": "Connect Notion workspaces", "enabled": True},
        {"id": "jira", "name": "Jira", "description": "Connect Jira projects", "enabled": True},
    ]
