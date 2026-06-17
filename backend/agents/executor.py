# agents/executor.py
from __future__ import annotations

from typing import Any

from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.agents.executor")

_EXECUTOR_SYSTEM = (
    "You are a precise task executor. Execute the given task step accurately, "
    "using available tools when necessary. Report your findings clearly and concisely."
)


class ExecutorAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def execute_step(
        self,
        step_description: str,
        context: str = "",
        tool_results: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
    ) -> str:
        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(self.settings)
        parts = [f"Task: {step_description}"]
        if context:
            parts.append(f"Context:\n{context}")
        if tool_results:
            for tr in tool_results:
                parts.append(f"Tool [{tr.get('tool')}]: {tr.get('result', '')}")
        parts.append("Execute the task and provide your output:")
        user_content = "\n\n".join(parts)

        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[
                    ChatMessage(role=ChatRole.SYSTEM, content=_EXECUTOR_SYSTEM),
                    ChatMessage(role=ChatRole.USER, content=user_content),
                ],
                max_tokens=max_tokens,
                temperature=0.1,
            )
        )
        return (response.content or "").strip()
