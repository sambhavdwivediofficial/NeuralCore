# knowledge_graph/graph_store.py
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from database.connection import get_engine
from monitoring.logging import get_logger
from sqlalchemy import text

logger = get_logger("neuralcore.knowledge_graph.store")


@dataclass(slots=True)
class KGNode:
    id: str
    label: str
    node_type: str
    knowledge_base_id: str
    properties: dict[str, Any] = field(default_factory=dict)
    source_ids: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "node_type": self.node_type,
            "knowledge_base_id": self.knowledge_base_id,
            "properties": self.properties,
            "source_ids": self.source_ids,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KGNode":
        return cls(
            id=data["id"],
            label=data["label"],
            node_type=data["node_type"],
            knowledge_base_id=data["knowledge_base_id"],
            properties=data.get("properties", {}),
            source_ids=data.get("source_ids", []),
            confidence=data.get("confidence", 1.0),
        )


@dataclass(slots=True)
class KGEdge:
    id: str
    source_id: str
    target_id: str
    relation: str
    knowledge_base_id: str
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    source_ids: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "knowledge_base_id": self.knowledge_base_id,
            "properties": self.properties,
            "weight": self.weight,
            "source_ids": self.source_ids,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KGEdge":
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation=data["relation"],
            knowledge_base_id=data["knowledge_base_id"],
            properties=data.get("properties", {}),
            weight=data.get("weight", 1.0),
            source_ids=data.get("source_ids", []),
            confidence=data.get("confidence", 1.0),
        )


class KnowledgeGraphStore:
    async def upsert_node(self, node: KGNode) -> KGNode:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO kg_nodes
                        (id, knowledge_base_id, label, node_type, properties, source_ids, confidence, created_at, updated_at)
                    VALUES
                        (:id, :kb_id, :label, :node_type, :properties::jsonb, :source_ids::jsonb, :confidence, NOW(), NOW())
                    ON CONFLICT (id)
                    DO UPDATE SET
                        properties = kg_nodes.properties || EXCLUDED.properties,
                        source_ids = kg_nodes.source_ids || EXCLUDED.source_ids,
                        confidence = GREATEST(kg_nodes.confidence, EXCLUDED.confidence),
                        updated_at = NOW()
                """),
                {
                    "id": node.id,
                    "kb_id": node.knowledge_base_id,
                    "label": node.label,
                    "node_type": node.node_type,
                    "properties": json.dumps(node.properties),
                    "source_ids": json.dumps(list(set(node.source_ids))),
                    "confidence": node.confidence,
                },
            )
        return node

    async def upsert_edge(self, edge: KGEdge) -> KGEdge:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO kg_edges
                        (id, knowledge_base_id, source_id, target_id, relation, properties, weight, source_ids, confidence, created_at, updated_at)
                    VALUES
                        (:id, :kb_id, :source_id, :target_id, :relation, :properties::jsonb, :weight, :source_ids::jsonb, :confidence, NOW(), NOW())
                    ON CONFLICT (id) DO NOTHING
                """),
                {
                    "id": edge.id,
                    "kb_id": edge.knowledge_base_id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relation": edge.relation,
                    "properties": json.dumps(edge.properties),
                    "weight": edge.weight,
                    "source_ids": json.dumps(list(set(edge.source_ids))),
                    "confidence": edge.confidence,
                },
            )
        return edge

    async def get_node(self, node_id: str) -> KGNode | None:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT * FROM kg_nodes WHERE id = :id"), {"id": node_id}
            )
            row = result.mappings().first()
        return KGNode.from_dict(dict(row)) if row else None

    async def get_nodes_by_label(
        self, knowledge_base_id: str, label: str, node_type: str | None = None, limit: int = 10
    ) -> list[KGNode]:
        engine = get_engine()
        query = "SELECT * FROM kg_nodes WHERE knowledge_base_id = :kb_id AND LOWER(label) LIKE LOWER(:pattern)"
        params: dict[str, Any] = {"kb_id": knowledge_base_id, "pattern": f"%{label}%"}
        if node_type:
            query += " AND node_type = :node_type"
            params["node_type"] = node_type
        query += " ORDER BY confidence DESC LIMIT :limit"
        params["limit"] = limit
        async with engine.connect() as conn:
            result = await conn.execute(text(query), params)
            return [KGNode.from_dict(dict(row)) for row in result.mappings().all()]

    async def get_neighbors(
        self, node_id: str, knowledge_base_id: str, max_depth: int = 1, max_neighbors: int = 50
    ) -> tuple[list[KGNode], list[KGEdge]]:
        engine = get_engine()
        async with engine.connect() as conn:
            edges_result = await conn.execute(
                text("""
                    SELECT * FROM kg_edges
                    WHERE knowledge_base_id = :kb_id
                    AND (source_id = :node_id OR target_id = :node_id)
                    ORDER BY weight DESC, confidence DESC
                    LIMIT :limit
                """),
                {"kb_id": knowledge_base_id, "node_id": node_id, "limit": max_neighbors},
            )
            edges = [KGEdge.from_dict(dict(row)) for row in edges_result.mappings().all()]

            neighbor_ids = {e.target_id if e.source_id == node_id else e.source_id for e in edges}
            neighbor_ids.discard(node_id)

            nodes: list[KGNode] = []
            if neighbor_ids:
                nodes_result = await conn.execute(
                    text("SELECT * FROM kg_nodes WHERE id = ANY(:ids)"),
                    {"ids": list(neighbor_ids)},
                )
                nodes = [KGNode.from_dict(dict(row)) for row in nodes_result.mappings().all()]

        return nodes, edges

    async def get_all_nodes(
        self, knowledge_base_id: str, node_type: str | None = None, limit: int = 1000
    ) -> list[KGNode]:
        engine = get_engine()
        query = "SELECT * FROM kg_nodes WHERE knowledge_base_id = :kb_id"
        params: dict[str, Any] = {"kb_id": knowledge_base_id}
        if node_type:
            query += " AND node_type = :node_type"
            params["node_type"] = node_type
        query += " ORDER BY confidence DESC LIMIT :limit"
        params["limit"] = limit
        async with engine.connect() as conn:
            result = await conn.execute(text(query), params)
            return [KGNode.from_dict(dict(row)) for row in result.mappings().all()]

    async def get_all_edges(
        self, knowledge_base_id: str, relation: str | None = None, limit: int = 5000
    ) -> list[KGEdge]:
        engine = get_engine()
        query = "SELECT * FROM kg_edges WHERE knowledge_base_id = :kb_id"
        params: dict[str, Any] = {"kb_id": knowledge_base_id}
        if relation:
            query += " AND relation = :relation"
            params["relation"] = relation
        query += " ORDER BY weight DESC LIMIT :limit"
        params["limit"] = limit
        async with engine.connect() as conn:
            result = await conn.execute(text(query), params)
            return [KGEdge.from_dict(dict(row)) for row in result.mappings().all()]

    async def delete_by_knowledge_base(self, knowledge_base_id: str) -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM kg_edges WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )
            await conn.execute(
                text("DELETE FROM kg_nodes WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )

    async def stats(self, knowledge_base_id: str) -> dict[str, Any]:
        engine = get_engine()
        async with engine.connect() as conn:
            node_count = (await conn.execute(
                text("SELECT COUNT(*) FROM kg_nodes WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )).scalar() or 0
            edge_count = (await conn.execute(
                text("SELECT COUNT(*) FROM kg_edges WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )).scalar() or 0
            type_counts = (await conn.execute(
                text("SELECT node_type, COUNT(*) as cnt FROM kg_nodes WHERE knowledge_base_id = :kb_id GROUP BY node_type"),
                {"kb_id": knowledge_base_id},
            )).mappings().all()
            relation_counts = (await conn.execute(
                text("SELECT relation, COUNT(*) as cnt FROM kg_edges WHERE knowledge_base_id = :kb_id GROUP BY relation"),
                {"kb_id": knowledge_base_id},
            )).mappings().all()
        return {
            "knowledge_base_id": knowledge_base_id,
            "node_count": int(node_count),
            "edge_count": int(edge_count),
            "node_type_distribution": {row["node_type"]: int(row["cnt"]) for row in type_counts},
            "relation_distribution": {row["relation"]: int(row["cnt"]) for row in relation_counts},
        }
    