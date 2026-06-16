# graphrag/graph_retriever.py
from __future__ import annotations

import uuid
from typing import Any

from graphrag.graph_search import GraphSearchResult, search_graph
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.retriever")


class GraphRetriever:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def search(
        self,
        query: str,
        knowledge_base_id: uuid.UUID,
        top_k: int = 10,
        max_hops: int | None = None,
    ) -> list[GraphSearchResult]:
        return await search_graph(
            query=query,
            knowledge_base_id=str(knowledge_base_id),
            settings=self.settings,
            top_k=top_k,
            max_hops=max_hops,
        )
    