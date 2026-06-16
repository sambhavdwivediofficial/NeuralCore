# retrieval/retriever.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger, log_slow_llm_call
from monitoring.tracing import trace_span
from settings import Settings

logger = get_logger("neuralcore.retrieval.retriever")


@dataclass(slots=True)
class RetrievalRequest:
    query: str
    knowledge_base_id: uuid.UUID
    collection_name: str
    top_k: int = 10
    use_hybrid: bool = True
    use_reranking: bool = True
    use_query_rewriting: bool = False
    use_graph: bool = False
    filter_spec: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalResult:
    id: str
    score: float
    rank: int
    text: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    reranked: bool = False
    sources: list[str] = field(default_factory=list)


class Retriever:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def search(
        self,
        knowledge_base_id: uuid.UUID,
        query: str,
        top_k: int | None = None,
        collection_name: str | None = None,
        use_hybrid: bool = True,
        use_reranking: bool = True,
        use_query_rewriting: bool = False,
        use_graph: bool = False,
        filter_spec: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        limit = top_k or self.settings.retrieval.vector_search.default_top_k
        collection = collection_name or f"nc_{knowledge_base_id.hex}"

        request = RetrievalRequest(
            query=query,
            knowledge_base_id=knowledge_base_id,
            collection_name=collection,
            top_k=limit,
            use_hybrid=use_hybrid,
            use_reranking=use_reranking,
            use_query_rewriting=use_query_rewriting,
            use_graph=use_graph,
            filter_spec=filter_spec or {},
        )

        with trace_span("retrieval.search", knowledge_base_id=str(knowledge_base_id), top_k=limit):
            return await self._execute(request)

    async def _execute(self, request: RetrievalRequest) -> list[RetrievalResult]:
        from embeddings.embedding_factory import get_embedding_provider
        from retrieval.hybrid_retriever import HybridRetriever
        from retrieval.metadata_search import build_metadata_filters
        from retrieval.vector_search import vector_search

        effective_query = request.query
        if request.use_query_rewriting:
            from retrieval.query_rewriter import expand_query
            effective_query = await expand_query(request.query, self.settings)

        provider = get_embedding_provider(settings=self.settings)
        query_vector = await provider.embed_query(effective_query)

        filters = build_metadata_filters(request.filter_spec) if request.filter_spec else None
        fetch_k = min(request.top_k * 3, self.settings.retrieval.vector_search.max_top_k)

        if request.use_hybrid and self.settings.retrieval.hybrid.enabled:
            retriever = HybridRetriever(settings=self.settings)
            hybrid_results = await retriever.search(
                query=effective_query,
                query_vector=query_vector,
                knowledge_base_id=request.knowledge_base_id,
                collection_name=request.collection_name,
                top_k=fetch_k,
                filters=filters,
                use_graph=request.use_graph,
            )
            candidates = [
                RetrievalResult(
                    id=result.id,
                    score=result.score,
                    rank=result.rank,
                    text=result.metadata.get("text"),
                    metadata=result.metadata,
                    sources=result.sources,
                )
                for result in hybrid_results
            ]
        else:
            vector_results = await vector_search(
                query_vector=query_vector,
                knowledge_base_id=request.knowledge_base_id,
                collection_name=request.collection_name,
                top_k=fetch_k,
                filters=filters,
                settings=self.settings,
            )
            candidates = [
                RetrievalResult(
                    id=result.id,
                    score=result.score,
                    rank=rank,
                    text=result.metadata.get("text"),
                    metadata=result.metadata,
                    sources=["vector"],
                )
                for rank, result in enumerate(vector_results, start=1)
            ]

        if not candidates:
            return []

        if request.use_reranking and self.settings.retrieval.reranking.enabled:
            candidates = await self._rerank(request.query, candidates, request.top_k)
        else:
            candidates = candidates[:request.top_k]
            for rank, candidate in enumerate(candidates, start=1):
                candidate.rank = rank

        return candidates

    async def _rerank(
        self, query: str, candidates: list[RetrievalResult], top_k: int
    ) -> list[RetrievalResult]:
        from reranking.hybrid_reranker import get_reranker

        try:
            reranker = get_reranker(
                self.settings.retrieval.reranking.default_provider, settings=self.settings
            )
            docs = [{"id": candidate.id, "text": candidate.text or "", "metadata": candidate.metadata} for candidate in candidates]
            reranked_docs = await reranker.rerank(query=query, documents=docs, top_n=top_k)

            id_to_candidate = {candidate.id: candidate for candidate in candidates}
            results: list[RetrievalResult] = []
            for rank, doc in enumerate(reranked_docs, start=1):
                original = id_to_candidate.get(doc.get("id", ""))
                if original:
                    original.score = doc.get("score", original.score)
                    original.rank = rank
                    original.reranked = True
                    results.append(original)
            return results
        except Exception as exc:
            logger.warning("reranking_failed", error=str(exc))
            return candidates[:top_k]
