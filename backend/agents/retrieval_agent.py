# agents/retrieval_agent.py
from __future__ import annotations

import uuid
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.agents.retrieval_agent")


class RetrievalAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def retrieve_and_synthesize(
        self,
        query: str,
        knowledge_base_id: uuid.UUID,
        top_k: int | None = None,
        use_graph: bool = True,
    ) -> dict[str, Any]:
        from retrieval.retriever import Retriever

        retriever = Retriever(settings=self.settings)
        results = await retriever.search(
            knowledge_base_id=knowledge_base_id,
            query=query,
            top_k=top_k or self.settings.retrieval.vector_search.default_top_k,
            use_hybrid=True,
            use_reranking=True,
            use_graph=use_graph,
        )

        context_chunks = [r.text or "" for r in results if r.text]
        combined_context = "\n\n".join(context_chunks)

        from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
        from model_gateway.provider_factory import get_model_gateway
        from prompt_engine.template_engine import default_registry

        gateway = get_model_gateway(self.settings)
        user_content = default_registry.render("rag_qa", context=combined_context, question=query)

        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[
                    ChatMessage(role=ChatRole.SYSTEM, content="You are a knowledgeable assistant. Answer based on the provided context."),
                    ChatMessage(role=ChatRole.USER, content=user_content),
                ],
                max_tokens=1024,
                temperature=0.1,
            )
        )

        return {
            "answer": (response.content or "").strip(),
            "sources": [{"id": r.id, "score": r.score, "metadata": r.metadata} for r in results],
            "chunks_used": len(context_chunks),
        }
