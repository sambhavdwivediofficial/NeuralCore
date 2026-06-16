# graphrag/entities/entity_resolver.py
from __future__ import annotations

import hashlib
import uuid
from typing import Any

from graphrag.graph_store import EntityType, GraphNode, GraphStore


def new_node_id() -> str:
    return uuid.uuid4().hex


def deterministic_node_id(knowledge_base_id: str, name: str, entity_type: str) -> str:
    key = f"{knowledge_base_id}:{entity_type}:{name.lower().strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]


async def resolve_duplicates(
    knowledge_base_id: str,
    store: GraphStore,
    min_confidence: float = 0.5,
) -> int:
    engine_nodes: dict[str, GraphNode] = {}

    from database.connection import get_engine
    from sqlalchemy import text

    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT n1.id as id1, n2.id as id2
                FROM graph_nodes n1
                JOIN graph_nodes n2 ON n1.id < n2.id
                WHERE n1.knowledge_base_id = :kb_id
                AND n2.knowledge_base_id = :kb_id
                AND n1.entity_type = n2.entity_type
                AND (
                    LOWER(n1.name) = LOWER(n2.name)
                    OR n1.aliases @> to_jsonb(ARRAY[LOWER(n2.name)])
                    OR n2.aliases @> to_jsonb(ARRAY[LOWER(n1.name)])
                )
            """),
            {"kb_id": knowledge_base_id},
        )
        duplicate_pairs = result.mappings().all()

    merged_count = 0
    for pair in duplicate_pairs:
        primary_id = pair["id1"]
        secondary_id = pair["id2"]
        primary = await store.get_node(primary_id)
        secondary = await store.get_node(secondary_id)
        if primary is None or secondary is None:
            continue

        primary.aliases = list(set(primary.aliases + secondary.aliases + [secondary.name]))
        primary.source_doc_ids = list(set(primary.source_doc_ids + secondary.source_doc_ids))
        primary.confidence = max(primary.confidence, secondary.confidence)
        if not primary.description and secondary.description:
            primary.description = secondary.description
        await store.upsert_node(primary)

        engine_local = get_engine()
        async with engine_local.begin() as conn:
            await conn.execute(
                text("UPDATE graph_edges SET source_id = :primary WHERE source_id = :secondary AND knowledge_base_id = :kb_id"),
                {"primary": primary_id, "secondary": secondary_id, "kb_id": knowledge_base_id},
            )
            await conn.execute(
                text("UPDATE graph_edges SET target_id = :primary WHERE target_id = :secondary AND knowledge_base_id = :kb_id"),
                {"primary": primary_id, "secondary": secondary_id, "kb_id": knowledge_base_id},
            )
            await conn.execute(
                text("DELETE FROM graph_nodes WHERE id = :secondary"),
                {"secondary": secondary_id},
            )
        merged_count += 1

    return merged_count
