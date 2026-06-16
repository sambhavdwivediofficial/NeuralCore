# memory/memory_manager.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from memory.episodic import Episode, EpisodicMemory
from memory.long_term import LongTermEntry, LongTermMemory
from memory.semantic import SemanticMemory, SemanticMemoryEntry
from memory.session import SessionMemory
from memory.short_term import ShortTermEntry, ShortTermMemory
from monitoring.logging import get_logger
from multitenancy.tenant_context import TenantContext
from settings import Settings

logger = get_logger("neuralcore.memory.manager")


@dataclass(slots=True)
class MemoryContext:
    short_term: list[dict[str, str]] = field(default_factory=list)
    long_term: list[LongTermEntry] = field(default_factory=list)
    semantic: list[SemanticMemoryEntry] = field(default_factory=list)
    episodic: list[Episode] = field(default_factory=list)
    session_vars: dict[str, Any] = field(default_factory=dict)
    total_tokens_used: int = 0


class MemoryManager:
    def __init__(
        self,
        tenant: TenantContext,
        db: AsyncSession,
        redis: Redis,
        settings: Settings,
    ) -> None:
        self.tenant = tenant
        self.settings = settings
        self._short_term = ShortTermMemory(redis, settings)
        self._session = SessionMemory(redis, settings)
        self._long_term = LongTermMemory(db, settings)
        self._episodic = EpisodicMemory(db, settings)
        self._semantic = SemanticMemory(settings)

    async def add_message(
        self,
        agent_id: uuid.UUID,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ShortTermEntry:
        return await self._short_term.add(
            agent_id=str(agent_id),
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata,
        )

    async def store_long_term(
        self,
        agent_id: uuid.UUID,
        content: str,
        role: str | None = None,
        importance_score: float = 0.5,
        also_embed: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> LongTermEntry:
        entry = await self._long_term.store(
            agent_id=agent_id,
            content=content,
            role=role,
            importance_score=importance_score,
            metadata=metadata,
        )
        if also_embed:
            await self._semantic.store(
                agent_id=agent_id,
                memory_id=entry.id,
                content=content,
                metadata={"importance_score": importance_score, **(metadata or {})},
            )
        return entry

    async def record_episode(
        self,
        agent_id: uuid.UUID,
        summary: str,
        importance_score: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Episode:
        return await self._episodic.record_episode(
            agent_id=agent_id,
            content=summary,
            importance_score=importance_score,
            metadata=metadata,
        )

    async def get_context(
        self,
        agent_id: uuid.UUID,
        session_id: str,
        query: str,
        max_tokens: int = 8192,
        include_semantic: bool = True,
        include_episodic: bool = True,
    ) -> MemoryContext:
        from chunking.base_chunker import count_tokens

        cfg = self.settings.agents.context_window
        stm_budget = int(max_tokens * cfg.memory_ratio * 0.5)
        ltm_budget = int(max_tokens * cfg.memory_ratio * 0.3)
        semantic_budget = int(max_tokens * cfg.memory_ratio * 0.2)

        short_term_messages = await self._short_term.to_messages(
            str(agent_id), session_id, max_tokens=stm_budget
        )
        long_term_entries = await self._long_term.retrieve(
            agent_id=agent_id, limit=10, min_importance=0.3
        )
        semantic_entries: list[SemanticMemoryEntry] = []
        if include_semantic and query:
            semantic_entries = await self._semantic.search(
                agent_id=agent_id, query=query, top_k=5
            )
        episodic_entries: list[Episode] = []
        if include_episodic:
            episodic_entries = await self._episodic.get_recent_episodes(agent_id, limit=5)

        session_vars = await self._session.get_all(str(agent_id), session_id)

        total_tokens = (
            sum(count_tokens(msg["content"]) for msg in short_term_messages)
            + sum(count_tokens(e.content) for e in long_term_entries)
            + sum(count_tokens(e.content) for e in semantic_entries)
        )

        return MemoryContext(
            short_term=short_term_messages,
            long_term=long_term_entries,
            semantic=semantic_entries,
            episodic=episodic_entries,
            session_vars=session_vars,
            total_tokens_used=total_tokens,
        )

    async def set_session_var(
        self, agent_id: uuid.UUID, session_id: str, key: str, value: Any
    ) -> None:
        await self._session.set(str(agent_id), session_id, key, value)

    async def get_session_var(
        self, agent_id: uuid.UUID, session_id: str, key: str, default: Any = None
    ) -> Any:
        return await self._session.get(str(agent_id), session_id, key, default)

    async def clear_session(self, agent_id: uuid.UUID, session_id: str) -> None:
        await self._short_term.clear(str(agent_id), session_id)
        await self._session.clear(str(agent_id), session_id)

    async def delete_agent_memory(self, agent_id: uuid.UUID) -> dict[str, int]:
        ltm_deleted = await self._long_term.delete_by_agent(agent_id)
        episodic_deleted = await self._episodic.clear(agent_id)
        await self._semantic.delete_agent_collection(agent_id)
        return {
            "long_term_deleted": ltm_deleted,
            "episodic_deleted": episodic_deleted,
        }

    def format_context_as_text(self, context: MemoryContext) -> str:
        parts: list[str] = []

        if context.long_term:
            parts.append("## Long-term Memory")
            for entry in context.long_term[:5]:
                parts.append(f"- {entry.content}")

        if context.semantic:
            parts.append("\n## Relevant Past Knowledge")
            for entry in context.semantic[:3]:
                parts.append(f"- [{entry.score:.2f}] {entry.content}")

        if context.episodic:
            parts.append("\n## Recent Episodes")
            for episode in context.episodic[:3]:
                parts.append(f"- {episode.content}")

        if context.session_vars:
            parts.append("\n## Session Variables")
            for key, value in list(context.session_vars.items())[:5]:
                parts.append(f"- {key}: {value}")

        return "\n".join(parts)
    