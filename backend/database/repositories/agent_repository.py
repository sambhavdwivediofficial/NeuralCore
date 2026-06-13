# database/repositories/agent_repository.py
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from database.base import BaseRepository
from database.models.agent import Agent, AgentStatus
from settings import AgentType


class AgentRepository(BaseRepository[Agent]):
    model = Agent

    async def list_by_project(self, project_id: uuid.UUID, offset: int = 0, limit: int = 20) -> list[Agent]:
        result = await self.session.execute(
            select(Agent)
            .where(Agent.project_id == project_id)
            .order_by(Agent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_type(self, project_id: uuid.UUID, agent_type: AgentType) -> list[Agent]:
        result = await self.session.execute(
            select(Agent).where(Agent.project_id == project_id, Agent.agent_type == agent_type)
        )
        return list(result.scalars().all())

    async def count_by_status(self, project_id: uuid.UUID, status: AgentStatus) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Agent)
            .where(Agent.project_id == project_id, Agent.status == status)
        )
        return int(result.scalar_one())

    async def update_status(self, agent_id: uuid.UUID, status: AgentStatus) -> Agent | None:
        return await self.update(agent_id, status=status)