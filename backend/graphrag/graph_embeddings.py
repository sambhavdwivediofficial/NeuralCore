# graphrag/graph_embeddings.py
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from graphrag.graph_store import GraphNode, GraphStore
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.graph_embeddings")


async def embed_nodes(
    nodes: list[GraphNode],
    knowledge_base_id: str,
    store: GraphStore,
    settings: Settings,
    collection_suffix: str = "_graph",
) -> int:
    if not nodes:
        return 0

    from embeddings.embedding_factory import get_embedding_provider
    from vector_stores import get_vector_store_adapter

    provider = get_embedding_provider(settings=settings)
    vector_store = get_vector_store_adapter(settings=settings)
    collection_name = f"nc_{knowledge_base_id.replace('-', '')}{collection_suffix}"

    try:
        if not await vector_store.collection_exists(collection_name):
            dimension = provider.get_dimension()
            await vector_store.create_collection(collection_name, dimension)
    except Exception as exc:
        logger.warning("graph_collection_create_failed", error=str(exc))
        return 0

    batch_size = settings.embeddings.pipeline.batch_size
    embedded_count = 0

    for start in range(0, len(nodes), batch_size):
        batch = nodes[start : start + batch_size]
        texts = [f"{node.name}: {node.description}" if node.description else node.name for node in batch]

        try:
            vectors = await provider.embed_documents(texts)
        except Exception as exc:
            logger.warning("graph_node_embedding_failed", batch_start=start, error=str(exc))
            continue

        points = [
            {
                "id": node.id,
                "vector": vector,
                "metadata": {
                    "name": node.name,
                    "entity_type": node.entity_type.value,
                    "knowledge_base_id": knowledge_base_id,
                    "description": node.description,
                },
            }
            for node, vector in zip(batch, vectors)
        ]

        try:
            await vector_store.upsert(collection_name, points)
            embedded_count += len(batch)
        except Exception as exc:
            logger.warning("graph_vector_upsert_failed", error=str(exc))

    return embedded_count


async def search_similar_nodes(
    query: str,
    knowledge_base_id: str,
    settings: Settings,
    top_k: int = 10,
    collection_suffix: str = "_graph",
) -> list[dict[str, Any]]:
    from embeddings.embedding_factory import get_embedding_provider
    from vector_stores import get_vector_store_adapter

    provider = get_embedding_provider(settings=settings)
    vector_store = get_vector_store_adapter(settings=settings)
    collection_name = f"nc_{knowledge_base_id.replace('-', '')}{collection_suffix}"

    try:
        query_vector = await provider.embed_query(query)
        results = await vector_store.search(collection_name, query_vector, top_k=top_k)
        return [{"id": result.id, "score": result.score, "metadata": result.metadata} for result in results]
    except Exception as exc:
        logger.warning("graph_node_vector_search_failed", error=str(exc))
        return []
    