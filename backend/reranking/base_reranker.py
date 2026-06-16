# reranking/base_reranker.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from settings import Settings


class RerankingError(Exception):
    def __init__(self, message: str, provider: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class BaseReranker(ABC):
    provider_name: str

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[dict[str, Any]],
        top_n: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def _resolve_top_n(self, top_n: int | None) -> int:
        return top_n or self.settings.retrieval.reranking.top_n

    def _get_text(self, document: dict[str, Any]) -> str:
        return document.get("text") or document.get("content") or document.get("metadata", {}).get("text", "")

    async def health_check(self) -> bool:
        try:
            await self.rerank("test", [{"id": "1", "text": "test document"}], top_n=1)
            return True
        except RerankingError:
            return False
