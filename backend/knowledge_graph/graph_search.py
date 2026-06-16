# knowledge_graph/graph_search.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from knowledge_graph.graph_embeddings import search_kg_nodes_by_vector
from knowledge_graph.graph_store import KGEdge, KGNode, KnowledgeGraphStore
from knowledge_graph.graph_utils import build_adjacency, extract_triples, triples_to_text
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.knowledge_graph.search")


@dataclass(slots=True)
class KGSearchResult:
    id: str
    score: float
    label: str
    node_type: str
    description: str
    related_triples: list[tuple[str, str, str]] = field(default_factory=list)
    context_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


async def search_knowledge_graph(
    query: str,
    knowledge_base_id: str,
    settings: Settings,
    top_k: int = 10,
    max_hops: int = 2,
    include_triples: bool = True,
) -> list[KGSearchResult]:
    store = KnowledgeGraphStore()

    vector_hits = await search_kg_nodes_by_vector(
        query=query,
        knowledge_base_id=knowledge_base_id,
        settings=settings,
        top_k=top_k,
    )

    if not vector_hits:
        text_nodes = await store.get_nodes_by_label(knowledge_base_id, query, limit=top_k)
        vector_hits = [
            {"id": node.id, "score": node.confidence, "metadata": {"label": node.label, "description": ""}}
            for node in text_nodes
        ]

    if not vector_hits:
        return []

    results: list[KGSearchResult] = []
    for hit in vector_hits:
        node_id_ = hit["id"]
        score = hit["score"]
        meta = hit.get("metadata", {})

        neighbors, edges = await store.get_neighbors(node_id_, knowledge_base_id, max_depth=max_hops)
        all_nodes = await store.get_nodes_by_label(knowledge_base_id, meta.get("label", ""), limit=1)
        root_nodes = all_nodes if all_nodes else []

        all_nodes_for_triples = root_nodes + neighbors
        triples: list[tuple[str, str, str]] = []
        if include_triples:
            triples = extract_triples(all_nodes_for_triples, edges)

        context_text = triples_to_text(triples) if triples else meta.get("description", "")

        results.append(
            KGSearchResult(
                id=node_id_,
                score=score,
                label=meta.get("label", ""),
                node_type=meta.get("node_type", "other"),
                description=meta.get("description", ""),
                related_triples=triples[:20],
                context_text=context_text[:2000],
                metadata=meta,
            )
        )

    return results


async def keyword_search_graph(
    terms: list[str],
    knowledge_base_id: str,
    settings: Settings,
    limit_per_term: int = 5,
) -> list[KGSearchResult]:
    import asyncio

    store = KnowledgeGraphStore()

    async def _search_term(term: str) -> list[KGSearchResult]:
        nodes = await store.get_nodes_by_label(knowledge_base_id, term, limit=limit_per_term)
        return [
            KGSearchResult(
                id=node.id,
                score=node.confidence,
                label=node.label,
                node_type=node.node_type,
                description=node.properties.get("description", ""),
                metadata={"label": node.label, "node_type": node.node_type},
            )
            for node in nodes
        ]

    results_nested = await asyncio.gather(*[_search_term(term) for term in terms])
    seen_ids: set[str] = set()
    flattened: list[KGSearchResult] = []
    for batch in results_nested:
        for result in batch:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                flattened.append(result)
    return flattened
