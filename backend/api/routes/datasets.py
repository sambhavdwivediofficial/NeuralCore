# backend/api/routes/datasets.py
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from api.dependencies import CurrentUser, Pagination, get_db

router = APIRouter()


class DatasetCreateRequest(BaseModel):
    name: str
    project_id: str
    format: str = "alpaca"
    description: Optional[str] = None


class DatasetUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


def _dataset_response(ds) -> dict[str, Any]:
    return {
        "id": str(ds.id),
        "name": ds.name,
        "description": ds.description if hasattr(ds, "description") else None,
        "project_id": str(ds.project_id) if hasattr(ds, "project_id") and ds.project_id else None,
        "format": ds.format.value if hasattr(ds.format, "value") else str(ds.format),
        "row_count": ds.num_examples if hasattr(ds, "num_examples") else 0,
        "status": ds.status.value if hasattr(ds.status, "value") else str(ds.status),
        "created_at": ds.created_at.isoformat() if hasattr(ds, "created_at") else None,
        "updated_at": ds.updated_at.isoformat() if hasattr(ds, "updated_at") else None,
    }


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
        datasets = await repo.list_by_project(
            uuid.UUID(project_id),
            offset=pagination.offset,
            limit=pagination.limit,
        )
    return {
        "items": [_dataset_response(d) for d in datasets],
        "total": len(datasets),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_dataset(
    body: DatasetCreateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.dataset_repository import DatasetRepository
    from database.models.dataset import DatasetFormat, DatasetStatus
    repo = DatasetRepository(db)
    ds = await repo.create(
        project_id=uuid.UUID(body.project_id),
        name=body.name,
        description=body.description,
        format=DatasetFormat(body.format),
        status=DatasetStatus.PENDING,
    )
    await db.commit()
    return _dataset_response(ds)


@router.get("/{dataset_id}")
async def get_dataset(
    dataset_id: str,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.dataset_repository import DatasetRepository
    repo = DatasetRepository(db)
    ds = await repo.get_by_id(uuid.UUID(dataset_id))
    if ds is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Dataset", dataset_id)

    if user.organization_id and hasattr(ds, "organization_id"):
        if str(ds.organization_id) != str(user.organization_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return _dataset_response(ds)


@router.patch("/{dataset_id}")
async def update_dataset(
    dataset_id: str,
    body: DatasetUpdateRequest,
    user: CurrentUser,
    db=Depends(get_db),
) -> dict[str, Any]:
    from database.repositories.dataset_repository import DatasetRepository
    repo = DatasetRepository(db)
    ds = await repo.get_by_id(uuid.UUID(dataset_id))
    if ds is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Dataset", dataset_id)

    if user.organization_id and hasattr(ds, "organization_id"):
        if str(ds.organization_id) != str(user.organization_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if body.name is not None:
        stripped = body.name.strip()
        if not stripped:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Dataset name cannot be empty",
            )
        ds.name = stripped

    if body.description is not None and hasattr(ds, "description"):
        ds.description = body.description

    await db.commit()
    await db.refresh(ds)
    return _dataset_response(ds)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_dataset(
    dataset_id: str,
    user: CurrentUser,
    db=Depends(get_db),
) -> Response:
    from database.repositories.dataset_repository import DatasetRepository
    repo = DatasetRepository(db)
    ds = await repo.get_by_id(uuid.UUID(dataset_id))
    if ds is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Dataset", dataset_id)

    if user.organization_id and hasattr(ds, "organization_id"):
        if str(ds.organization_id) != str(user.organization_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    await repo.delete(uuid.UUID(dataset_id))
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
