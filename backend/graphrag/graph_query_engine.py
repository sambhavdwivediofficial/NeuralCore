# graphrag/graph_query_engine.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from graphrag.graph_context_builder import GraphContext, build_graph_context
from graphrag.graph_retriever import GraphRetriever
from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.graphrag.query_engine")

_GRAPH_RAG_SYSTEM = """You are an intelligent assistant with access to a structured knowledge graph.
Use the provided graph context (entities and relationships) along with document context to answer questions accurately.
When referencing entities or relationships from the graph, be explicit about the connections.
If the answer requires multi-hop reasoning across entities, show your reasoning step by step."""

_GRAPH_RAG_USER = """Knowledge Graph Context:
{graph_context}

Document Context:
{doc_context}

Question: {query}

Answer:"""


@dataclass(slots=True)
class GraphRAGResponse:
    answer: str
    entities_used: list[dict[str, Any]] = field(default_factory=list)
    relationships_used: list[dict[str, Any]] = field(default_factory=list)
    graph_context_tokens: int = 0
    provider: str = ""
    model: str = ""


class GraphQueryEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.retriever = GraphRetriever(settings)

    async def query(
        self,
        question: str,
        knowledge_base_id: uuid.UUID,
        doc_context: str = "",
        top_k: int = 10,
        max_hops: int | None = None,
        max_context_tokens: int = 2000,
    ) -> GraphRAGResponse:
        graph_results = await self.retriever.search(
            query=question,
            knowledge_base_id=knowledge_base_id,
            top_k=top_k,
            max_hops=max_hops,
        )

        graph_context: GraphContext = await build_graph_context(
            graph_results=graph_results,
            knowledge_base_id=str(knowledge_base_id),
            settings=self.settings,
            max_tokens=max_context_tokens,
        )

        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        prompt = _GRAPH_RAG_USER.format(
            graph_context=graph_context.text,
            doc_context=doc_context[:3000] if doc_context else "No additional document context provided.",
            query=question,
        )

        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[
                    ChatMessage(role=ChatRole.SYSTEM, content=_GRAPH_RAG_SYSTEM),
                    ChatMessage(role=ChatRole.USER, content=prompt),
                ],
                max_tokens=1500,
                temperature=0.1,
            )
        )

        return GraphRAGResponse(
            answer=response.content or "",
            entities_used=graph_context.entities,
            relationships_used=graph_context.relationships,
            graph_context_tokens=graph_context.token_count,
            provider=response.provider,
            model=response.model,
        )
    