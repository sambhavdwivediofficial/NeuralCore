# retrieval/vector_search.py
from __future__ import annotations

import uuid
from typing import Any

from monitoring.logging import get_logger
from monitoring.metrics import VECTOR_SEARCH_DURATION_SECONDS, track_duration
from monitoring.tracing import trace_span
from settings import Settings
from vector_stores.base import MetadataFilter, VectorSearchResult

try:
    import neuralcore_engine
except ImportError:
    neuralcore_engine = None

logger = get_logger("neuralcore.retrieval.vector_search")


class VectorSearchResult2(VectorSearchResult):
    pass


async def vector_search(
    *,
    query_vector: list[float],
    knowledge_base_id: uuid.UUID,
    collection_name: str,
    top_k: int,
    filters: list[MetadataFilter] | None = None,
    score_threshold: float | None = None,
    with_vectors: bool = False,
    settings: Settings,
) -> list[VectorSearchResult]:
    from vector_stores import get_vector_store_adapter

    backend = settings.vector_db.default
    vector_store = get_vector_store_adapter(settings=settings)

    with trace_span(
        "retrieval.vector_search",
        knowledge_base_id=str(knowledge_base_id),
        top_k=top_k,
        backend=backend.value,
    ):
        with track_duration(VECTOR_SEARCH_DURATION_SECONDS, backend=backend.value):
            results = await vector_store.search(
                collection_name=collection_name,
                query_vector=query_vector,
                top_k=top_k,
                filters=filters,
                with_vectors=with_vectors,
                score_threshold=score_threshold,
            )

    logger.debug(
        "vector_search_complete",
        knowledge_base_id=str(knowledge_base_id),
        results=len(results),
        top_k=top_k,
    )
    return results


def engine_top_k(
    query_vector: list[float],
    vectors: list[list[float]],
    ids: list[str],
    k: int,
    metric: str = "cosine",
) -> list[tuple[str, float]]:
    if neuralcore_engine is None or not vectors:
        return []
    func = getattr(neuralcore_engine, "py_top_k_by_similarity", None)
    if func is None:
        return []
    try:
        raw = func(query_vector, vectors, k, metric)
        return [(ids[index], float(score)) for index, score in raw if index < len(ids)]
    except Exception:
        return []
    