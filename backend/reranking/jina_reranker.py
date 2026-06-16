# reranking/jina_reranker.py
from __future__ import annotations

from typing import Any

import httpx

from reranking.base_reranker import BaseReranker, RerankingError
from settings import Settings

_JINA_RERANK_URL = "https://api.jina.ai/v1/rerank"
_DEFAULT_JINA_MODEL = "jina-reranker-v2-base-multilingual"


class JinaReranker(BaseReranker):
    provider_name = "jina"

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        jina_config = settings.embeddings.providers.get("jina")
        api_key = jina_config.api_key.get_secret_value() if jina_config and jina_config.api_key else None
        if not api_key:
            raise RerankingError("Jina API key is not configured", provider=self.provider_name)
        self._api_key = api_key

    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_n: int | None = None,
        model_name: str = _DEFAULT_JINA_MODEL,
    ) -> list[dict[str, Any]]:
        if not documents:
            return []
        limit = self._resolve_top_n(top_n)

        payload = {
            "model": model_name,
            "query": query,
            "documents": [self._get_text(doc) for doc in documents],
            "top_n": limit,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    _JINA_RERANK_URL,
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise RerankingError("invalid Jina API key", provider=self.provider_name) from exc
            raise RerankingError(f"Jina API error {exc.response.status_code}", provider=self.provider_name) from exc
        except httpx.TransportError as exc:
            raise RerankingError(str(exc), provider=self.provider_name) from exc

        results = response.json().get("results", [])
        reranked: list[dict[str, Any]] = []
        for item in results:
            index = item.get("index", 0)
            if index < len(documents):
                reranked.append({
                    **documents[index],
                    "score": float(item.get("relevance_score", 0.0)),
                    "rerank_provider": self.provider_name,
                })
        return reranked
