# graphrag/visualization/graph_metrics.py
from __future__ import annotations

from typing import Any

from graphrag.graph_store import GraphEdge, GraphNode
from graphrag.relationships.scorer import compute_pagerank


def compute_graph_density(nodes: list[GraphNode], edges: list[GraphEdge]) -> float:
    n = len(nodes)
    if n <= 1:
        return 0.0
    max_edges = n * (n - 1)
    return len(edges) / max_edges if max_edges > 0 else 0.0


def compute_clustering_coefficient(nodes: list[GraphNode], edges: list[GraphEdge]) -> float:
    if not nodes:
        return 0.0
    adjacency: dict[str, set[str]] = {node.id: set() for node in nodes}
    for edge in edges:
        adjacency[edge.source_id].add(edge.target_id)
        adjacency[edge.target_id].add(edge.source_id)

    coefficients: list[float] = []
    for node in nodes:
        neighbors = adjacency[node.id]
        k = len(neighbors)
        if k < 2:
            coefficients.append(0.0)
            continue
        actual_connections = sum(
            1 for nb_a in neighbors for nb_b in neighbors
            if nb_a != nb_b and nb_b in adjacency[nb_a]
        )
        coefficients.append(actual_connections / (k * (k - 1)))
    return sum(coefficients) / len(coefficients) if coefficients else 0.0


def compute_full_graph_metrics(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
) -> dict[str, Any]:
    pagerank = compute_pagerank(nodes, edges)
    top_entities = sorted(pagerank.items(), key=lambda item: item[1], reverse=True)[:10]
    node_map = {node.id: node for node in nodes}
    entity_type_dist: dict[str, int] = {}
    for node in nodes:
        entity_type_dist[node.entity_type.value] = entity_type_dist.get(node.entity_type.value, 0) + 1
    relation_type_dist: dict[str, int] = {}
    for edge in edges:
        relation_type_dist[edge.relation_type.value] = relation_type_dist.get(edge.relation_type.value, 0) + 1

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "density": compute_graph_density(nodes, edges),
        "avg_clustering_coefficient": compute_clustering_coefficient(nodes, edges),
        "avg_confidence": sum(node.confidence for node in nodes) / max(len(nodes), 1),
        "entity_type_distribution": entity_type_dist,
        "relation_type_distribution": relation_type_dist,
        "top_entities_by_pagerank": [
            {"id": node_id, "name": node_map[node_id].name if node_id in node_map else node_id, "pagerank": score}
            for node_id, score in top_entities
        ],
    }
