# retrieval/graph_search.py
from __future__ import annotations

import uuid
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.retrieval.graph_search")


class GraphSearchResult:
    __slots__ = ("id", "score", "metadata", "depth", "path")

    def __init__(self, id: str, score: float, metadata: dict[str, Any], depth: int, path: list[str]) -> None:
        self.id = id
        self.score = score
        self.metadata = metadata
        self.depth = depth
        self.path = path


async def graph_search(
    *,
    query: str,
    knowledge_base_id: uuid.UUID,
    top_k: int = 10,
    max_hops: int | None = None,
    settings: Settings,
) -> list[GraphSearchResult]:
    if not settings.retrieval.graph_search.enabled:
        return []

    hops = max_hops or settings.retrieval.graph_search.max_hops

    try:
        from graphrag.graph_retriever import GraphRetriever

        retriever = GraphRetriever(settings=settings)
        return await retriever.search(
            query=query,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
            max_hops=hops,
        )
    except ImportError:
        logger.warning("graphrag_module_unavailable")
        return []
    except Exception as exc:
        logger.error("graph_search_failed", error=str(exc))
        return []
