# retrieval/federated_search.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.retrieval.federated_search")


@dataclass(slots=True)
class FederatedSearchResult:
    id: str
    score: float
    knowledge_base_id: str
    knowledge_base_name: str
    metadata: dict[str, Any] = field(default_factory=dict)
    rank: int = 0


async def federated_search(
    *,
    query: str,
    query_vector: list[float],
    knowledge_base_ids: list[uuid.UUID],
    collection_names: dict[str, str],
    kb_names: dict[str, str],
    top_k: int = 10,
    settings: Settings,
) -> list[FederatedSearchResult]:
    cfg = settings.retrieval.federated_search
    if not cfg.enabled:
        return []

    max_kbs = cfg.max_knowledge_bases
    effective_kb_ids = knowledge_base_ids[:max_kbs]

    from retrieval.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever(settings=settings)

    async def _search_one(kb_id: uuid.UUID) -> list[FederatedSearchResult]:
        kb_id_str = str(kb_id)
        collection = collection_names.get(kb_id_str, "")
        kb_name = kb_names.get(kb_id_str, kb_id_str)
        if not collection:
            return []
        try:
            results = await asyncio.wait_for(
                retriever.search(
                    query=query,
                    query_vector=query_vector,
                    knowledge_base_id=kb_id,
                    collection_name=collection,
                    top_k=top_k,
                    use_bm25=True,
                ),
                timeout=cfg.timeout_seconds,
            )
            return [
                FederatedSearchResult(
                    id=result.id,
                    score=result.score,
                    knowledge_base_id=kb_id_str,
                    knowledge_base_name=kb_name,
                    metadata=result.metadata,
                )
                for result in results
            ]
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("federated_kb_search_failed", kb_id=kb_id_str, error=str(exc))
            return []

    all_results_nested = await asyncio.gather(*[_search_one(kb_id) for kb_id in effective_kb_ids])
    all_results = [result for batch in all_results_nested for result in batch]
    all_results.sort(key=lambda result: result.score, reverse=True)

    for rank, result in enumerate(all_results[:top_k], start=1):
        result.rank = rank

    return all_results[:top_k]
