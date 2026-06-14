# queue/tasks/retrieval.py
from __future__ import annotations

import logging
import uuid
from typing import Any

from queue.celery import celery_app, run_async
from settings import get_settings

logger = logging.getLogger(__name__)

try:
    import neuralcore_engine
except ImportError:
    neuralcore_engine = None


def _engine_invalidate_kb(knowledge_base_id: str) -> int:
    if neuralcore_engine is None:
        return 0
    func = getattr(neuralcore_engine, "py_query_cache_invalidate_kb", None)
    if func is None:
        return 0
    try:
        return int(func(knowledge_base_id))
    except Exception:
        return 0


@celery_app.task(
    name="queue.tasks.retrieval.warm_query_cache",
    bind=True,
    max_retries=2,
    default_retry_delay=60,
)
def warm_query_cache(self, knowledge_base_id: str, queries: list[str]) -> dict[str, Any]:
    return run_async(_warm_query_cache(uuid.UUID(knowledge_base_id), queries))


async def _warm_query_cache(knowledge_base_id: uuid.UUID, queries: list[str]) -> dict[str, Any]:
    settings = get_settings()

    from retrieval.retriever import Retriever

    retriever = Retriever(settings=settings)
    warmed = 0
    for query in queries:
        await retriever.search(
            knowledge_base_id=knowledge_base_id,
            query=query,
            top_k=settings.retrieval.vector_search.default_top_k,
        )
        warmed += 1

    logger.info("warmed query cache", extra={"knowledge_base_id": str(knowledge_base_id), "queries": warmed})
    return {"knowledge_base_id": str(knowledge_base_id), "queries_warmed": warmed}


@celery_app.task(
    name="queue.tasks.retrieval.invalidate_knowledge_base_cache",
    bind=True,
    max_retries=3,
    default_retry_delay=15,
)
def invalidate_knowledge_base_cache(self, knowledge_base_id: str) -> dict[str, Any]:
    return run_async(_invalidate_knowledge_base_cache(knowledge_base_id))


async def _invalidate_knowledge_base_cache(knowledge_base_id: str) -> dict[str, Any]:
    invalidated = _engine_invalidate_kb(knowledge_base_id)
    logger.info(
        "invalidated knowledge base cache",
        extra={"knowledge_base_id": knowledge_base_id, "invalidated": invalidated},
    )
    return {"knowledge_base_id": knowledge_base_id, "invalidated": invalidated}


@celery_app.task(
    name="queue.tasks.retrieval.reindex_knowledge_base",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    acks_late=True,
)
def reindex_knowledge_base(self, knowledge_base_id: str) -> dict[str, Any]:
    from queue.tasks.embeddings import _refresh_knowledge_base_embeddings

    return run_async(_refresh_knowledge_base_embeddings(uuid.UUID(knowledge_base_id)))