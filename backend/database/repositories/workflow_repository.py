# database/repositories/workflow_repository.py
from __future__ import annotations

import uuid

from sqlalchemy import select

from database.base import BaseRepository
from database.models.workflow import Workflow, WorkflowStatus


class WorkflowRepository(BaseRepository[Workflow]):
    model = Workflow

    async def list_by_project(self, project_id: uuid.UUID, offset: int = 0, limit: int = 20) -> list[Workflow]:
        result = await self.session.execute(
            select(Workflow)
            .where(Workflow.project_id == project_id)
            .order_by(Workflow.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_name(self, project_id: uuid.UUID, name: str) -> Workflow | None:
        result = await self.session.execute(
            select(Workflow).where(Workflow.project_id == project_id, Workflow.name == name)
        )
        return result.scalar_one_or_none()

    async def update_status(self, workflow_id: uuid.UUID, status: WorkflowStatus) -> Workflow | None:
        return await self.update(workflow_id, status=status)

    async def increment_run_count(self, workflow_id: uuid.UUID) -> Workflow | None:
        workflow = await self.get_by_id(workflow_id)
        if workflow is None:
            return None
        workflow.run_count += 1
        await self.session.flush()
        return workflow