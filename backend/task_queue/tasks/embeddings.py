# queue/tasks/embeddings.py
from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from sqlalchemy import select

from database.connection import get_session_factory
from database.models.knowledgebase import KnowledgeBase, KnowledgeBaseStatus
from task_queue.celery import celery_app, run_async
from settings import get_settings

logger = logging.getLogger(__name__)

try:
    import neuralcore_engine
except ImportError:
    neuralcore_engine = None


def _cache_key(text: str, model: str) -> str:
    digest = hashlib.sha256(f"{model}:{text}".encode("utf-8")).hexdigest()
    return f"emb:{digest}"


def _engine_cache_get(key: str) -> list[float] | None:
    if neuralcore_engine is None:
        return None
    func = getattr(neuralcore_engine, "py_embedding_cache_get", None)
    if func is None:
        return None
    try:
        return func(key)
    except Exception:
        return None


def _engine_cache_set(key: str, value: list[float]) -> None:
    if neuralcore_engine is None:
        return
    func = getattr(neuralcore_engine, "py_embedding_cache_set", None)
    if func is None:
        return
    try:
        func(key, value)
    except Exception:
        logger.debug("embedding cache set failed", exc_info=True)


@celery_app.task(
    name="queue.tasks.embeddings.generate_embeddings_for_chunks",
    bind=True,
    max_retries=5,
    default_retry_delay=30,
    acks_late=True,
)
def generate_embeddings_for_chunks(
    self,
    knowledge_base_id: str,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    try:
        return run_async(_generate_embeddings_for_chunks(uuid.UUID(knowledge_base_id), chunks))
    except Exception as exc:
        logger.exception("embedding generation failed", extra={"knowledge_base_id": knowledge_base_id})
        raise self.retry(exc=exc)


async def _generate_embeddings_for_chunks(
    knowledge_base_id: uuid.UUID, chunks: list[dict[str, Any]]
) -> dict[str, Any]:
    settings = get_settings()
    session_factory = get_session_factory()

    async with session_factory() as session:
        result = await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
        knowledge_base = result.scalar_one_or_none()
        if knowledge_base is None:
            raise ValueError(f"Knowledge base {knowledge_base_id} not found")

        from embeddings.embedding_factory import get_embedding_provider

        provider = get_embedding_provider(settings=settings, provider_name=knowledge_base.embedding_provider)

        texts = [chunk["text"] for chunk in chunks]
        cached_vectors: dict[int, list[float]] = {}
        pending_indices: list[int] = []
        pending_texts: list[str] = []

        for index, text in enumerate(texts):
            cached = _engine_cache_get(_cache_key(text, knowledge_base.embedding_model))
            if cached is not None:
                cached_vectors[index] = cached
            else:
                pending_indices.append(index)
                pending_texts.append(text)

        generated_vectors: list[list[float]] = []
        if pending_texts:
            generated_vectors = await provider.embed_documents(pending_texts, model=knowledge_base.embedding_model)
            for text, vector in zip(pending_texts, generated_vectors):
                _engine_cache_set(_cache_key(text, knowledge_base.embedding_model), vector)

        vectors: list[list[float]] = [[] for _ in texts]
        for index, vector in cached_vectors.items():
            vectors[index] = vector
        for offset, index in enumerate(pending_indices):
            vectors[index] = generated_vectors[offset]

        from vector_stores import get_vector_store_adapter

        vector_store = get_vector_store_adapter(settings=settings, backend=knowledge_base.vector_db_backend)
        points = [
            {"id": chunk["id"], "vector": vector, "metadata": chunk.get("metadata", {})}
            for chunk, vector in zip(chunks, vectors)
        ]
        await vector_store.upsert(collection_name=knowledge_base.collection_name, points=points)

        knowledge_base.chunk_count += len(chunks)
        knowledge_base.status = KnowledgeBaseStatus.READY
        await session.commit()

        logger.info(
            "generated embeddings for chunks",
            extra={
                "knowledge_base_id": str(knowledge_base_id),
                "count": len(chunks),
                "cache_hits": len(cached_vectors),
            },
        )
        return {
            "knowledge_base_id": str(knowledge_base_id),
            "embedded": len(chunks),
            "cache_hits": len(cached_vectors),
        }


@celery_app.task(
    name="queue.tasks.embeddings.refresh_knowledge_base_embeddings",
    bind=True,
    max_retries=2,
    default_retry_delay=120,
)
def refresh_knowledge_base_embeddings(self, knowledge_base_id: str) -> dict[str, Any]:
    return run_async(_refresh_knowledge_base_embeddings(uuid.UUID(knowledge_base_id)))


async def _refresh_knowledge_base_embeddings(knowledge_base_id: uuid.UUID) -> dict[str, Any]:
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == knowledge_base_id))
        knowledge_base = result.scalar_one_or_none()
        if knowledge_base is None:
            raise ValueError(f"Knowledge base {knowledge_base_id} not found")

        knowledge_base.status = KnowledgeBaseStatus.INDEXING
        await session.commit()

        from vector_stores import get_vector_store_adapter

        vector_store = get_vector_store_adapter(settings=settings, backend=knowledge_base.vector_db_backend)
        await vector_store.recreate_collection(
            collection_name=knowledge_base.collection_name,
            dimension=knowledge_base.embedding_dimension,
        )

        knowledge_base.chunk_count = 0
        knowledge_base.status = KnowledgeBaseStatus.READY
        await session.commit()

        logger.info("refreshed knowledge base embeddings", extra={"knowledge_base_id": str(knowledge_base_id)})
        return {"knowledge_base_id": str(knowledge_base_id), "status": knowledge_base.status.value}