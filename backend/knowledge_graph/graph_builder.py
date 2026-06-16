# knowledge_graph/graph_builder.py
from __future__ import annotations

import json
import uuid
from typing import Any

from knowledge_graph.graph_embeddings import embed_kg_nodes
from knowledge_graph.graph_store import KGEdge, KGNode, KnowledgeGraphStore
from knowledge_graph.graph_utils import edge_id, node_id, normalize_label
from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.knowledge_graph.builder")

_KG_EXTRACTION_PROMPT = """Extract a knowledge graph from the text below.
Return a JSON object with two keys:
- "nodes": list of {{"id": unique_slug, "label": entity_name, "type": entity_type, "description": one_sentence, "aliases": [list]}}
- "edges": list of {{"source": node_id, "target": node_id, "relation": snake_case_relation, "weight": 0.0-1.0}}

Entity types: person, organization, location, concept, technology, event, product, date, quantity, other
Keep node ids short (3-5 words joined by underscores, lowercase).
Only include high-confidence facts from the text. No invented relationships.
Return ONLY valid JSON, no markdown, no explanation.

Text:
{text}

JSON:"""


class KnowledgeGraphBuilder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = KnowledgeGraphStore()

    async def extract_from_chunk(
        self, text: str, chunk_id: str, knowledge_base_id: str
    ) -> tuple[list[KGNode], list[KGEdge]]:
        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        prompt = _KG_EXTRACTION_PROMPT.format(text=text[:4000])

        try:
            response = await gateway.chat_completion(
                CompletionRequest(
                    messages=[ChatMessage(role=ChatRole.USER, content=prompt)],
                    max_tokens=2000,
                    temperature=0.0,
                )
            )
            raw = (response.content or "").strip().strip("```json").strip("```").strip()
            data: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("kg_extraction_failed", chunk_id=chunk_id, error=str(exc)[:200])
            return [], []

        raw_nodes: list[dict[str, Any]] = data.get("nodes", [])
        raw_edges: list[dict[str, Any]] = data.get("edges", [])

        slug_to_node_id: dict[str, str] = {}
        kg_nodes: list[KGNode] = []

        for raw_node in raw_nodes:
            label = normalize_label(str(raw_node.get("label", "")).strip())
            node_type = str(raw_node.get("type", "other")).lower().strip()
            slug = str(raw_node.get("id", "")).strip() or label.lower().replace(" ", "_")
            if not label:
                continue
            nid = node_id(knowledge_base_id, label, node_type)
            slug_to_node_id[slug] = nid
            kg_nodes.append(
                KGNode(
                    id=nid,
                    label=label,
                    node_type=node_type,
                    knowledge_base_id=knowledge_base_id,
                    properties={
                        "description": str(raw_node.get("description", ""))[:512],
                        "aliases": [str(a) for a in raw_node.get("aliases", [])],
                    },
                    source_ids=[chunk_id],
                    confidence=0.9,
                )
            )

        kg_edges: list[KGEdge] = []
        for raw_edge in raw_edges:
            source_slug = str(raw_edge.get("source", "")).strip()
            target_slug = str(raw_edge.get("target", "")).strip()
            relation = str(raw_edge.get("relation", "related_to")).lower().strip().replace(" ", "_")
            source_id_ = slug_to_node_id.get(source_slug)
            target_id_ = slug_to_node_id.get(target_slug)
            if not source_id_ or not target_id_ or source_id_ == target_id_:
                continue
            eid = edge_id(source_id_, target_id_, relation)
            kg_edges.append(
                KGEdge(
                    id=eid,
                    source_id=source_id_,
                    target_id=target_id_,
                    relation=relation,
                    knowledge_base_id=knowledge_base_id,
                    weight=float(raw_edge.get("weight", 0.8)),
                    source_ids=[chunk_id],
                    confidence=0.85,
                )
            )

        return kg_nodes, kg_edges

    async def build_from_chunks(
        self,
        chunks: list[dict[str, Any]],
        knowledge_base_id: str,
        embed_nodes: bool = True,
    ) -> dict[str, Any]:
        import asyncio

        logger.info("kg_build_started", kb_id=knowledge_base_id, chunks=len(chunks))
        semaphore = asyncio.Semaphore(3)

        async def _process_chunk(chunk: dict[str, Any]) -> tuple[list[KGNode], list[KGEdge]]:
            async with semaphore:
                return await self.extract_from_chunk(
                    text=chunk.get("text", ""),
                    chunk_id=chunk.get("id", str(uuid.uuid4())),
                    knowledge_base_id=knowledge_base_id,
                )

        results = await asyncio.gather(*[_process_chunk(chunk) for chunk in chunks], return_exceptions=True)

        all_nodes: dict[str, KGNode] = {}
        all_edges: dict[str, KGEdge] = {}

        for batch in results:
            if not isinstance(batch, tuple):
                continue
            nodes_batch, edges_batch = batch
            for node in nodes_batch:
                if node.id in all_nodes:
                    existing = all_nodes[node.id]
                    existing.source_ids = list(set(existing.source_ids + node.source_ids))
                    existing.confidence = max(existing.confidence, node.confidence)
                else:
                    all_nodes[node.id] = node
            for edge in edges_batch:
                all_edges[edge.id] = edge

        for node in all_nodes.values():
            await self.store.upsert_node(node)
        for edge in all_edges.values():
            await self.store.upsert_edge(edge)

        embedded_count = 0
        if embed_nodes and all_nodes:
            embedded_count = await embed_kg_nodes(list(all_nodes.values()), knowledge_base_id, self.settings)

        stats = {
            "nodes": len(all_nodes),
            "edges": len(all_edges),
            "chunks_processed": len(chunks),
            "nodes_embedded": embedded_count,
        }
        logger.info("kg_build_complete", kb_id=knowledge_base_id, **stats)
        return stats
    