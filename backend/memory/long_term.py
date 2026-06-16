# memory/long_term.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.memory import Memory, MemoryLayer
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.memory.long_term")


@dataclass(slots=True)
class LongTermEntry:
    id: str
    agent_id: str
    content: str
    role: str | None
    importance_score: float
    access_count: int
    vector_id: str | None
    metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_model(cls, model: Memory) -> "LongTermEntry":
        return cls(
            id=str(model.id),
            agent_id=str(model.agent_id),
            content=model.content,
            role=model.role,
            importance_score=model.importance_score,
            access_count=model.access_count,
            vector_id=model.vector_id,
            metadata=model.metadata_,
            created_at=model.created_at,
        )


class LongTermMemory:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def store(
        self,
        agent_id: uuid.UUID,
        content: str,
        role: str | None = None,
        importance_score: float = 0.5,
        vector_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> LongTermEntry:
        memory = Memory(
            agent_id=agent_id,
            layer=MemoryLayer.LONG_TERM,
            role=role,
            content=content,
            importance_score=importance_score,
            vector_id=vector_id,
            metadata_=metadata or {},
        )
        self.session.add(memory)
        await self.session.flush()
        return LongTermEntry.from_model(memory)

    async def retrieve(
        self,
        agent_id: uuid.UUID,
        limit: int = 20,
        min_importance: float = 0.0,
        role: str | None = None,
    ) -> list[LongTermEntry]:
        stmt = (
            select(Memory)
            .where(
                Memory.agent_id == agent_id,
                Memory.layer == MemoryLayer.LONG_TERM,
                Memory.importance_score >= min_importance,
            )
            .order_by(Memory.importance_score.desc(), Memory.created_at.desc())
            .limit(limit)
        )
        if role:
            stmt = stmt.where(Memory.role == role)

        result = await self.session.execute(stmt)
        memories = list(result.scalars().all())

        for memory in memories:
            memory.access_count += 1
        await self.session.flush()

        return [LongTermEntry.from_model(m) for m in memories]

    async def update_importance(self, memory_id: uuid.UUID, importance_score: float) -> None:
        await self.session.execute(
            update(Memory)
            .where(Memory.id == memory_id)
            .values(importance_score=min(max(importance_score, 0.0), 1.0))
        )
        await self.session.flush()

    async def delete(self, memory_id: uuid.UUID) -> None:
        await self.session.execute(delete(Memory).where(Memory.id == memory_id))
        await self.session.flush()

    async def delete_by_agent(self, agent_id: uuid.UUID) -> int:
        result = await self.session.execute(
            delete(Memory).where(Memory.agent_id == agent_id, Memory.layer == MemoryLayer.LONG_TERM)
        )
        await self.session.flush()
        return result.rowcount or 0

    async def count(self, agent_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.agent_id == agent_id, Memory.layer == MemoryLayer.LONG_TERM)
        )
        return len(result.scalars().all())
    