# graphrag/relationships/scorer.py
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from graphrag.graph_store import GraphEdge, GraphNode, RelationType


def compute_edge_centrality(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
) -> dict[str, float]:
    degree: dict[str, int] = defaultdict(int)
    for edge in edges:
        degree[edge.source_id] += 1
        degree[edge.target_id] += 1

    max_degree = max(degree.values(), default=1)
    return {node_id: degree.get(node_id, 0) / max_degree for node_id in {node.id for node in nodes}}


def compute_pagerank(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    damping: float = 0.85,
    iterations: int = 20,
) -> dict[str, float]:
    if not nodes:
        return {}

    node_ids = [node.id for node in nodes]
    n = len(node_ids)
    rank: dict[str, float] = {node_id: 1.0 / n for node_id in node_ids}

    out_links: dict[str, list[str]] = defaultdict(list)
    in_links: dict[str, list[str]] = defaultdict(list)
    edge_weights: dict[tuple[str, str], float] = {}

    for edge in edges:
        out_links[edge.source_id].append(edge.target_id)
        in_links[edge.target_id].append(edge.source_id)
        edge_weights[(edge.source_id, edge.target_id)] = edge.weight

    for _ in range(iterations):
        new_rank: dict[str, float] = {}
        for node_id in node_ids:
            incoming_score = sum(
                rank.get(src, 0.0) * edge_weights.get((src, node_id), 1.0) / max(len(out_links[src]), 1)
                for src in in_links.get(node_id, [])
            )
            new_rank[node_id] = (1 - damping) / n + damping * incoming_score
        rank = new_rank

    return rank


def score_relationship_relevance(
    edge: GraphEdge,
    query_node_ids: set[str],
    pagerank: dict[str, float],
) -> float:
    base = edge.weight * edge.confidence
    pr_boost = (pagerank.get(edge.source_id, 0.0) + pagerank.get(edge.target_id, 0.0)) / 2.0
    proximity_bonus = 0.3 if (edge.source_id in query_node_ids or edge.target_id in query_node_ids) else 0.0
    return base * (1.0 + pr_boost) + proximity_bonus
