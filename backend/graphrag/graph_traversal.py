# graphrag/graph_traversal.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from graphrag.graph_store import GraphEdge, GraphNode, GraphStore
from monitoring.logging import get_logger

logger = get_logger("neuralcore.graphrag.traversal")


@dataclass(slots=True)
class TraversalResult:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    paths: list[list[str]] = field(default_factory=list)
    depth_reached: int = 0


async def bfs_traversal(
    start_node_ids: list[str],
    knowledge_base_id: str,
    store: GraphStore,
    max_hops: int = 3,
    max_nodes: int = 100,
) -> TraversalResult:
    visited_ids: set[str] = set()
    all_nodes: list[GraphNode] = []
    all_edges: list[GraphEdge] = []
    paths: list[list[str]] = []
    queue: list[tuple[str, int, list[str]]] = [(node_id, 0, [node_id]) for node_id in start_node_ids]
    depth_reached = 0

    while queue and len(visited_ids) < max_nodes:
        current_id, depth, path = queue.pop(0)
        if current_id in visited_ids or depth > max_hops:
            continue

        visited_ids.add(current_id)
        depth_reached = max(depth_reached, depth)

        node = await store.get_node(current_id)
        if node is not None:
            all_nodes.append(node)
            if depth == max_hops or len(visited_ids) >= max_nodes:
                paths.append(path)

        if depth < max_hops:
            neighbors, edges = await store.get_neighbors(
                current_id, knowledge_base_id, max_neighbors=50
            )
            for edge in edges:
                if edge not in all_edges:
                    all_edges.append(edge)

            for neighbor in neighbors:
                if neighbor.id not in visited_ids:
                    queue.append((neighbor.id, depth + 1, path + [neighbor.id]))

    return TraversalResult(
        nodes=all_nodes,
        edges=all_edges,
        paths=paths,
        depth_reached=depth_reached,
    )


async def shortest_path(
    source_id: str,
    target_id: str,
    knowledge_base_id: str,
    store: GraphStore,
    max_hops: int = 6,
) -> list[str] | None:
    if source_id == target_id:
        return [source_id]

    visited: set[str] = {source_id}
    queue: list[list[str]] = [[source_id]]

    while queue:
        path = queue.pop(0)
        current = path[-1]
        if len(path) > max_hops + 1:
            continue

        neighbors, _ = await store.get_neighbors(current, knowledge_base_id, max_neighbors=50)
        for neighbor in neighbors:
            if neighbor.id == target_id:
                return path + [neighbor.id]
            if neighbor.id not in visited:
                visited.add(neighbor.id)
                queue.append(path + [neighbor.id])

    return None
