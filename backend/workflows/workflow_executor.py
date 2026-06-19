# workflows/workflow_executor.py
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from monitoring.tracing import trace_span
from settings import Settings
from workflows.workflow_engine import evaluate_condition, get_ready_steps, render_template_dict, render_template_string
from workflows.workflow_registry import StepDefinition, StepType

logger = get_logger("neuralcore.workflows.executor")


class StepExecutionError(RuntimeError):
    def __init__(self, step_id: str, cause: Exception) -> None:
        self.step_id = step_id
        self.cause = cause
        super().__init__(f"Step '{step_id}' failed: {cause}")


@dataclass(slots=True)
class StepResult:
    step_id: str
    status: str
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"step_id": self.step_id, "status": self.status, "output": self.output, "error": self.error, "duration_ms": self.duration_ms}


@dataclass(slots=True)
class WorkflowExecutionContext:
    workflow_run_id: str
    input: dict[str, Any]
    step_outputs: dict[str, Any] = field(default_factory=dict)
    organization_id: str | None = None
    project_id: str | None = None

    def as_template_context(self) -> dict[str, Any]:
        return {"input": self.input, "steps": self.step_outputs, "run_id": self.workflow_run_id}


class StepExecutor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def execute_step(self, step: StepDefinition, context: WorkflowExecutionContext) -> StepResult:
        start = time.perf_counter()
        template_ctx = context.as_template_context()

        try:
            if step.condition and not evaluate_condition(step.condition, template_ctx):
                return StepResult(step_id=step.id, status="skipped", duration_ms=(time.perf_counter() - start) * 1000)

            output = await self._dispatch(step, template_ctx)
            duration_ms = (time.perf_counter() - start) * 1000
            return StepResult(step_id=step.id, status="completed", output=output, duration_ms=duration_ms)

        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.warning("workflow_step_failed", step_id=step.id, error=str(exc))
            return StepResult(step_id=step.id, status="failed", error=str(exc), duration_ms=duration_ms)

    async def _dispatch(self, step: StepDefinition, template_ctx: dict[str, Any]) -> Any:
        handler_map = {
            StepType.RETRIEVAL: self._run_retrieval,
            StepType.LLM_CALL: self._run_llm_call,
            StepType.AGENT_RUN: self._run_agent,
            StepType.TOOL_CALL: self._run_tool,
            StepType.TRANSFORM: self._run_transform,
            StepType.PARALLEL: self._run_parallel,
            StepType.CONDITION: self._run_noop,
            StepType.LOOP: self._run_noop,
            StepType.HUMAN_INPUT: self._run_noop,
        }
        handler = handler_map.get(step.type)
        if handler is None:
            raise StepExecutionError(step.id, ValueError(f"No handler for step type '{step.type.value}'"))

        return await asyncio.wait_for(handler(step, template_ctx), timeout=step.timeout_seconds)

    async def _run_retrieval(self, step: StepDefinition, ctx: dict[str, Any]) -> dict[str, Any]:
        import uuid as _uuid
        from retrieval.retriever import Retriever

        config = render_template_dict(step.config, ctx)
        retriever = Retriever(settings=self.settings)
        results = await retriever.search(
            knowledge_base_id=_uuid.UUID(config["knowledge_base_id"]),
            query=config.get("query_template", ctx.get("input", {}).get("query", "")),
            top_k=int(config.get("top_k", 10)),
        )
        return {"results": [{"id": r.id, "score": r.score, "text": r.text} for r in results], "count": len(results)}

    async def _run_llm_call(self, step: StepDefinition, ctx: dict[str, Any]) -> dict[str, Any]:
        from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
        from model_gateway.provider_factory import get_model_gateway

        config = render_template_dict(step.config, ctx)
        gateway = get_model_gateway(self.settings)
        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[ChatMessage(role=ChatRole.USER, content=config["prompt_template"])],
                max_tokens=int(config.get("max_tokens", 1024)),
                temperature=float(config.get("temperature", 0.7)),
            ),
            provider_name=config.get("provider"),
        )
        return {"content": response.content, "provider": response.provider, "model": response.model}

    async def _run_agent(self, step: StepDefinition, ctx: dict[str, Any]) -> dict[str, Any]:
        import uuid as _uuid
        from database.connection import get_session_factory
        from database.repositories.agent_repository import AgentRepository
        from task_queue.redis import get_redis_client
        from agents.runtime.state_manager import AgentStateManager
        from agents.runtime.checkpoint import CheckpointManager
        from agents.runtime.lifecycle import AgentLifecycleManager
        from agents.runtime.runtime import AgentRuntime

        config = render_template_dict(step.config, ctx)
        session_factory = get_session_factory()
        redis = get_redis_client(self.settings)

        async with session_factory() as session:
            repo = AgentRepository(session)
            agent = await repo.get_by_id(_uuid.UUID(config["agent_id"]))
            if agent is None:
                raise ValueError(f"Agent {config['agent_id']} not found")

            state_manager = AgentStateManager(redis)
            checkpoint_manager = CheckpointManager(redis)
            lifecycle = AgentLifecycleManager(session, state_manager)
            runtime = AgentRuntime(self.settings, state_manager, checkpoint_manager, lifecycle)
            return await runtime.run(agent, config.get("task_template", ""))

    async def _run_tool(self, step: StepDefinition, ctx: dict[str, Any]) -> Any:
        from tools.registry import get_tool_registry

        config = step.config
        tool_name = config["tool_name"]
        arguments = render_template_dict(config.get("arguments_template", {}), ctx)
        registry = get_tool_registry()
        return await registry.execute(tool_name, arguments)

    async def _run_transform(self, step: StepDefinition, ctx: dict[str, Any]) -> Any:
        config = step.config
        source_path = config.get("source", "")
        return render_template_string(source_path, ctx)

    async def _run_parallel(self, step: StepDefinition, ctx: dict[str, Any]) -> dict[str, Any]:
        return {"branches": step.config.get("branches", [])}

    async def _run_noop(self, step: StepDefinition, ctx: dict[str, Any]) -> Any:
        return None
