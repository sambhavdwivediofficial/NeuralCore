# api/routes/prompts.py
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_app_settings
from settings import Settings

router = APIRouter()


class PromptRenderRequest(BaseModel):
    template_name: str
    variables: dict[str, Any] = {}


class PromptCreateRequest(BaseModel):
    name: str
    template: str
    description: Optional[str] = None
    variables: list[str] = []


@router.get("")
async def list_prompt_templates(user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> list[dict[str, Any]]:
    from prompt_engine.template_engine import default_registry
    return [{"name": name, "input_variables": tmpl.input_variables, "description": tmpl.description} for name, tmpl in default_registry._templates.items()]


@router.post("/render")
async def render_prompt(body: PromptRenderRequest, user: CurrentUser) -> dict[str, Any]:
    from prompt_engine.template_engine import default_registry
    try:
        rendered = default_registry.render(body.template_name, **body.variables)
        return {"template_name": body.template_name, "rendered": rendered}
    except Exception as exc:
        from api.exceptions import UnprocessableError
        raise UnprocessableError(str(exc))
    