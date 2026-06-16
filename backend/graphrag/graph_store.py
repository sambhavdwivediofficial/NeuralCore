# graphrag/graph_store.py
from __future__ import annotations

import enum
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin, UUIDMixin
from database.connection import get_engine


class EntityType(str, enum.Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    CONCEPT = "concept"
    TECHNOLOGY = "technology"
    EVENT = "event"
    PRODUCT = "product"
    DATE = "date"
    QUANTITY = "quantity"
    OTHER = "other"


class RelationType(str, enum.Enum):
    WORKS_AT = "works_at"
    LOCATED_IN = "located_in"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    MENTIONS = "mentions"
    CAUSES = "causes"
    USES = "uses"
    CREATES = "creates"
    BELONGS_TO = "belongs_to"
    OCCURRED_AT = "occurred_at"
    HAS_PROPERTY = "has_property"
    SIMILAR_TO = "similar_to"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    OTHER = "other"


@dataclass(slots=True)
class GraphNode:
    id: str
    name: str
    entity_type: EntityType
    knowledge_base_id: str
    description: str = ""
    aliases: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)
    source_doc_ids: list[str] = field(default_factory=list)
    embedding_id: str | None = None
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "knowledge_base_id": self.knowledge_base_id,
            "description": self.description,
            "aliases": self.aliases,
            "properties": self.properties,
            "source_doc_ids": self.source_doc_ids,
            "embedding_id": self.embedding_id,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphNode":
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=EntityType(data["entity_type"]),
            knowledge_base_id=data["knowledge_base_id"],
            description=data.get("description", ""),
            aliases=data.get("aliases", []),
            properties=data.get("properties", {}),
            source_doc_ids=data.get("source_doc_ids", []),
            embedding_id=data.get("embedding_id"),
            confidence=data.get("confidence", 1.0),
        )


@dataclass(slots=True)
class GraphEdge:
    id: str
    source_id: str
    target_id: str
    relation_type: RelationType
    knowledge_base_id: str
    description: str = ""
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    source_doc_ids: list[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "knowledge_base_id": self.knowledge_base_id,
            "description": self.description,
            "weight": self.weight,
            "properties": self.properties,
            "source_doc_ids": self.source_doc_ids,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphEdge":
        return cls(
            id=data["id"],
            source_id=data["source_id"],
            target_id=data["target_id"],
            relation_type=RelationType(data["relation_type"]),
            knowledge_base_id=data["knowledge_base_id"],
            description=data.get("description", ""),
            weight=data.get("weight", 1.0),
            properties=data.get("properties", {}),
            source_doc_ids=data.get("source_doc_ids", []),
            confidence=data.get("confidence", 1.0),
        )


class GraphNodeModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "graph_nodes"
    __table_args__ = (
        UniqueConstraint("knowledge_base_id", "name", "entity_type", name="uq_graph_node_name_type"),
        Index("ix_graph_nodes_kb_type", "knowledge_base_id", "entity_type"),
    )

    knowledge_base_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    aliases: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_doc_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)


class GraphEdgeModel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "graph_edges"
    __table_args__ = (
        Index("ix_graph_edges_kb_source", "knowledge_base_id", "source_id"),
        Index("ix_graph_edges_kb_target", "knowledge_base_id", "target_id"),
        Index("ix_graph_edges_relation", "knowledge_base_id", "relation_type"),
    )

    knowledge_base_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    weight: Mapped[float] = mapped_column(nullable=False, default=1.0)
    properties: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_doc_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)


class GraphStore:
    async def upsert_node(self, node: GraphNode) -> GraphNode:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO graph_nodes (id, knowledge_base_id, name, entity_type, description,
                        aliases, properties, source_doc_ids, embedding_id, confidence,
                        created_at, updated_at)
                    VALUES (:id, :kb_id, :name, :entity_type, :description,
                        :aliases::jsonb, :properties::jsonb, :source_doc_ids::jsonb,
                        :embedding_id, :confidence, NOW(), NOW())
                    ON CONFLICT (knowledge_base_id, name, entity_type)
                    DO UPDATE SET
                        description = EXCLUDED.description,
                        aliases = graph_nodes.aliases || EXCLUDED.aliases,
                        properties = graph_nodes.properties || EXCLUDED.properties,
                        source_doc_ids = graph_nodes.source_doc_ids || EXCLUDED.source_doc_ids,
                        confidence = GREATEST(graph_nodes.confidence, EXCLUDED.confidence),
                        updated_at = NOW()
                    RETURNING id
                """),
                {
                    "id": node.id,
                    "kb_id": node.knowledge_base_id,
                    "name": node.name,
                    "entity_type": node.entity_type.value,
                    "description": node.description,
                    "aliases": json.dumps(list(set(node.aliases))),
                    "properties": json.dumps(node.properties),
                    "source_doc_ids": json.dumps(list(set(node.source_doc_ids))),
                    "embedding_id": node.embedding_id,
                    "confidence": node.confidence,
                },
            )
        return node

    async def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text("""
                    INSERT INTO graph_edges (id, knowledge_base_id, source_id, target_id,
                        relation_type, description, weight, properties, source_doc_ids, confidence,
                        created_at, updated_at)
                    VALUES (:id, :kb_id, :source_id, :target_id, :relation_type,
                        :description, :weight, :properties::jsonb, :source_doc_ids::jsonb,
                        :confidence, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": edge.id,
                    "kb_id": edge.knowledge_base_id,
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "relation_type": edge.relation_type.value,
                    "description": edge.description,
                    "weight": edge.weight,
                    "properties": json.dumps(edge.properties),
                    "source_doc_ids": json.dumps(list(set(edge.source_doc_ids))),
                    "confidence": edge.confidence,
                },
            )
        return edge

    async def get_node(self, node_id: str) -> GraphNode | None:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT * FROM graph_nodes WHERE id = :id"), {"id": node_id}
            )
            row = result.mappings().first()
        if row is None:
            return None
        return GraphNode.from_dict(dict(row))

    async def get_node_by_name(self, knowledge_base_id: str, name: str, entity_type: EntityType) -> GraphNode | None:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT * FROM graph_nodes WHERE knowledge_base_id = :kb_id AND name = :name AND entity_type = :et"),
                {"kb_id": knowledge_base_id, "name": name, "et": entity_type.value},
            )
            row = result.mappings().first()
        if row is None:
            return None
        return GraphNode.from_dict(dict(row))

    async def get_neighbors(
        self, node_id: str, knowledge_base_id: str, max_neighbors: int = 50
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        engine = get_engine()
        async with engine.connect() as conn:
            edges_result = await conn.execute(
                text("""
                    SELECT * FROM graph_edges
                    WHERE knowledge_base_id = :kb_id
                    AND (source_id = :node_id OR target_id = :node_id)
                    ORDER BY weight DESC, confidence DESC
                    LIMIT :limit
                """),
                {"kb_id": knowledge_base_id, "node_id": node_id, "limit": max_neighbors},
            )
            raw_edges = [GraphEdge.from_dict(dict(row)) for row in edges_result.mappings().all()]

            neighbor_ids = set()
            for edge in raw_edges:
                neighbor_ids.add(edge.source_id)
                neighbor_ids.add(edge.target_id)
            neighbor_ids.discard(node_id)

            nodes: list[GraphNode] = []
            if neighbor_ids:
                nodes_result = await conn.execute(
                    text("SELECT * FROM graph_nodes WHERE id = ANY(:ids)"),
                    {"ids": list(neighbor_ids)},
                )
                nodes = [GraphNode.from_dict(dict(row)) for row in nodes_result.mappings().all()]

        return nodes, raw_edges

    async def search_nodes_by_name(
        self, knowledge_base_id: str, query: str, limit: int = 20
    ) -> list[GraphNode]:
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT *, similarity(name, :query) AS sim
                    FROM graph_nodes
                    WHERE knowledge_base_id = :kb_id
                    AND (
                        name ILIKE :pattern
                        OR :query = ANY(SELECT jsonb_array_elements_text(aliases))
                        OR to_tsvector('english', name || ' ' || description) @@ plainto_tsquery('english', :query)
                    )
                    ORDER BY sim DESC, confidence DESC
                    LIMIT :limit
                """),
                {"kb_id": knowledge_base_id, "query": query, "pattern": f"%{query}%", "limit": limit},
            )
            return [GraphNode.from_dict(dict(row)) for row in result.mappings().all()]

    async def delete_by_knowledge_base(self, knowledge_base_id: str) -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(
                text("DELETE FROM graph_edges WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )
            await conn.execute(
                text("DELETE FROM graph_nodes WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )

    async def stats(self, knowledge_base_id: str) -> dict[str, Any]:
        engine = get_engine()
        async with engine.connect() as conn:
            node_count = (await conn.execute(
                text("SELECT COUNT(*) FROM graph_nodes WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )).scalar() or 0
            edge_count = (await conn.execute(
                text("SELECT COUNT(*) FROM graph_edges WHERE knowledge_base_id = :kb_id"),
                {"kb_id": knowledge_base_id},
            )).scalar() or 0
            type_dist = (await conn.execute(
                text("SELECT entity_type, COUNT(*) as cnt FROM graph_nodes WHERE knowledge_base_id = :kb_id GROUP BY entity_type"),
                {"kb_id": knowledge_base_id},
            )).mappings().all()
        return {
            "knowledge_base_id": knowledge_base_id,
            "node_count": int(node_count),
            "edge_count": int(edge_count),
            "entity_type_distribution": {row["entity_type"]: int(row["cnt"]) for row in type_dist},
        }
    