# reranking/hybrid_reranker.py
from __future__ import annotations

import math
from typing import Any

from reranking.base_reranker import BaseReranker, RerankingError
from settings import Settings

_RERANKER_REGISTRY: dict[str, type[BaseReranker]] = {}


def _register() -> None:
    global _RERANKER_REGISTRY
    from reranking.bge_reranker import BGEReranker
    from reranking.cross_encoder import CrossEncoderReranker
    from reranking.jina_reranker import JinaReranker

    _RERANKER_REGISTRY = {
        "bge": BGEReranker,
        "cross_encoder": CrossEncoderReranker,
        "jina": JinaReranker,
        "hybrid": HybridReranker,
    }


def get_reranker(provider_name: str, settings: Settings) -> BaseReranker:
    if not _RERANKER_REGISTRY:
        _register()
    cls = _RERANKER_REGISTRY.get(provider_name)
    if cls is None:
        raise RerankingError(f"unknown reranker provider '{provider_name}'", provider=provider_name)
    return cls(settings)


class HybridReranker(BaseReranker):
    provider_name = "hybrid"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._primary: BaseReranker | None = None
        self._fallbacks: list[BaseReranker] = []

    def _init_providers(self) -> None:
        if self._primary is not None:
            return
        available_providers = self.settings.retrieval.reranking.providers
        ordered = [p for p in available_providers if p != "hybrid"]

        for provider_name in ordered:
            try:
                reranker = get_reranker(provider_name, self.settings)
                if self._primary is None:
                    self._primary = reranker
                else:
                    self._fallbacks.append(reranker)
            except (RerankingError, Exception):
                continue

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_n: int | None = None,
    ) -> list[dict[str, Any]]:
        self._init_providers()

        if self._primary is None:
            return self._score_normalize(documents, top_n)

        try:
            return await self._primary.rerank(query, documents, top_n)
        except RerankingError:
            for fallback in self._fallbacks:
                try:
                    return await fallback.rerank(query, documents, top_n)
                except RerankingError:
                    continue
            return self._score_normalize(documents, top_n)

    def _score_normalize(
        self, documents: list[dict[str, Any]], top_n: int | None
    ) -> list[dict[str, Any]]:
        limit = self._resolve_top_n(top_n)
        scores = [float(doc.get("score", 0.0)) for doc in documents]
        if not scores:
            return []
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score

        normalized: list[dict[str, Any]] = []
        for doc, score in zip(documents, scores):
            normalized_score = (score - min_score) / score_range if score_range > 0 else 1.0
            normalized.append({**doc, "score": normalized_score, "rerank_provider": "normalized"})

        return sorted(normalized, key=lambda item: item["score"], reverse=True)[:limit]
