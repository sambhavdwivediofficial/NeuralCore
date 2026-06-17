# api/routes/workflows.py
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, Pagination, get_db

router = APIRouter()


class WorkflowCreateRequest(BaseModel):
    name: str
    project_id: str
    description: Optional[str] = None
    template: Optional[str] = None
    definition: dict[str, Any] = {}


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
        workflows = await repo.list_by_project(uuid.UUID(project_id), offset=pagination.offset, limit=pagination.limit)
    return {
        "items": [
            {
                "id": str(w.id),
                "name": w.name,
                "status": w.status.value,
                "run_count": w.run_count,
            }
            for w in workflows
        ],
        "total": len(workflows),
    }


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from database.repositories.workflow_repository import WorkflowRepository

    repo = WorkflowRepository(db)
    wf = await repo.get_by_id(uuid.UUID(workflow_id))
    if wf is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Workflow", workflow_id)
    return {
        "id": str(wf.id),
        "name": wf.name,
        "status": wf.status.value,
        "definition": wf.definition,
        "run_count": wf.run_count,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_workflow(body: WorkflowCreateRequest, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
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
    return {"id": str(wf.id), "name": wf.name, "status": wf.status.value}


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_workflow(workflow_id: str, user: CurrentUser, db=Depends(get_db)) -> Response:
    from database.repositories.workflow_repository import WorkflowRepository

    repo = WorkflowRepository(db)
    await repo.delete(uuid.UUID(workflow_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
