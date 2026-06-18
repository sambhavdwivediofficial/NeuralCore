# evaluation/agent_eval.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.evaluation.agent")


@dataclass(slots=True)
class AgentEvalTask:
    task_description: str
    expected_output_keywords: list[str]
    expected_tool_calls: list[str] = field(default_factory=list)
    max_steps: int = 10
    timeout_seconds: float = 120.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentEvalResult:
    task: str
    completed: bool
    steps_taken: int
    tools_called: list[str]
    output_keyword_match_rate: float
    tool_call_accuracy: float
    latency_ms: float
    error: str | None = None

    @property
    def overall_score(self) -> float:
        if not self.completed:
            return 0.0
        return (self.output_keyword_match_rate + self.tool_call_accuracy) / 2.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task[:200],
            "completed": self.completed,
            "steps_taken": self.steps_taken,
            "tools_called": self.tools_called,
            "output_keyword_match_rate": round(self.output_keyword_match_rate, 4),
            "tool_call_accuracy": round(self.tool_call_accuracy, 4),
            "overall_score": round(self.overall_score, 4),
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
        }


async def evaluate_agent_task(
    agent_id: uuid.UUID,
    eval_task: AgentEvalTask,
    settings: Settings,
) -> AgentEvalResult:
    import time
    from database.connection import get_session_factory
    from task_queue.redis import get_redis_client
    from agents.runtime.state_manager import AgentStateManager
    from agents.runtime.checkpoint import CheckpointManager
    from agents.runtime.lifecycle import AgentLifecycleManager
    from agents.runtime.runtime import AgentRuntime
    from database.repositories.agent_repository import AgentRepository

    start = time.perf_counter()
    session_factory = get_session_factory()
    redis = get_redis_client(settings)

    async with session_factory() as session:
        repo = AgentRepository(session)
        agent = await repo.get_by_id(agent_id)
        if agent is None:
            return AgentEvalResult(
                task=eval_task.task_description, completed=False, steps_taken=0,
                tools_called=[], output_keyword_match_rate=0.0, tool_call_accuracy=0.0,
                latency_ms=0.0, error=f"Agent {agent_id} not found",
            )

        state_manager = AgentStateManager(redis)
        checkpoint_manager = CheckpointManager(redis)
        lifecycle = AgentLifecycleManager(session, state_manager)
        runtime = AgentRuntime(settings, state_manager, checkpoint_manager, lifecycle)

        try:
            result = await asyncio.wait_for(
                runtime.run(agent, eval_task.task_description),
                timeout=eval_task.timeout_seconds,
            )
        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - start) * 1000
            return AgentEvalResult(
                task=eval_task.task_description, completed=False, steps_taken=0,
                tools_called=[], output_keyword_match_rate=0.0, tool_call_accuracy=0.0,
                latency_ms=latency_ms, error="Evaluation timed out",
            )

    latency_ms = (time.perf_counter() - start) * 1000
    output = result.get("output", "").lower()
    keywords_found = sum(1 for kw in eval_task.expected_output_keywords if kw.lower() in output)
    keyword_match_rate = keywords_found / max(len(eval_task.expected_output_keywords), 1)

    state = await state_manager.load(str(agent_id))
    tools_called = list({tc["tool"] for tc in (state.tool_calls if state else [])})
    expected_tools = set(eval_task.expected_tool_calls)
    tool_accuracy = len(set(tools_called) & expected_tools) / max(len(expected_tools), 1) if expected_tools else 1.0

    return AgentEvalResult(
        task=eval_task.task_description,
        completed=result.get("status") == "completed",
        steps_taken=result.get("steps", 0),
        tools_called=tools_called,
        output_keyword_match_rate=keyword_match_rate,
        tool_call_accuracy=tool_accuracy,
        latency_ms=latency_ms,
    )
