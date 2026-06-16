# reranking/bge_reranker.py
from __future__ import annotations

import asyncio
from typing import Any

from reranking.base_reranker import BaseReranker, RerankingError
from settings import Settings

_BGE_MODELS: dict[str, str] = {
    "bge-reranker-large": "BAAI/bge-reranker-large",
    "bge-reranker-base": "BAAI/bge-reranker-base",
    "bge-reranker-v2-m3": "BAAI/bge-reranker-v2-m3",
}


class BGEReranker(BaseReranker):
    provider_name = "bge"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._model_cache: dict[str, Any] = {}

    def _load_model(self, model_name: str) -> Any:
        if model_name in self._model_cache:
            return self._model_cache[model_name]
        hf_id = _BGE_MODELS.get(model_name, model_name)
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(hf_id, max_length=512)
            self._model_cache[model_name] = model
            return model
        except ImportError as exc:
            raise RerankingError(
                "sentence-transformers not installed; use requirements-worker.txt",
                provider=self.provider_name,
            ) from exc

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_n: int | None = None,
        model_name: str = "bge-reranker-large",
    ) -> list[dict[str, Any]]:
        if not documents:
            return []
        limit = self._resolve_top_n(top_n)

        pairs = [[query, self._get_text(doc)] for doc in documents]
        try:
            model = self._load_model(model_name)
            scores: list[float] = await asyncio.to_thread(model.predict, pairs)
        except RerankingError:
            raise
        except Exception as exc:
            raise RerankingError(str(exc), provider=self.provider_name) from exc

        scored = sorted(zip(documents, scores), key=lambda item: item[1], reverse=True)
        return [
            {**doc, "score": float(score), "rerank_provider": self.provider_name}
            for doc, score in scored[:limit]
        ]
