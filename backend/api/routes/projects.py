# api/routes/projects.py
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, Pagination, get_db
from api.exceptions import ConflictError, NotFoundError

router = APIRouter()


class ProjectCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    settings: Optional[dict[str, Any]] = None


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    settings: Optional[dict[str, Any]] = None


def _project_response(project: Any) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "name": project.name,
        "slug": project.slug,
        "description": project.description,
        "is_active": project.is_active,
        "organization_id": str(project.organization_id),
        "owner_id": str(project.owner_id) if project.owner_id else None,
        "settings": project.settings,
        "created_at": project.created_at.isoformat(),
        "updated_at": project.updated_at.isoformat(),
    }


@router.get("")
async def list_projects(
    user: CurrentUser,
    pagination: Pagination,
    db=Depends(get_db),
    search: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    from database.repositories.project_repository import ProjectRepository

    repo = ProjectRepository(db)
    if user.organization_id is None:
        return {"items": [], "total": 0, "page": pagination.page, "page_size": pagination.page_size}

    projects = await repo.list_by_organization(
        user.organization_id, offset=pagination.offset, limit=pagination.limit
    )
    total = await repo.count(organization_id=user.organization_id)
    return {
        "items": [_project_response(p) for p in projects],
        "total": total,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/{project_id}")
async def get_project(project_id: str, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from database.repositories.project_repository import ProjectRepository

    repo = ProjectRepository(db)
    project = await repo.get_by_id(uuid.UUID(project_id))
    if project is None or project.organization_id != user.organization_id:
        raise NotFoundError("Project", project_id)
    return _project_response(project)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.project_repository import ProjectRepository
    from multitenancy.tenant_manager import TenantManager

    if user.organization_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No organization context")

    manager = TenantManager(db)
    slug = await manager.generate_unique_slug(body.name)
    repo = ProjectRepository(db)

    existing = await repo.get_by_slug(slug)
    if existing is not None:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    project = await repo.create(
        organization_id=user.organization_id,
        owner_id=user.id,
        name=body.name,
        slug=slug,
        description=body.description,
        settings=body.settings or {},
    )
    await db.commit()
    return _project_response(project)


@router.patch("/{project_id}")
async def update_project(
    project_id: str,
    body: ProjectUpdateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.project_repository import ProjectRepository

    repo = ProjectRepository(db)
    project = await repo.get_by_id(uuid.UUID(project_id))
    if project is None or project.organization_id != user.organization_id:
        raise NotFoundError("Project", project_id)

    updates: dict[str, Any] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    if body.settings is not None:
        updates["settings"] = {**project.settings, **body.settings}

    updated = await repo.update(uuid.UUID(project_id), **updates)
    await db.commit()
    return _project_response(updated or project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_project(project_id: str, user: CurrentUser, db=Depends(get_db)) -> Response:
    from database.repositories.project_repository import ProjectRepository

    repo = ProjectRepository(db)
    project = await repo.get_by_id(uuid.UUID(project_id))
    if project is None or project.organization_id != user.organization_id:
        raise NotFoundError("Project", project_id)
    await repo.delete(uuid.UUID(project_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/analytics")
async def project_analytics(
    project_id: str,
    user: CurrentUser,
    range: Optional[str] = Query(default="7d", pattern="^(24h|7d|30d|90d)$"),
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "range": range,
        "total_queries": 0,
        "total_documents": 0,
        "total_agents_run": 0,
        "avg_latency_ms": 0.0,
        "error_rate": 0.0,
    }


@router.get("/{project_id}/usage")
async def project_usage(project_id: str, user: CurrentUser) -> dict[str, Any]:
    return {"project_id": project_id, "llm_tokens": 0, "embedding_tokens": 0, "storage_bytes": 0, "api_calls": 0}


@router.get("/{project_id}/settings")
async def get_project_settings(project_id: str, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from database.repositories.project_repository import ProjectRepository
    repo = ProjectRepository(db)
    project = await repo.get_by_id(uuid.UUID(project_id))
    if project is None or project.organization_id != user.organization_id:
        raise NotFoundError("Project", project_id)
    return project.settings


@router.patch("/{project_id}/settings")
async def update_project_settings(
    project_id: str,
    body: dict[str, Any],
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.project_repository import ProjectRepository
    repo = ProjectRepository(db)
    project = await repo.get_by_id(uuid.UUID(project_id))
    if project is None or project.organization_id != user.organization_id:
        raise NotFoundError("Project", project_id)
    merged = {**project.settings, **body}
    await repo.update(uuid.UUID(project_id), settings=merged)
    await db.commit()
    return merged
