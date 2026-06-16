# graphrag/visualization/graph_export.py
from __future__ import annotations

import json
from typing import Any

from graphrag.graph_store import GraphEdge, GraphNode


def export_to_cytoscape(nodes: list[GraphNode], edges: list[GraphEdge]) -> dict[str, Any]:
    elements: list[dict[str, Any]] = []
    for node in nodes:
        elements.append({
            "data": {
                "id": node.id,
                "label": node.name,
                "type": node.entity_type.value,
                "description": node.description,
                "confidence": node.confidence,
            },
            "classes": node.entity_type.value,
        })
    for edge in edges:
        elements.append({
            "data": {
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "label": edge.relation_type.value.replace("_", " "),
                "weight": edge.weight,
                "confidence": edge.confidence,
            },
        })
    return {"elements": elements}


def export_to_d3(nodes: list[GraphNode], edges: list[GraphEdge]) -> dict[str, Any]:
    return {
        "nodes": [
            {
                "id": node.id,
                "name": node.name,
                "type": node.entity_type.value,
                "description": node.description,
                "confidence": node.confidence,
            }
            for node in nodes
        ],
        "links": [
            {
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "relation": edge.relation_type.value,
                "weight": edge.weight,
            }
            for edge in edges
        ],
    }


def export_to_graphml(nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
    lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<graphml xmlns="http://graphml.graphdrawing.org/graphml">',
        '<key id="name" for="node" attr.name="name" attr.type="string"/>',
        '<key id="type" for="node" attr.name="type" attr.type="string"/>',
        '<key id="relation" for="edge" attr.name="relation" attr.type="string"/>',
        '<key id="weight" for="edge" attr.name="weight" attr.type="double"/>',
        '<graph id="G" edgedefault="directed">',
    ]
    for node in nodes:
        lines.append(f'  <node id="{node.id}">')
        lines.append(f'    <data key="name">{node.name}</data>')
        lines.append(f'    <data key="type">{node.entity_type.value}</data>')
        lines.append("  </node>")
    for edge in edges:
        lines.append(f'  <edge id="{edge.id}" source="{edge.source_id}" target="{edge.target_id}">')
        lines.append(f'    <data key="relation">{edge.relation_type.value}</data>')
        lines.append(f'    <data key="weight">{edge.weight}</data>')
        lines.append("  </edge>")
    lines += ["</graph>", "</graphml>"]
    return "\n".join(lines)
