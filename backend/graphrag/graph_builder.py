# graphrag/graph_builder.py
from __future__ import annotations

import uuid
from typing import Any

from graphrag.entities.entity_extractor import batch_extract_entities
from graphrag.entities.entity_linker import link_entities
from graphrag.graph_embeddings import embed_nodes
from graphrag.graph_store import GraphEdge, GraphNode, GraphStore, RelationType
from graphrag.relationships.extractor import extract_relationships
from graphrag.relationships.validator import deduplicate_edges, filter_low_confidence_edges, validate_relationship
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.builder")


class GraphBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = GraphStore()

    async def build_from_chunks(
        self,
        chunks: list[dict[str, Any]],
        knowledge_base_id: str,
        embed_entities: bool = True,
    ) -> dict[str, Any]:
        logger.info("graph_build_started", kb_id=knowledge_base_id, chunks=len(chunks))

        all_extracted = await batch_extract_entities(chunks, self.settings)
        if not all_extracted:
            logger.warning("no_entities_extracted", kb_id=knowledge_base_id)
            return {"nodes": 0, "edges": 0, "chunks_processed": len(chunks)}

        linked_nodes = await link_entities(all_extracted, knowledge_base_id, self.store, self.settings)
        name_to_node: dict[str, GraphNode] = {node.name.lower(): node for node in linked_nodes}
        for node in linked_nodes:
            for alias in node.aliases:
                name_to_node.setdefault(alias.lower(), node)

        all_edges: list[GraphEdge] = []
        for chunk in chunks:
            chunk_text = chunk.get("text", "")
            chunk_id = chunk.get("id", str(uuid.uuid4()))
            entity_names = list({node.name for node in linked_nodes if any(
                node.name.lower() in chunk_text.lower() or
                any(alias.lower() in chunk_text.lower() for alias in node.aliases)
            )})[:20]

            if len(entity_names) < 2:
                continue

            raw_rels = await extract_relationships(
                text=chunk_text,
                chunk_id=chunk_id,
                entity_names=entity_names,
                settings=self.settings,
            )

            for rel in raw_rels:
                source_node = name_to_node.get(rel.source_name.lower())
                target_node = name_to_node.get(rel.target_name.lower())
                entity_name_to_id = {k: v.id for k, v in name_to_node.items()}

                if not validate_relationship(rel, entity_name_to_id):
                    continue
                if source_node is None or target_node is None:
                    continue

                try:
                    rel_type = RelationType(rel.relation_type)
                except ValueError:
                    rel_type = RelationType.OTHER

                edge = GraphEdge(
                    id=uuid.uuid4().hex,
                    source_id=source_node.id,
                    target_id=target_node.id,
                    relation_type=rel_type,
                    knowledge_base_id=knowledge_base_id,
                    description=rel.description,
                    weight=rel.weight,
                    properties={},
                    source_doc_ids=[chunk_id],
                    confidence=rel.confidence,
                )
                all_edges.append(edge)

        all_edges = filter_low_confidence_edges(deduplicate_edges(all_edges))
        for edge in all_edges:
            await self.store.upsert_edge(edge)

        embedded = 0
        if embed_entities:
            embedded = await embed_nodes(linked_nodes, knowledge_base_id, self.store, self.settings)

        stats = {
            "nodes": len(linked_nodes),
            "edges": len(all_edges),
            "chunks_processed": len(chunks),
            "entities_extracted": len(all_extracted),
            "nodes_embedded": embedded,
        }
        logger.info("graph_build_complete", kb_id=knowledge_base_id, **stats)
        return stats
    