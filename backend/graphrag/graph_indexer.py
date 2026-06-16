# graphrag/graph_indexer.py
from __future__ import annotations

import uuid
from typing import Any

from graphrag.entities.entity_resolver import resolve_duplicates
from graphrag.graph_builder import GraphBuilder
from graphrag.graph_store import GraphStore
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.indexer")


class GraphIndexer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = GraphStore()
        self.builder = GraphBuilder(settings)

    async def index_knowledge_base(
        self,
        knowledge_base_id: str,
        chunks: list[dict[str, Any]],
        rebuild: bool = False,
    ) -> dict[str, Any]:
        if rebuild:
            await self.store.delete_by_knowledge_base(knowledge_base_id)
            logger.info("graph_index_rebuilt", kb_id=knowledge_base_id)

        build_stats = await self.builder.build_from_chunks(chunks, knowledge_base_id)
        merged = await resolve_duplicates(knowledge_base_id, self.store)
        final_stats = await self.store.stats(knowledge_base_id)

        return {
            **build_stats,
            "duplicates_merged": merged,
            "final_node_count": final_stats["node_count"],
            "final_edge_count": final_stats["edge_count"],
            "entity_type_distribution": final_stats["entity_type_distribution"],
        }

    async def incremental_update(
        self,
        knowledge_base_id: str,
        new_chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await self.builder.build_from_chunks(new_chunks, knowledge_base_id)
    