# backend/api/routes/workflows.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, String, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from api.dependencies import CurrentUser, Pagination, get_db

router = APIRouter()


class WorkflowCreateRequest(BaseModel):
    name: str
    project_id: str
    description: Optional[str] = None
    template: Optional[str] = None
    definition: dict[str, Any] = {}


class WorkflowUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    definition: Optional[dict[str, Any]] = None


class WorkflowRunRequest(BaseModel):
    input: Optional[dict[str, Any]] = None


def _get_workflow_run_model():
    from database.base import Base, TimestampMixin, UUIDMixin

    class WorkflowRun(Base, UUIDMixin, TimestampMixin):
        __tablename__ = "workflow_runs"
        __table_args__ = {"extend_existing": True}

        workflow_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
        triggered_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
        status: Mapped[str] = mapped_column(String(32), default="started", nullable=False)
        input_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
        output_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
        steps: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
        started_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True),
            default=lambda: datetime.now(timezone.utc),
            nullable=False,
        )
        completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
        error_message: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    return WorkflowRun


def _workflow_response(wf) -> dict[str, Any]:
    return {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description if hasattr(wf, "description") else None,
        "project_id": str(wf.project_id) if hasattr(wf, "project_id") and wf.project_id else None,
        "template": wf.template if hasattr(wf, "template") else None,
        "definition": wf.definition if hasattr(wf, "definition") else {},
        "status": wf.status.value if hasattr(wf.status, "value") else str(wf.status),
        "run_count": wf.run_count if hasattr(wf, "run_count") else 0,
        "created_at": wf.created_at.isoformat() if hasattr(wf, "created_at") else None,
        "updated_at": wf.updated_at.isoformat() if hasattr(wf, "updated_at") else None,
    }


def _run_response(run) -> dict[str, Any]:
    return {
        "run_id": str(run.id),
        "workflow_id": str(run.workflow_id),
        "status": run.status,
        "input": run.input_data,
        "output": run.output_data,
        "steps": run.steps or [],
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
    }


@router.get("")
async def list_workflows(
    user: CurrentUser,
    pagination: Pagination,
    db=Depends(get_db),
    project_id: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    from database.repositories.workflow_repository import WorkflowRepository
    repo = WorkflowRepository(db)
    workflows = []
    if project_id:
        workflows = await repo.list_by_project(
            uuid.UUID(project_id),
            offset=pagination.offset,
            limit=pagination.limit,
        )
    return {
        "items": [_workflow_response(w) for w in workflows],
        "total": len(workflows),
    }


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.workflow_repository import WorkflowRepository
    repo = WorkflowRepository(db)
    wf = await repo.get_by_id(uuid.UUID(workflow_id))
    if wf is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Workflow", workflow_id)
    return _workflow_response(wf)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.workflow_repository import WorkflowRepository
    from database.models.workflow import WorkflowStatus
    repo = WorkflowRepository(db)
    wf = await repo.create(
        project_id=uuid.UUID(body.project_id),
        name=body.name,
        description=body.description,
        template=body.template,
        definition=body.definition,
        status=WorkflowStatus.DRAFT,
    )
    await db.commit()
    return _workflow_response(wf)


@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    body: WorkflowUpdateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.workflow_repository import WorkflowRepository
    repo = WorkflowRepository(db)
    wf = await repo.get_by_id(uuid.UUID(workflow_id))
    if wf is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Workflow", workflow_id)

    if user.organization_id and hasattr(wf, "organization_id"):
        if str(wf.organization_id) != str(user.organization_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if body.name is not None:
        stripped = body.name.strip()
        if not stripped:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Workflow name cannot be empty",
            )
        wf.name = stripped

    if body.description is not None and hasattr(wf, "description"):
        wf.description = body.description

    if body.definition is not None and hasattr(wf, "definition"):
        wf.definition = body.definition

    await db.commit()
    await db.refresh(wf)
    return _workflow_response(wf)


@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    body: WorkflowRunRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.workflow_repository import WorkflowRepository
    repo = WorkflowRepository(db)
    wf = await repo.get_by_id(uuid.UUID(workflow_id))
    if wf is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Workflow", workflow_id)

    WorkflowRun = _get_workflow_run_model()
    run = WorkflowRun(
        workflow_id=uuid.UUID(workflow_id),
        triggered_by=user.id,
        status="started",
        input_data=body.input,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)

    if hasattr(wf, "run_count"):
        wf.run_count = (wf.run_count or 0) + 1

    await db.commit()
    await db.refresh(run)

    try:
        from task_queue.tasks.ingestion import run_workflow_task
        run_workflow_task.delay(str(run.id), workflow_id, body.input or {})
    except Exception:
        pass

    return {"run_id": str(run.id), "status": "started"}


@router.get("/{workflow_id}/runs")
async def list_workflow_runs(
    workflow_id: str,
    user: CurrentUser,
    db=Depends(get_db),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    from database.repositories.workflow_repository import WorkflowRepository
    repo = WorkflowRepository(db)
    wf = await repo.get_by_id(uuid.UUID(workflow_id))
    if wf is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Workflow", workflow_id)

    WorkflowRun = _get_workflow_run_model()
    offset = (page - 1) * page_size

    count_result = await db.execute(
        select(func.count(WorkflowRun.id)).where(
            WorkflowRun.workflow_id == uuid.UUID(workflow_id)
        )
    )
    total = count_result.scalar_one()

    runs_result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == uuid.UUID(workflow_id))
        .order_by(WorkflowRun.started_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    runs = runs_result.scalars().all()

    return {
        "items": [_run_response(r) for r in runs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{workflow_id}/runs/{run_id}")
async def get_workflow_run(
    workflow_id: str,
    run_id: str,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.workflow_repository import WorkflowRepository
    repo = WorkflowRepository(db)
    wf = await repo.get_by_id(uuid.UUID(workflow_id))
    if wf is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Workflow", workflow_id)

    WorkflowRun = _get_workflow_run_model()
    result = await db.execute(
        select(WorkflowRun).where(
            WorkflowRun.id == uuid.UUID(run_id),
            WorkflowRun.workflow_id == uuid.UUID(workflow_id),
        )
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

    return _run_response(run)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_workflow(
    workflow_id: str,
    user: CurrentUser,
    db=Depends(get_db),
) -> Response:
    from database.repositories.workflow_repository import WorkflowRepository
    repo = WorkflowRepository(db)
    await repo.delete(uuid.UUID(workflow_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
