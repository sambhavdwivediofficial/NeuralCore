# database/repositories/dataset_repository.py
from __future__ import annotations

import uuid

from sqlalchemy import select

from database.base import BaseRepository
from database.models.dataset import Dataset, DatasetFormat, DatasetStatus


class DatasetRepository(BaseRepository[Dataset]):
    model = Dataset

    async def list_by_project(self, project_id: uuid.UUID, offset: int = 0, limit: int = 20) -> list[Dataset]:
        result = await self.session.execute(
            select(Dataset)
            .where(Dataset.project_id == project_id)
            .order_by(Dataset.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_format(self, project_id: uuid.UUID, dataset_format: DatasetFormat) -> list[Dataset]:
        result = await self.session.execute(
            select(Dataset).where(Dataset.project_id == project_id, Dataset.format == dataset_format)
        )
        return list(result.scalars().all())

    async def update_status(self, dataset_id: uuid.UUID, status: DatasetStatus) -> Dataset | None:
        return await self.update(dataset_id, status=status)

    async def update_stats(
        self, dataset_id: uuid.UUID, num_examples: int, size_bytes: int
    ) -> Dataset | None:
        return await self.update(dataset_id, num_examples=num_examples, size_bytes=size_bytes)