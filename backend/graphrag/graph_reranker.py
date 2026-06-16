# graphrag/graph_reranker.py
from __future__ import annotations

from typing import Any

from graphrag.graph_search import GraphSearchResult
from graphrag.graph_store import GraphStore
from graphrag.relationships.scorer import compute_pagerank, score_relationship_relevance
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.reranker")


async def rerank_graph_results(
    results: list[GraphSearchResult],
    knowledge_base_id: str,
    store: GraphStore,
    settings: Settings,
) -> list[GraphSearchResult]:
    if not results:
        return []

    node_ids = [result.id for result in results]
    from graphrag.graph_traversal import bfs_traversal

    traversal = await bfs_traversal(
        start_node_ids=node_ids,
        knowledge_base_id=knowledge_base_id,
        store=store,
        max_hops=1,
        max_nodes=200,
    )

    pagerank = compute_pagerank(traversal.nodes, traversal.edges)
    query_node_ids = set(node_ids)

    edge_scores = {
        edge.id: score_relationship_relevance(edge, query_node_ids, pagerank)
        for edge in traversal.edges
    }

    node_edge_boost: dict[str, float] = {}
    for edge in traversal.edges:
        boost = edge_scores.get(edge.id, 0.0)
        node_edge_boost[edge.source_id] = node_edge_boost.get(edge.source_id, 0.0) + boost
        node_edge_boost[edge.target_id] = node_edge_boost.get(edge.target_id, 0.0) + boost

    reranked: list[GraphSearchResult] = []
    for result in results:
        pr = pagerank.get(result.id, 0.0)
        edge_boost = min(node_edge_boost.get(result.id, 0.0) * 0.1, 0.3)
        new_score = result.score * (1.0 + pr) + edge_boost
        reranked.append(
            GraphSearchResult(
                id=result.id,
                score=new_score,
                metadata=result.metadata,
                depth=result.depth,
                path=result.path,
            )
        )

    reranked.sort(key=lambda r: r.score, reverse=True)
    return reranked
