# api/routes/datasets.py
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, Pagination, get_db

router = APIRouter()


class DatasetCreateRequest(BaseModel):
    name: str
    project_id: str
    format: str = "alpaca"
    description: Optional[str] = None


@router.get("")
async def list_datasets(
    user: CurrentUser,
    pagination: Pagination,
    db=Depends(get_db),
    project_id: Optional[str] = None,
) -> dict[str, Any]:
    from database.repositories.dataset_repository import DatasetRepository
    repo = DatasetRepository(db)
    datasets = []
    if project_id:
        datasets = await repo.list_by_project(uuid.UUID(project_id), offset=pagination.offset, limit=pagination.limit)
    return {"items": [{"id": str(d.id), "name": d.name, "format": d.format.value, "status": d.status.value, "num_examples": d.num_examples} for d in datasets], "total": len(datasets)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_dataset(body: DatasetCreateRequest, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from database.repositories.dataset_repository import DatasetRepository
    from database.models.dataset import DatasetFormat, DatasetStatus
    repo = DatasetRepository(db)
    ds = await repo.create(project_id=uuid.UUID(body.project_id), name=body.name, description=body.description, format=DatasetFormat(body.format), status=DatasetStatus.PENDING)
    await db.commit()
    return {"id": str(ds.id), "name": ds.name, "format": ds.format.value, "status": ds.status.value}
