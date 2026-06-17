# agents/research_agent.py
from __future__ import annotations

import asyncio
from typing import Any

from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.agents.research_agent")

_RESEARCH_SYSTEM = (
    "You are a rigorous research assistant. Analyze multiple sources, "
    "synthesize findings, identify contradictions, and produce well-structured research summaries. "
    "Always cite which source supports each claim."
)


class ResearchAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def research_topic(
        self,
        topic: str,
        sub_queries: list[str] | None = None,
        knowledge_base_ids: list[str] | None = None,
        max_sources: int = 10,
    ) -> dict[str, Any]:
        from retrieval.retriever import Retriever

        retriever = Retriever(settings=self.settings)
        queries = sub_queries or [topic]
        all_results: list[dict[str, Any]] = []

        semaphore = asyncio.Semaphore(3)

        async def _search_query(query: str) -> None:
            async with semaphore:
                import uuid as _uuid
                kb_id = _uuid.UUID(int=0) if not knowledge_base_ids else _uuid.UUID(knowledge_base_ids[0])
                results = await retriever.search(knowledge_base_id=kb_id, query=query, top_k=5)
                for r in results:
                    all_results.append({
                        "query": query,
                        "text": r.text or "",
                        "score": r.score,
                        "source": r.metadata.get("source_type", "unknown"),
                    })

        await asyncio.gather(*[_search_query(q) for q in queries])
        all_results = sorted(all_results, key=lambda x: x["score"], reverse=True)[:max_sources]

        context_parts = [f"[Source {i+1}] {r['text']}" for i, r in enumerate(all_results)]
        combined_context = "\n\n".join(context_parts)

        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        synthesis_prompt = (
            f"Research Topic: {topic}\n\n"
            f"Sources:\n{combined_context}\n\n"
            "Provide a comprehensive research summary that:\n"
            "1. Synthesizes key findings\n"
            "2. Identifies common themes\n"
            "3. Notes any contradictions or gaps\n"
            "4. References specific sources by number\n\n"
            "Research Summary:"
        )

        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[
                    ChatMessage(role=ChatRole.SYSTEM, content=_RESEARCH_SYSTEM),
                    ChatMessage(role=ChatRole.USER, content=synthesis_prompt),
                ],
                max_tokens=2000,
                temperature=0.1,
            )
        )

        return {
            "topic": topic,
            "summary": (response.content or "").strip(),
            "sources_used": len(all_results),
            "queries_executed": len(queries),
            "raw_sources": all_results,
        }
