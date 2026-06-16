# memory/episodic.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.memory import Memory, MemoryLayer
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.memory.episodic")


@dataclass(slots=True)
class Episode:
    id: str
    agent_id: str
    content: str
    importance_score: float
    access_count: int
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_model(cls, model: Memory) -> "Episode":
        return cls(
            id=str(model.id),
            agent_id=str(model.agent_id),
            content=model.content,
            importance_score=model.importance_score,
            access_count=model.access_count,
            metadata=model.metadata_,
            created_at=model.created_at,
        )


class EpisodicMemory:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        max_ep = settings.agents.memory.episodic.max_entries
        self._max_entries = max_ep if max_ep is not None else 1000

    async def record_episode(
        self,
        agent_id: uuid.UUID,
        content: str,
        importance_score: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Episode:
        current_count = await self._count(agent_id)
        if current_count >= self._max_entries:
            await self._evict_oldest(agent_id, 10)

        memory = Memory(
            agent_id=agent_id,
            layer=MemoryLayer.EPISODIC,
            content=content,
            importance_score=importance_score,
            metadata_=metadata or {},
        )
        self.session.add(memory)
        await self.session.flush()
        return Episode.from_model(memory)

    async def get_recent_episodes(
        self, agent_id: uuid.UUID, limit: int = 10
    ) -> list[Episode]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.agent_id == agent_id, Memory.layer == MemoryLayer.EPISODIC)
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        return [Episode.from_model(m) for m in result.scalars().all()]

    async def get_important_episodes(
        self, agent_id: uuid.UUID, min_importance: float = 0.7, limit: int = 20
    ) -> list[Episode]:
        result = await self.session.execute(
            select(Memory)
            .where(
                Memory.agent_id == agent_id,
                Memory.layer == MemoryLayer.EPISODIC,
                Memory.importance_score >= min_importance,
            )
            .order_by(Memory.importance_score.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        return [Episode.from_model(m) for m in result.scalars().all()]

    async def _count(self, agent_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(Memory).where(Memory.agent_id == agent_id, Memory.layer == MemoryLayer.EPISODIC)
        )
        return len(result.scalars().all())

    async def _evict_oldest(self, agent_id: uuid.UUID, n: int) -> None:
        result = await self.session.execute(
            select(Memory.id)
            .where(Memory.agent_id == agent_id, Memory.layer == MemoryLayer.EPISODIC)
            .order_by(Memory.importance_score.asc(), Memory.created_at.asc())
            .limit(n)
        )
        ids_to_delete = [row[0] for row in result.all()]
        if ids_to_delete:
            await self.session.execute(delete(Memory).where(Memory.id.in_(ids_to_delete)))
            await self.session.flush()

    async def clear(self, agent_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(Memory).where(Memory.agent_id == agent_id, Memory.layer == MemoryLayer.EPISODIC)
        )
        await self.session.flush()
        return result.rowcount or 0
    