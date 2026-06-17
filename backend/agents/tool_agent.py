# agents/tool_agent.py
from __future__ import annotations

from typing import Any

from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest, ToolDefinition
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.agents.tool_agent")

_TOOL_SYSTEM = (
    "You are a specialized tool-calling assistant. "
    "Use the available tools precisely and efficiently to complete tasks. "
    "Always verify tool outputs before using them in your response. "
    "If a tool fails, try an alternative approach or report the issue clearly."
)


class ToolAgent:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def execute_with_tools(
        self,
        task: str,
        available_tools: list[str],
        context: str = "",
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        from model_gateway.provider_factory import get_model_gateway
        from tools.registry import get_tool_registry

        gateway = get_model_gateway(self.settings)
        tool_registry = get_tool_registry()
        tool_definitions = tool_registry.get_definitions(available_tools)

        messages: list[ChatMessage] = [
            ChatMessage(role=ChatRole.SYSTEM, content=_TOOL_SYSTEM),
        ]
        if context:
            messages.append(ChatMessage(role=ChatRole.SYSTEM, content=f"Context:\n{context}"))
        messages.append(ChatMessage(role=ChatRole.USER, content=task))

        tool_calls_log: list[dict[str, Any]] = []
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            response = await gateway.chat_completion(
                CompletionRequest(
                    messages=messages,
                    tools=tool_definitions if tool_definitions else None,
                    max_tokens=1024,
                    temperature=0.0,
                )
            )

            if not response.tool_calls:
                return {
                    "output": (response.content or "").strip(),
                    "tool_calls": tool_calls_log,
                    "iterations": iterations,
                }

            messages.append(ChatMessage(role=ChatRole.ASSISTANT, content=response.content, tool_calls=response.tool_calls))

            for tool_call in response.tool_calls:
                try:
                    result = await tool_registry.execute(tool_call.name, tool_call.arguments)
                    result_str = str(result)[:4096]
                except Exception as exc:
                    result_str = f"Error: {exc}"
                    logger.warning("tool_agent_tool_error", tool=tool_call.name, error=str(exc))

                tool_calls_log.append({"tool": tool_call.name, "input": tool_call.arguments, "result": result_str})
                messages.append(ChatMessage(role=ChatRole.TOOL, content=result_str, tool_call_id=tool_call.id, name=tool_call.name))

        return {"output": "Max iterations reached", "tool_calls": tool_calls_log, "iterations": iterations}
