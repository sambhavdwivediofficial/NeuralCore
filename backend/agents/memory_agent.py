# agents/memory_agent.py
from __future__ import annotations

import uuid
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.agents.memory_agent")


class MemoryAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def consolidate_memories(
        self,
        agent_id: uuid.UUID,
        session_id: str,
        memory_manager: Any,
    ) -> dict[str, Any]:
        from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
        from model_gateway.provider_factory import get_model_gateway
        from prompt_engine.template_engine import default_registry

        messages = await memory_manager._short_term.get_all(str(agent_id), session_id)
        if not messages:
            return {"consolidated": 0, "stored": False}

        conversation_text = "\n".join(
            f"{msg.role.capitalize()}: {msg.content}" for msg in messages
        )
        gateway = get_model_gateway(self.settings)
        summary_prompt = default_registry.render("memory_summary", conversation=conversation_text)

        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[ChatMessage(role=ChatRole.USER, content=summary_prompt)],
                max_tokens=512,
                temperature=0.1,
            )
        )

        summary = (response.content or "").strip()
        if summary:
            await memory_manager.store_long_term(
                agent_id=agent_id,
                content=summary,
                importance_score=0.7,
                also_embed=True,
                metadata={"source": "memory_consolidation", "session_id": session_id},
            )
            await memory_manager.record_episode(
                agent_id=agent_id,
                summary=f"Session {session_id}: {summary[:200]}",
                importance_score=0.6,
            )

        return {"consolidated": len(messages), "stored": bool(summary), "summary_preview": summary[:200]}

    async def retrieve_relevant_memories(
        self,
        agent_id: uuid.UUID,
        query: str,
        memory_manager: Any,
        top_k: int = 5,
    ) -> str:
        context = await memory_manager.get_context(
            agent_id=agent_id,
            session_id="",
            query=query,
            max_tokens=2000,
            include_semantic=True,
            include_episodic=True,
        )
        return memory_manager.format_context_as_text(context)
