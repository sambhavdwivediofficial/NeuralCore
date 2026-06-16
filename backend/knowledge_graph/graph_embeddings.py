# knowledge_graph/graph_embeddings.py
from __future__ import annotations

import asyncio
from typing import Any

from knowledge_graph.graph_store import KGNode, KnowledgeGraphStore
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.knowledge_graph.embeddings")

_COLLECTION_SUFFIX = "_kg"


def _kg_collection_name(knowledge_base_id: str) -> str:
    return f"nc_{knowledge_base_id.replace('-', '')}{_COLLECTION_SUFFIX}"


async def embed_kg_nodes(
    nodes: list[KGNode],
    knowledge_base_id: str,
    settings: Settings,
) -> int:
    if not nodes:
        return 0

    from embeddings.embedding_factory import get_embedding_provider
    from vector_stores import get_vector_store_adapter

    provider = get_embedding_provider(settings=settings)
    vector_store = get_vector_store_adapter(settings=settings)
    collection_name = _kg_collection_name(knowledge_base_id)

    try:
        if not await vector_store.collection_exists(collection_name):
            dimension = provider.get_dimension()
            await vector_store.create_collection(collection_name, dimension)
    except Exception as exc:
        logger.error("kg_collection_create_failed", error=str(exc))
        return 0

    batch_size = settings.embeddings.pipeline.batch_size
    embedded_count = 0

    for start in range(0, len(nodes), batch_size):
        batch = nodes[start : start + batch_size]
        text_inputs: list[str] = []
        for node in batch:
            desc = node.properties.get("description", "")
            aliases = node.properties.get("aliases", [])
            alias_str = f" (also known as: {', '.join(aliases)})" if aliases else ""
            text_inputs.append(f"{node.label}{alias_str}: {desc}" if desc else node.label)

        try:
            vectors = await provider.embed_documents(text_inputs)
        except Exception as exc:
            logger.warning("kg_embed_batch_failed", start=start, error=str(exc))
            continue

        points = [
            {
                "id": node.id,
                "vector": vector,
                "metadata": {
                    "label": node.label,
                    "node_type": node.node_type,
                    "knowledge_base_id": knowledge_base_id,
                    "description": node.properties.get("description", ""),
                    "text": text_inputs[i],
                },
            }
            for i, (node, vector) in enumerate(zip(batch, vectors))
        ]

        try:
            await vector_store.upsert(collection_name, points)
            embedded_count += len(batch)
        except Exception as exc:
            logger.warning("kg_vector_upsert_failed", error=str(exc))

    logger.info("kg_nodes_embedded", count=embedded_count, kb_id=knowledge_base_id)
    return embedded_count


async def search_kg_nodes_by_vector(
    query: str,
    knowledge_base_id: str,
    settings: Settings,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    from embeddings.embedding_factory import get_embedding_provider
    from vector_stores import get_vector_store_adapter

    provider = get_embedding_provider(settings=settings)
    vector_store = get_vector_store_adapter(settings=settings)
    collection_name = _kg_collection_name(knowledge_base_id)

    try:
        query_vector = await provider.embed_query(query)
        if not await vector_store.collection_exists(collection_name):
            return []
        results = await vector_store.search(collection_name, query_vector, top_k=top_k)
        return [{"id": r.id, "score": r.score, "metadata": r.metadata} for r in results]
    except Exception as exc:
        logger.warning("kg_vector_search_failed", error=str(exc))
        return []
    