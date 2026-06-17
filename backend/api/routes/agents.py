# api/routes/agents.py
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.dependencies import CurrentUser, Pagination, get_app_settings, get_db, get_redis
from api.exceptions import NotFoundError
from settings import AgentType, Settings

router = APIRouter()


class AgentCreateRequest(BaseModel):
    name: str
    agent_type: str
    project_id: str
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: str = "local"
    model_name: str = "neuralcore-48b"
    max_iterations: int = 10
    tools: list[str] = []
    config: dict[str, Any] = {}


class AgentUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    max_iterations: Optional[int] = None
    tools: Optional[list[str]] = None
    config: Optional[dict[str, Any]] = None


class AgentRunRequest(BaseModel):
    input: str


def _agent_response(agent: Any) -> dict[str, Any]:
    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "agent_type": agent.agent_type.value,
        "status": agent.status.value,
        "project_id": str(agent.project_id),
        "model_provider": agent.model_provider,
        "model_name": agent.model_name,
        "system_prompt": agent.system_prompt,
        "max_iterations": agent.max_iterations,
        "tools": agent.tools,
        "config": agent.config,
        "last_run_at": agent.last_run_at.isoformat() if agent.last_run_at else None,
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat(),
    }


@router.get("")
async def list_agents(
    user: CurrentUser,
    pagination: Pagination,
    db=Depends(get_db),
    project_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    from database.repositories.agent_repository import AgentRepository

    repo = AgentRepository(db)
    if project_id:
        agents = await repo.list_by_project(uuid.UUID(project_id), offset=pagination.offset, limit=pagination.limit)
        total = await repo.count(project_id=uuid.UUID(project_id))
    else:
        agents = []
        total = 0

    return {
        "items": [_agent_response(a) for a in agents],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/tools")
async def list_tools() -> list[dict[str, Any]]:
    from tools.registry import get_tool_registry

    registry = get_tool_registry()
    return [
        {"id": name, "name": name.replace("_", " ").title(), "description": tool.description if hasattr(tool, "description") else ""}
        for name, tool in registry._tools.items()
    ]


@router.get("/{agent_id}")
async def get_agent(agent_id: str, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from database.repositories.agent_repository import AgentRepository

    repo = AgentRepository(db)
    agent = await repo.get_by_id(uuid.UUID(agent_id))
    if agent is None:
        raise NotFoundError("Agent", agent_id)
    return _agent_response(agent)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(body: AgentCreateRequest, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from database.repositories.agent_repository import AgentRepository
    from database.models.agent import AgentStatus

    try:
        agent_type = AgentType(body.agent_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid agent type: {body.agent_type}")

    repo = AgentRepository(db)
    agent = await repo.create(
        project_id=uuid.UUID(body.project_id),
        name=body.name,
        description=body.description,
        agent_type=agent_type,
        status=AgentStatus.CREATED,
        model_provider=body.model_provider,
        model_name=body.model_name,
        system_prompt=body.system_prompt,
        max_iterations=body.max_iterations,
        tools=body.tools,
        config=body.config,
    )
    await db.commit()
    return _agent_response(agent)


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str, body: AgentUpdateRequest, user: CurrentUser, db=Depends(get_db)
) -> dict[str, Any]:
    from database.repositories.agent_repository import AgentRepository

    repo = AgentRepository(db)
    agent = await repo.get_by_id(uuid.UUID(agent_id))
    if agent is None:
        raise NotFoundError("Agent", agent_id)

    updates: dict[str, Any] = {}
    for field in ("name", "description", "system_prompt", "model_provider", "model_name", "max_iterations", "tools", "config"):
        value = getattr(body, field)
        if value is not None:
            updates[field] = value

    updated = await repo.update(uuid.UUID(agent_id), **updates)
    await db.commit()
    return _agent_response(updated or agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_agent(agent_id: str, user: CurrentUser, db=Depends(get_db)) -> Response:
    from database.repositories.agent_repository import AgentRepository

    repo = AgentRepository(db)
    await repo.delete(uuid.UUID(agent_id))
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{agent_id}/run")
async def run_agent(
    agent_id: str,
    body: AgentRunRequest,
    user: CurrentUser,
    db=Depends(get_db),
    redis=Depends(get_redis),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    run_id = uuid.uuid4().hex
    from task_queue.celery import celery_app
    return {"run_id": run_id, "agent_id": agent_id, "status": "started", "input": body.input}


@router.post("/{agent_id}/pause", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def pause_agent(agent_id: str, user: CurrentUser, db=Depends(get_db)) -> Response:
    from database.repositories.agent_repository import AgentRepository
    from database.models.agent import AgentStatus

    repo = AgentRepository(db)
    await repo.update_status(uuid.UUID(agent_id), AgentStatus.PAUSED)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{agent_id}/resume", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def resume_agent(agent_id: str, user: CurrentUser, db=Depends(get_db)) -> Response:
    from database.repositories.agent_repository import AgentRepository
    from database.models.agent import AgentStatus

    repo = AgentRepository(db)
    await repo.update_status(uuid.UUID(agent_id), AgentStatus.RUNNING)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{agent_id}/stop", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def stop_agent(agent_id: str, user: CurrentUser, db=Depends(get_db)) -> Response:
    from database.repositories.agent_repository import AgentRepository
    from database.models.agent import AgentStatus

    repo = AgentRepository(db)
    await repo.update_status(uuid.UUID(agent_id), AgentStatus.COMPLETED)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{agent_id}/runs")
async def list_runs(agent_id: str, user: CurrentUser, pagination: Pagination) -> dict[str, Any]:
    return {"items": [], "total": 0, "page": pagination.page, "page_size": pagination.page_size}


@router.get("/{agent_id}/runs/{run_id}")
async def get_run(agent_id: str, run_id: str, user: CurrentUser) -> dict[str, Any]:
    return {"id": run_id, "agent_id": agent_id, "status": "completed", "output": "", "steps": []}


@router.get("/{agent_id}/runs/{run_id}/logs")
async def get_run_logs(agent_id: str, run_id: str, user: CurrentUser) -> list[dict[str, Any]]:
    return []


@router.get("/{agent_id}/runs/{run_id}/stream")
async def stream_run(
    agent_id: str,
    run_id: str,
    user: CurrentUser,
    redis=Depends(get_redis),
) -> StreamingResponse:
    async def _event_generator() -> AsyncIterator[str]:
        yield f"data: {json.dumps({'type': 'step_update', 'step': {'id': '1', 'title': 'Starting', 'state': 'running'}})}\n\n"
        await asyncio.sleep(0.1)
        yield f"data: {json.dumps({'type': 'step_update', 'step': {'id': '1', 'title': 'Starting', 'state': 'complete'}})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


@router.get("/{agent_id}/settings")
async def get_agent_settings(agent_id: str, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from database.repositories.agent_repository import AgentRepository

    repo = AgentRepository(db)
    agent = await repo.get_by_id(uuid.UUID(agent_id))
    if agent is None:
        raise NotFoundError("Agent", agent_id)
    return agent.config


@router.patch("/{agent_id}/settings")
async def update_agent_settings(
    agent_id: str, body: dict[str, Any], user: CurrentUser, db=Depends(get_db)
) -> dict[str, Any]:
    from database.repositories.agent_repository import AgentRepository

    repo = AgentRepository(db)
    agent = await repo.get_by_id(uuid.UUID(agent_id))
    if agent is None:
        raise NotFoundError("Agent", agent_id)
    merged = {**agent.config, **body}
    await repo.update(uuid.UUID(agent_id), config=merged)
    await db.commit()
    return merged
