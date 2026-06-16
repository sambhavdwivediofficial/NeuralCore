# graphrag/relationships/validator.py
from __future__ import annotations

from graphrag.graph_store import GraphEdge, GraphNode, RelationType
from graphrag.relationships.extractor import ExtractedRelationship


def validate_relationship(rel: ExtractedRelationship, entity_name_to_id: dict[str, str]) -> bool:
    if not rel.source_name or not rel.target_name:
        return False
    if rel.source_name == rel.target_name:
        return False
    if rel.source_name.lower() not in {k.lower() for k in entity_name_to_id}:
        return False
    if rel.target_name.lower() not in {k.lower() for k in entity_name_to_id}:
        return False
    if not (0.0 <= rel.confidence <= 1.0):
        return False
    if not (0.0 <= rel.weight <= 1.0):
        return False
    return True


def filter_low_confidence_edges(
    edges: list[GraphEdge], min_confidence: float = 0.3, min_weight: float = 0.1
) -> list[GraphEdge]:
    return [edge for edge in edges if edge.confidence >= min_confidence and edge.weight >= min_weight]


def deduplicate_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    seen: dict[tuple[str, str, str], GraphEdge] = {}
    for edge in edges:
        key = (edge.source_id, edge.target_id, edge.relation_type.value)
        if key not in seen or edge.confidence > seen[key].confidence:
            seen[key] = edge
    return list(seen.values())
