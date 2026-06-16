# graphrag/visualization/graph_renderer.py
from __future__ import annotations

from typing import Any

from graphrag.visualization.graph_export import export_to_cytoscape, export_to_d3
from graphrag.visualization.graph_metrics import compute_full_graph_metrics
from graphrag.graph_store import GraphEdge, GraphNode


def render_graph_summary(
    nodes: list[GraphNode],
    edges: list[GraphEdge],
    format: str = "cytoscape",
) -> dict[str, Any]:
    metrics = compute_full_graph_metrics(nodes, edges)
    if format == "d3":
        graph_data = export_to_d3(nodes, edges)
    else:
        graph_data = export_to_cytoscape(nodes, edges)

    return {
        "graph": graph_data,
        "metrics": metrics,
        "format": format,
    }
