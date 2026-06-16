# retrieval/hybrid_retriever.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger, log_slow_llm_call
from monitoring.tracing import trace_span
from settings import Settings
from vector_stores.base import MetadataFilter, VectorSearchResult

try:
    import neuralcore_engine
except ImportError:
    neuralcore_engine = None

logger = get_logger("neuralcore.retrieval.hybrid_retriever")


@dataclass(slots=True)
class HybridSearchResult:
    id: str
    score: float
    rank: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    vector_score: float | None = None
    bm25_score: float | None = None
    graph_score: float | None = None
    sources: list[str] = field(default_factory=list)


def _reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    k: int = 60,
    weights: list[float] | None = None,
) -> list[tuple[str, float]]:
    if neuralcore_engine is not None:
        func = getattr(neuralcore_engine, "py_fuse_ranked_lists", None)
        if func is not None:
            try:
                return func(ranked_lists, "rrf", k)
            except Exception:
                pass

    scores: dict[str, float] = {}
    effective_weights = weights or [1.0] * len(ranked_lists)

    for ranked_list, weight in zip(ranked_lists, effective_weights):
        for rank, (doc_id, _) in enumerate(ranked_list, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + weight * (1.0 / (k + rank))

    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


class HybridRetriever:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def search(
        self,
        *,
        query: str,
        query_vector: list[float],
        knowledge_base_id: uuid.UUID,
        collection_name: str,
        top_k: int | None = None,
        filters: list[MetadataFilter] | None = None,
        use_bm25: bool = True,
        use_graph: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> list[HybridSearchResult]:
        cfg = self.settings.retrieval
        limit = top_k or cfg.vector_search.default_top_k
        hybrid_cfg = cfg.hybrid

        with trace_span(
            "retrieval.hybrid_search",
            knowledge_base_id=str(knowledge_base_id),
            top_k=limit,
            use_bm25=use_bm25,
            use_graph=use_graph,
        ):
            vector_task = self._vector_search(query_vector, knowledge_base_id, collection_name, limit * 2, filters)
            bm25_task = self._bm25_search(query, knowledge_base_id, limit * 2) if (use_bm25 and hybrid_cfg.enabled) else asyncio.coroutine(lambda: [])()
            graph_task = self._graph_search(query, knowledge_base_id, limit) if use_graph else asyncio.coroutine(lambda: [])()

            vector_results, bm25_results, graph_results = await asyncio.gather(
                vector_task, bm25_task, graph_task, return_exceptions=True
            )

            vector_results = vector_results if isinstance(vector_results, list) else []
            bm25_results = bm25_results if isinstance(bm25_results, list) else []
            graph_results = graph_results if isinstance(graph_results, list) else []

        return self._fuse_results(
            vector_results=vector_results,
            bm25_results=bm25_results,
            graph_results=graph_results,
            top_k=limit,
            rrf_k=hybrid_cfg.rrf_k,
            vector_weight=hybrid_cfg.vector_weight,
            bm25_weight=hybrid_cfg.bm25_weight,
        )

    async def _vector_search(
        self,
        query_vector: list[float],
        knowledge_base_id: uuid.UUID,
        collection_name: str,
        top_k: int,
        filters: list[MetadataFilter] | None,
    ) -> list[VectorSearchResult]:
        from retrieval.vector_search import vector_search

        return await vector_search(
            query_vector=query_vector,
            knowledge_base_id=knowledge_base_id,
            collection_name=collection_name,
            top_k=top_k,
            filters=filters,
            score_threshold=self.settings.retrieval.vector_search.score_threshold or None,
            settings=self.settings,
        )

    async def _bm25_search(self, query: str, knowledge_base_id: uuid.UUID, top_k: int) -> list[Any]:
        from retrieval.bm25 import get_bm25_index

        cfg = self.settings.retrieval.bm25
        index = get_bm25_index(str(knowledge_base_id), k1=cfg.k1, b=cfg.b)
        if len(index) == 0:
            return []
        return index.search(query, top_k=top_k)

    async def _graph_search(self, query: str, knowledge_base_id: uuid.UUID, top_k: int) -> list[Any]:
        from retrieval.graph_search import graph_search

        return await graph_search(
            query=query,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
            settings=self.settings,
        )

    def _fuse_results(
        self,
        *,
        vector_results: list[Any],
        bm25_results: list[Any],
        graph_results: list[Any],
        top_k: int,
        rrf_k: int,
        vector_weight: float,
        bm25_weight: float,
    ) -> list[HybridSearchResult]:
        vector_ranked = [(result.id, result.score) for result in vector_results]
        bm25_ranked = [(result.id, result.score) for result in bm25_results]
        graph_ranked = [(result.id, result.score) for result in graph_results]

        all_lists = [vector_ranked]
        all_weights = [vector_weight]
        if bm25_ranked:
            all_lists.append(bm25_ranked)
            all_weights.append(bm25_weight)
        if graph_ranked:
            all_lists.append(graph_ranked)
            all_weights.append(0.3)

        fused = _reciprocal_rank_fusion(all_lists, k=rrf_k, weights=all_weights)[:top_k]

        vector_score_map = {result.id: result.score for result in vector_results}
        bm25_score_map = {result.id: result.score for result in bm25_results}
        graph_score_map = {getattr(result, "id", ""): getattr(result, "score", 0.0) for result in graph_results}
        metadata_map = {
            result.id: result.metadata
            for result in [*vector_results, *bm25_results]
            if hasattr(result, "metadata")
        }

        output: list[HybridSearchResult] = []
        for rank, (doc_id, rrf_score) in enumerate(fused, start=1):
            sources: list[str] = []
            if doc_id in vector_score_map:
                sources.append("vector")
            if doc_id in bm25_score_map:
                sources.append("bm25")
            if doc_id in graph_score_map:
                sources.append("graph")

            output.append(
                HybridSearchResult(
                    id=doc_id,
                    score=rrf_score,
                    rank=rank,
                    metadata=metadata_map.get(doc_id, {}),
                    vector_score=vector_score_map.get(doc_id),
                    bm25_score=bm25_score_map.get(doc_id),
                    graph_score=graph_score_map.get(doc_id),
                    sources=sources,
                )
            )
        return output
