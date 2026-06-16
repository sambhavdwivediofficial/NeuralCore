# retrieval/multimodal_search.py
from __future__ import annotations

import uuid
from typing import Any

from monitoring.logging import get_logger
from settings import Settings
from vector_stores.base import VectorSearchResult

logger = get_logger("neuralcore.retrieval.multimodal_search")


async def embed_image(image_bytes: bytes, settings: Settings) -> list[float]:
    config = settings.retrieval.multimodal_search
    if not config.enabled:
        raise ValueError("multimodal search is not enabled")

    from embeddings.embedding_factory import get_embedding_provider

    provider = get_embedding_provider(settings=settings, provider_name=config.image_embedding_provider)
    import base64

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return await provider.embed_query(f"data:image/jpeg;base64,{b64}")


async def multimodal_search(
    *,
    image_bytes: bytes | None = None,
    text_query: str | None = None,
    knowledge_base_id: uuid.UUID,
    collection_name: str,
    top_k: int = 10,
    settings: Settings,
) -> list[VectorSearchResult]:
    if not settings.retrieval.multimodal_search.enabled:
        return []

    from embeddings.embedding_factory import get_embedding_provider
    from retrieval.vector_search import vector_search

    query_vectors: list[list[float]] = []

    if image_bytes is not None:
        try:
            image_vector = await embed_image(image_bytes, settings)
            query_vectors.append(image_vector)
        except Exception as exc:
            logger.error("image_embedding_failed", error=str(exc))

    if text_query is not None:
        try:
            provider = get_embedding_provider(settings=settings)
            text_vector = await provider.embed_query(text_query)
            query_vectors.append(text_vector)
        except Exception as exc:
            logger.error("text_embedding_failed", error=str(exc))

    if not query_vectors:
        return []

    if len(query_vectors) == 1:
        combined_vector = query_vectors[0]
    else:
        dim = len(query_vectors[0])
        combined_vector = [
            (query_vectors[0][i] + query_vectors[1][i]) / 2.0 for i in range(dim)
        ]
        norm = sum(v * v for v in combined_vector) ** 0.5
        if norm > 0:
            combined_vector = [v / norm for v in combined_vector]

    return await vector_search(
        query_vector=combined_vector,
        knowledge_base_id=knowledge_base_id,
        collection_name=collection_name,
        top_k=top_k,
        settings=settings,
    )
