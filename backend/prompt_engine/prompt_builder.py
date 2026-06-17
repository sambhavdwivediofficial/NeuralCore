# prompt_engine/prompt_builder.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chunking.base_chunker import count_tokens
from model_gateway.base_provider import ChatMessage, ChatRole
from monitoring.logging import get_logger
from prompt_engine.context_builder import ContextBuilder
from prompt_engine.template_engine import PromptTemplate, default_registry
from prompt_engine.token_optimizer import (
    deduplicate_context_chunks,
    format_numbered_context,
    normalize_prompt_whitespace,
    trim_messages_to_fit,
)
from settings import Settings

logger = get_logger("neuralcore.prompt_engine.prompt_builder")


@dataclass(slots=True)
class BuiltPrompt:
    messages: list[ChatMessage]
    system_prompt: str
    user_prompt: str
    total_tokens: int
    context_tokens: int
    template_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PromptBuilder:
    def __init__(self, settings: Settings, max_tokens: int | None = None) -> None:
        self.settings = settings
        self.max_tokens = max_tokens or 8192

    def build_rag_prompt(
        self,
        query: str,
        retrieval_results: list[dict[str, Any]],
        conversation_history: list[dict[str, str]] | None = None,
        system_prompt: str | None = None,
        template_name: str = "rag_qa",
        max_context_tokens: int | None = None,
        deduplicate: bool = True,
    ) -> BuiltPrompt:
        context_token_budget = max_context_tokens or int(self.max_tokens * 0.4)

        chunks = [
            r.get("text") or r.get("content") or r.get("metadata", {}).get("text", "")
            for r in retrieval_results
            if r.get("text") or r.get("content") or r.get("metadata", {}).get("text", "")
        ]

        if deduplicate:
            chunks = deduplicate_context_chunks(chunks)

        context_builder = ContextBuilder(max_tokens=context_token_budget)
        context_builder.add_retrieval_results(retrieval_results, priority=10)
        if conversation_history:
            context_builder.add_conversation_history(
                conversation_history, max_tokens=512, priority=5
            )
        built_ctx = context_builder.build()
        context_text = normalize_prompt_whitespace(built_ctx.full_text)

        template = default_registry.get(template_name)

        if conversation_history and template_name == "rag_qa":
            try:
                template = default_registry.get("rag_with_history")
                history_text = "\n".join(
                    f"{m['role'].capitalize()}: {m['content']}"
                    for m in (conversation_history or [])[-6:]
                )
                user_content = template.render(
                    history=history_text,
                    context=context_text,
                    question=query,
                )
            except Exception:
                user_content = template.render(context=context_text, question=query) if "history" not in template.input_variables else default_registry.render("rag_qa", context=context_text, question=query)
        else:
            user_content = template.render(context=context_text, question=query)

        sys_prompt = system_prompt or "You are a helpful AI assistant."
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=sys_prompt),
            ChatMessage(role=ChatRole.USER, content=user_content),
        ]

        messages_dicts = [{"role": m.role.value, "content": m.content or ""} for m in messages]
        fits, total_tokens = trim_messages_to_fit(
            messages_dicts, self.max_tokens, keep_system=True, reserved_for_completion=512
        ), count_tokens(sys_prompt) + count_tokens(user_content)

        return BuiltPrompt(
            messages=messages,
            system_prompt=sys_prompt,
            user_prompt=user_content,
            total_tokens=total_tokens,
            context_tokens=built_ctx.total_tokens,
            template_name=template_name,
            metadata={
                "sections_included": built_ctx.sections_included,
                "sections_truncated": built_ctx.sections_truncated,
                "sections_omitted": built_ctx.sections_omitted,
                "chunks_used": len(chunks),
                "deduplicated": deduplicate,
            },
        )

    def build_agent_prompt(
        self,
        agent_name: str,
        specialization: str,
        capabilities: list[str],
        tools: list[str],
        instructions: str,
        context: str = "",
        conversation_history: list[dict[str, str]] | None = None,
    ) -> BuiltPrompt:
        sys_content = default_registry.render(
            "agent_system",
            agent_name=agent_name,
            specialization=specialization,
            capabilities="\n".join(f"- {cap}" for cap in capabilities),
            tools="\n".join(f"- {tool}" for tool in tools),
            instructions=instructions,
        )

        user_parts: list[str] = []
        if context:
            user_parts.append(f"Context:\n{normalize_prompt_whitespace(context)}")
        if conversation_history:
            history_text = "\n".join(
                f"{m['role'].capitalize()}: {m['content']}" for m in conversation_history[-8:]
            )
            user_parts.append(f"Conversation:\n{history_text}")

        user_content = "\n\n".join(user_parts) if user_parts else "Begin."
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=sys_content),
            ChatMessage(role=ChatRole.USER, content=user_content),
        ]
        total_tokens = count_tokens(sys_content) + count_tokens(user_content)

        return BuiltPrompt(
            messages=messages,
            system_prompt=sys_content,
            user_prompt=user_content,
            total_tokens=total_tokens,
            context_tokens=count_tokens(context),
            template_name="agent_system",
        )

    def build_custom(
        self,
        template_name: str,
        system_prompt: str = "",
        **template_kwargs: Any,
    ) -> BuiltPrompt:
        user_content = default_registry.render(template_name, **template_kwargs)
        sys_prompt = system_prompt or "You are a helpful AI assistant."
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=sys_prompt),
            ChatMessage(role=ChatRole.USER, content=user_content),
        ]
        total_tokens = count_tokens(sys_prompt) + count_tokens(user_content)
        return BuiltPrompt(
            messages=messages,
            system_prompt=sys_prompt,
            user_prompt=user_content,
            total_tokens=total_tokens,
            context_tokens=0,
            template_name=template_name,
        )
    