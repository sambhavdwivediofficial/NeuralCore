# agents/runtime/runtime.py
from __future__ import annotations

import asyncio
import uuid
from typing import Any

from agents.runtime.checkpoint import CheckpointManager
from agents.runtime.event_bus import AgentEvent, get_event_bus
from agents.runtime.lifecycle import AgentLifecycleManager
from agents.runtime.state_manager import AgentState, AgentStateManager
from database.models.agent import Agent, AgentStatus
from model_gateway.base_provider import (
    ChatMessage,
    ChatRole,
    CompletionRequest,
    ToolCall,
    ToolDefinition,
)
from monitoring.logging import get_logger, log_slow_llm_call
from monitoring.tracing import trace_span
from settings import Settings

logger = get_logger("neuralcore.agents.runtime")

_MAX_CONSECUTIVE_ERRORS = 3


class AgentRuntime:
    def __init__(
        self,
        settings: Settings,
        state_manager: AgentStateManager,
        checkpoint_manager: CheckpointManager,
        lifecycle: AgentLifecycleManager,
    ) -> None:
        self.settings = settings
        self.state_manager = state_manager
        self.checkpoint_manager = checkpoint_manager
        self.lifecycle = lifecycle
        self.bus = get_event_bus()

    async def run(
        self,
        agent: Agent,
        task: str,
        tools: list[ToolDefinition] | None = None,
        session_id: str | None = None,
        context: str = "",
    ) -> dict[str, Any]:
        from model_gateway.provider_factory import get_model_gateway
        from tools.registry import get_tool_registry

        agent_id_str = str(agent.id)
        state = await self.lifecycle.initialize(agent, task_description=task, session_id=session_id)
        await self.lifecycle.start(agent.id)

        tool_registry = get_tool_registry()
        available_tools: list[ToolDefinition] = tools or tool_registry.get_definitions(agent.tools)
        gateway = get_model_gateway(self.settings)

        messages: list[ChatMessage] = []
        if agent.system_prompt:
            messages.append(ChatMessage(role=ChatRole.SYSTEM, content=agent.system_prompt))
        if context:
            messages.append(ChatMessage(role=ChatRole.SYSTEM, content=f"Context:\n{context}"))
        messages.append(ChatMessage(role=ChatRole.USER, content=task))

        consecutive_errors = 0
        final_output = ""

        with trace_span("agent.run", agent_id=agent_id_str, agent_type=agent.agent_type.value):
            while await self.lifecycle.can_continue(agent.id):
                step = await self.state_manager.increment_step(agent_id_str)
                await self.bus.emit(AgentEvent.STEP_STARTED, agent_id_str, {"step": step})

                try:
                    with log_slow_llm_call(self.settings, agent.model_provider, agent.model_name):
                        response = await gateway.chat_completion(
                            CompletionRequest(
                                messages=messages,
                                model=agent.model_name,
                                tools=available_tools if available_tools else None,
                                max_tokens=2048,
                                temperature=0.1,
                            ),
                            provider_name=agent.model_provider,
                        )
                    consecutive_errors = 0
                except Exception as exc:
                    consecutive_errors += 1
                    logger.warning("agent_step_llm_error", agent_id=agent_id_str, step=step, error=str(exc))
                    if consecutive_errors >= _MAX_CONSECUTIVE_ERRORS:
                        await self.lifecycle.fail(agent.id, str(exc))
                        return {"status": "failed", "error": str(exc), "steps": step}
                    await asyncio.sleep(1.0)
                    continue

                if response.tool_calls:
                    messages.append(ChatMessage(role=ChatRole.ASSISTANT, content=response.content, tool_calls=response.tool_calls))
                    for tool_call in response.tool_calls:
                        tool_result = await self._execute_tool(tool_call, tool_registry, agent_id_str)
                        messages.append(ChatMessage(role=ChatRole.TOOL, content=tool_result, tool_call_id=tool_call.id, name=tool_call.name))
                    await self.checkpoint_manager.save(state, messages=[m.model_dump() for m in messages])
                else:
                    final_output = response.content or ""
                    messages.append(ChatMessage(role=ChatRole.ASSISTANT, content=final_output))
                    await self.bus.emit(AgentEvent.STEP_COMPLETED, agent_id_str, {"step": step, "has_output": bool(final_output)})
                    if response.finish_reason and response.finish_reason.value == "stop":
                        break

        await self.lifecycle.complete(agent.id, final_output)
        state_final = await self.state_manager.load(agent_id_str)
        return {
            "status": "completed",
            "output": final_output,
            "steps": state_final.current_step if state_final else 0,
            "tool_calls_count": len(state_final.tool_calls) if state_final else 0,
        }

    async def _execute_tool(
        self,
        tool_call: ToolCall,
        tool_registry: Any,
        agent_id: str,
    ) -> str:
        await self.bus.emit(AgentEvent.TOOL_CALLED, agent_id, {"tool": tool_call.name, "input": tool_call.arguments})
        try:
            result = await tool_registry.execute(tool_call.name, tool_call.arguments)
            result_str = str(result)[:4096]
        except Exception as exc:
            result_str = f"Error executing {tool_call.name}: {exc}"
            logger.warning("tool_execution_error", agent_id=agent_id, tool=tool_call.name, error=str(exc))

        await self.bus.emit(AgentEvent.TOOL_RESULT, agent_id, {"tool": tool_call.name, "result": result_str[:200]})
        await self.state_manager.record_tool_call(agent_id, tool_call.name, tool_call.arguments, result_str)
        return result_str
    