# knowledge_graph/graph_utils.py
from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

from knowledge_graph.graph_store import KGEdge, KGNode


def node_id(knowledge_base_id: str, label: str, node_type: str) -> str:
    key = f"{knowledge_base_id}:{node_type}:{label.lower().strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def edge_id(source_id: str, target_id: str, relation: str) -> str:
    key = f"{source_id}:{relation}:{target_id}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


def normalize_label(label: str) -> str:
    label = label.strip()
    label = re.sub(r"\s+", " ", label)
    return label


def merge_nodes(primary: KGNode, secondary: KGNode) -> KGNode:
    merged_properties = {**secondary.properties, **primary.properties}
    merged_source_ids = list(set(primary.source_ids + secondary.source_ids))
    merged_confidence = max(primary.confidence, secondary.confidence)
    return KGNode(
        id=primary.id,
        label=primary.label,
        node_type=primary.node_type,
        knowledge_base_id=primary.knowledge_base_id,
        properties=merged_properties,
        source_ids=merged_source_ids,
        confidence=merged_confidence,
    )


def build_adjacency(
    nodes: list[KGNode], edges: list[KGEdge]
) -> dict[str, list[tuple[str, str, float]]]:
    adjacency: dict[str, list[tuple[str, str, float]]] = {node.id: [] for node in nodes}
    for edge in edges:
        if edge.source_id in adjacency:
            adjacency[edge.source_id].append((edge.target_id, edge.relation, edge.weight))
        if edge.target_id in adjacency:
            adjacency[edge.target_id].append((edge.source_id, edge.relation, edge.weight))
    return adjacency


def find_connected_components(
    nodes: list[KGNode], edges: list[KGEdge]
) -> list[list[str]]:
    adjacency = build_adjacency(nodes, edges)
    visited: set[str] = set()
    components: list[list[str]] = []

    def dfs(node_id_: str, component: list[str]) -> None:
        visited.add(node_id_)
        component.append(node_id_)
        for neighbor_id, _, _ in adjacency.get(node_id_, []):
            if neighbor_id not in visited:
                dfs(neighbor_id, component)

    for node in nodes:
        if node.id not in visited:
            component: list[str] = []
            dfs(node.id, component)
            if component:
                components.append(component)

    return components


def compute_degree_centrality(
    nodes: list[KGNode], edges: list[KGEdge]
) -> dict[str, float]:
    degree: dict[str, int] = {node.id: 0 for node in nodes}
    for edge in edges:
        degree[edge.source_id] = degree.get(edge.source_id, 0) + 1
        degree[edge.target_id] = degree.get(edge.target_id, 0) + 1
    max_degree = max(degree.values(), default=1)
    return {node_id_: count / max_degree for node_id_, count in degree.items()}


def extract_triples(
    nodes: list[KGNode], edges: list[KGEdge]
) -> list[tuple[str, str, str]]:
    node_map = {node.id: node.label for node in nodes}
    return [
        (node_map.get(edge.source_id, edge.source_id), edge.relation, node_map.get(edge.target_id, edge.target_id))
        for edge in edges
        if edge.source_id in node_map and edge.target_id in node_map
    ]


def triples_to_text(triples: list[tuple[str, str, str]]) -> str:
    return "\n".join(f"{subj} {pred.replace('_', ' ')} {obj}." for subj, pred, obj in triples)
