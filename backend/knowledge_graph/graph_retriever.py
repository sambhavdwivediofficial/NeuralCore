# knowledge_graph/graph_retriever.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from knowledge_graph.graph_search import KGSearchResult, search_knowledge_graph
from knowledge_graph.graph_store import KnowledgeGraphStore
from knowledge_graph.graph_utils import extract_triples, triples_to_text
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.knowledge_graph.retriever")


@dataclass(slots=True)
class KGRetrievalResult:
    id: str
    score: float
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    triples: list[tuple[str, str, str]] = field(default_factory=list)


class KnowledgeGraphRetriever:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = KnowledgeGraphStore()

    async def retrieve(
        self,
        query: str,
        knowledge_base_id: uuid.UUID,
        top_k: int = 10,
        max_hops: int = 2,
        min_score: float = 0.0,
    ) -> list[KGRetrievalResult]:
        kb_id_str = str(knowledge_base_id)
        results = await search_knowledge_graph(
            query=query,
            knowledge_base_id=kb_id_str,
            settings=self.settings,
            top_k=top_k,
            max_hops=max_hops,
            include_triples=True,
        )

        retrieval_results: list[KGRetrievalResult] = []
        for result in results:
            if result.score < min_score:
                continue

            text_parts: list[str] = []
            if result.label:
                text_parts.append(f"Entity: {result.label} ({result.node_type})")
            if result.description:
                text_parts.append(f"Description: {result.description}")
            if result.related_triples:
                text_parts.append("Relationships:")
                text_parts.append(triples_to_text(result.related_triples[:10]))

            retrieval_results.append(
                KGRetrievalResult(
                    id=result.id,
                    score=result.score,
                    text="\n".join(text_parts),
                    metadata={
                        "label": result.label,
                        "node_type": result.node_type,
                        "knowledge_base_id": kb_id_str,
                        "triple_count": len(result.related_triples),
                        **result.metadata,
                    },
                    triples=result.related_triples,
                )
            )

        return retrieval_results

    async def get_entity_subgraph(
        self,
        entity_label: str,
        knowledge_base_id: uuid.UUID,
        max_hops: int = 2,
    ) -> dict[str, Any]:
        kb_id_str = str(knowledge_base_id)
        nodes = await self.store.get_nodes_by_label(kb_id_str, entity_label, limit=1)
        if not nodes:
            return {"nodes": [], "edges": [], "triples": []}

        root_node = nodes[0]
        neighbor_nodes, edges = await self.store.get_neighbors(root_node.id, kb_id_str, max_depth=max_hops)
        all_nodes = [root_node] + neighbor_nodes
        triples = extract_triples(all_nodes, edges)

        return {
            "root": root_node.to_dict(),
            "nodes": [node.to_dict() for node in all_nodes],
            "edges": [edge.to_dict() for edge in edges],
            "triples": [{"subject": s, "predicate": p, "object": o} for s, p, o in triples],
            "triple_text": triples_to_text(triples),
        }

    async def context_for_query(
        self, query: str, knowledge_base_id: uuid.UUID, max_tokens: int = 1500
    ) -> str:
        from chunking.base_chunker import count_tokens

        results = await self.retrieve(query, knowledge_base_id, top_k=5, max_hops=2)
        if not results:
            return ""

        lines: list[str] = ["## Knowledge Graph Context\n"]
        for result in results:
            lines.append(result.text)
            lines.append("")
            if count_tokens("\n".join(lines)) > max_tokens:
                break

        return "\n".join(lines).strip()
    