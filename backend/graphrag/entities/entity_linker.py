# graphrag/entities/entity_linker.py
from __future__ import annotations

from typing import Any

from graphrag.entities.entity_extractor import ExtractedEntity
from graphrag.graph_store import EntityType, GraphNode, GraphStore
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.entity_linker")

_SIMILARITY_THRESHOLD = 0.85


def _normalize_name(name: str) -> str:
    return name.lower().strip().replace("-", " ").replace("_", " ")


def _names_overlap(a: str, b: str, aliases_a: list[str], aliases_b: list[str]) -> bool:
    norm_a = _normalize_name(a)
    norm_b = _normalize_name(b)
    if norm_a == norm_b:
        return True
    all_a = {norm_a} | {_normalize_name(alias) for alias in aliases_a}
    all_b = {norm_b} | {_normalize_name(alias) for alias in aliases_b}
    return bool(all_a & all_b)


async def link_entities(
    extracted: list[ExtractedEntity],
    knowledge_base_id: str,
    store: GraphStore,
    settings: Settings,
) -> list[GraphNode]:
    linked: list[GraphNode] = []

    for entity in extracted:
        try:
            entity_type = EntityType(entity.entity_type)
        except ValueError:
            entity_type = EntityType.OTHER

        existing = await store.get_node_by_name(knowledge_base_id, entity.name, entity_type)

        if existing is not None:
            existing.aliases = list(set(existing.aliases + entity.aliases))
            existing.source_doc_ids = list(set(existing.source_doc_ids + [entity.chunk_id]))
            existing.confidence = max(existing.confidence, entity.confidence)
            await store.upsert_node(existing)
            linked.append(existing)
        else:
            similar = await store.search_nodes_by_name(knowledge_base_id, entity.name, limit=5)
            matched: GraphNode | None = None
            for candidate in similar:
                if candidate.entity_type == entity_type and _names_overlap(
                    entity.name, candidate.name, entity.aliases, candidate.aliases
                ):
                    matched = candidate
                    break

            if matched is not None:
                matched.aliases = list(set(matched.aliases + [entity.name] + entity.aliases))
                matched.source_doc_ids = list(set(matched.source_doc_ids + [entity.chunk_id]))
                matched.confidence = max(matched.confidence, entity.confidence)
                await store.upsert_node(matched)
                linked.append(matched)
            else:
                from graphrag.entities.entity_resolver import new_node_id

                new_node = GraphNode(
                    id=new_node_id(),
                    name=entity.name,
                    entity_type=entity_type,
                    knowledge_base_id=knowledge_base_id,
                    description=entity.description,
                    aliases=entity.aliases,
                    properties={},
                    source_doc_ids=[entity.chunk_id],
                    confidence=entity.confidence,
                )
                await store.upsert_node(new_node)
                linked.append(new_node)

    return linked
