# graphrag/graph_search.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from graphrag.graph_embeddings import search_similar_nodes
from graphrag.graph_store import GraphNode, GraphStore
from graphrag.graph_traversal import TraversalResult, bfs_traversal
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.search")


@dataclass(slots=True)
class GraphSearchResult:
    id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    depth: int = 0
    path: list[str] = field(default_factory=list)


async def search_graph(
    query: str,
    knowledge_base_id: str,
    settings: Settings,
    top_k: int = 10,
    max_hops: int | None = None,
) -> list[GraphSearchResult]:
    hops = max_hops or settings.retrieval.graph_search.max_hops
    store = GraphStore()

    seed_nodes = await search_similar_nodes(
        query=query,
        knowledge_base_id=knowledge_base_id,
        settings=settings,
        top_k=min(top_k, settings.retrieval.graph_search.max_entities_per_hop),
    )

    if not seed_nodes:
        text_nodes = await store.search_nodes_by_name(knowledge_base_id, query, limit=top_k)
        seed_nodes = [
            {"id": node.id, "score": node.confidence, "metadata": {"name": node.name, "description": node.description}}
            for node in text_nodes
        ]

    if not seed_nodes:
        return []

    seed_ids = [item["id"] for item in seed_nodes]
    traversal: TraversalResult = await bfs_traversal(
        start_node_ids=seed_ids,
        knowledge_base_id=knowledge_base_id,
        store=store,
        max_hops=hops,
        max_nodes=top_k * 5,
    )

    seed_score_map = {item["id"]: item["score"] for item in seed_nodes}
    results: list[GraphSearchResult] = []

    for node in traversal.nodes:
        base_score = seed_score_map.get(node.id, 0.0)
        depth_penalty = 0.1 * min(
            next((depth for start_id in seed_ids for depth in [0] if node.id == start_id), hops),
            hops,
        )
        final_score = base_score * (1.0 - depth_penalty) * node.confidence
        results.append(
            GraphSearchResult(
                id=node.id,
                score=final_score,
                metadata={
                    "name": node.name,
                    "entity_type": node.entity_type.value,
                    "description": node.description,
                    "knowledge_base_id": knowledge_base_id,
                    "text": f"{node.name}: {node.description}",
                },
                depth=0 if node.id in seed_ids else 1,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]
