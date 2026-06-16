# memory/semantic.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.memory.semantic")

_COLLECTION_SUFFIX = "_semantic_memory"


def _collection_name(agent_id: str) -> str:
    return f"nc_{agent_id.replace('-', '')}{_COLLECTION_SUFFIX}"


@dataclass(slots=True)
class SemanticMemoryEntry:
    id: str
    content: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class SemanticMemory:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def store(
        self,
        agent_id: uuid.UUID,
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        from embeddings.embedding_factory import get_embedding_provider
        from vector_stores import get_vector_store_adapter

        agent_id_str = str(agent_id)
        collection = _collection_name(agent_id_str)
        provider = get_embedding_provider(settings=self.settings)
        vector_store = get_vector_store_adapter(settings=self.settings)

        try:
            if not await vector_store.collection_exists(collection):
                dimension = provider.get_dimension()
                await vector_store.create_collection(collection, dimension)
            vector = await provider.embed_query(content)
            await vector_store.upsert(
                collection,
                [{"id": memory_id, "vector": vector, "metadata": {"content": content, "agent_id": agent_id_str, **(metadata or {})}}],
            )
            return True
        except Exception as exc:
            logger.warning("semantic_memory_store_failed", agent_id=agent_id_str, error=str(exc))
            return False

    async def search(
        self,
        agent_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> list[SemanticMemoryEntry]:
        from embeddings.embedding_factory import get_embedding_provider
        from vector_stores import get_vector_store_adapter

        agent_id_str = str(agent_id)
        collection = _collection_name(agent_id_str)
        provider = get_embedding_provider(settings=self.settings)
        vector_store = get_vector_store_adapter(settings=self.settings)

        try:
            if not await vector_store.collection_exists(collection):
                return []
            query_vector = await provider.embed_query(query)
            results = await vector_store.search(
                collection, query_vector, top_k=top_k, score_threshold=score_threshold
            )
            return [
                SemanticMemoryEntry(
                    id=result.id,
                    content=result.metadata.get("content", ""),
                    score=result.score,
                    metadata=result.metadata,
                )
                for result in results
            ]
        except Exception as exc:
            logger.warning("semantic_memory_search_failed", agent_id=agent_id_str, error=str(exc))
            return []

    async def delete(self, agent_id: uuid.UUID, memory_ids: list[str]) -> None:
        from vector_stores import get_vector_store_adapter

        agent_id_str = str(agent_id)
        collection = _collection_name(agent_id_str)
        vector_store = get_vector_store_adapter(settings=self.settings)
        try:
            if await vector_store.collection_exists(collection):
                await vector_store.delete(collection, memory_ids)
        except Exception as exc:
            logger.warning("semantic_memory_delete_failed", agent_id=agent_id_str, error=str(exc))

    async def delete_agent_collection(self, agent_id: uuid.UUID) -> None:
        from vector_stores import get_vector_store_adapter

        collection = _collection_name(str(agent_id))
        vector_store = get_vector_store_adapter(settings=self.settings)
        try:
            if await vector_store.collection_exists(collection):
                await vector_store.delete_collection(collection)
        except Exception as exc:
            logger.warning("semantic_memory_collection_delete_failed", error=str(exc))
