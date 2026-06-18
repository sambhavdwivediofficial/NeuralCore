# tools/executor.py
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from monitoring.metrics import AGENT_TASK_DURATION_SECONDS, track_duration
from monitoring.tracing import trace_span
from tools.registry import ToolExecutionError, ToolNotFoundError, get_tool_registry

logger = get_logger("neuralcore.tools.executor")


@dataclass(slots=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]
    call_id: str = ""
    agent_id: str | None = None


@dataclass(slots=True)
class ToolResult:
    call_id: str
    tool_name: str
    result: Any
    success: bool
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_string(self) -> str:
        if not self.success:
            return f"[Tool Error] {self.tool_name}: {self.error}"
        if isinstance(self.result, str):
            return self.result
        import json
        return json.dumps(self.result, ensure_ascii=False, indent=2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "result": self.result,
            "success": self.success,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


class ToolExecutor:
    def __init__(self, agent_id: str | None = None, max_parallel: int = 4) -> None:
        self.agent_id = agent_id
        self.max_parallel = max_parallel
        self._registry = get_tool_registry()
        self._call_history: list[ToolResult] = []

    async def execute(self, call: ToolCall) -> ToolResult:
        start = time.perf_counter()
        with trace_span("tool.execute", tool_name=call.tool_name, agent_id=self.agent_id or ""):
            try:
                result = await self._registry.execute(call.tool_name, call.arguments)
                duration_ms = (time.perf_counter() - start) * 1000
                tool_result = ToolResult(
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    result=result,
                    success=True,
                    duration_ms=round(duration_ms, 2),
                )
                logger.debug("tool_execution_success", tool=call.tool_name, duration_ms=tool_result.duration_ms, agent_id=self.agent_id)
            except (ToolNotFoundError, ToolExecutionError) as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                tool_result = ToolResult(
                    call_id=call.call_id,
                    tool_name=call.tool_name,
                    result=None,
                    success=False,
                    error=str(exc),
                    duration_ms=round(duration_ms, 2),
                )
                logger.warning("tool_execution_failed", tool=call.tool_name, error=str(exc), agent_id=self.agent_id)

        self._call_history.append(tool_result)
        return tool_result

    async def execute_parallel(self, calls: list[ToolCall]) -> list[ToolResult]:
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def _bounded(call: ToolCall) -> ToolResult:
            async with semaphore:
                return await self.execute(call)

        return list(await asyncio.gather(*[_bounded(call) for call in calls]))

    async def execute_sequential(self, calls: list[ToolCall]) -> list[ToolResult]:
        results: list[ToolResult] = []
        for call in calls:
            result = await self.execute(call)
            results.append(result)
            if not result.success:
                break
        return results

    def get_history(self) -> list[ToolResult]:
        return list(self._call_history)

    def clear_history(self) -> None:
        self._call_history.clear()

    def format_results_for_llm(self, results: list[ToolResult]) -> str:
        return "\n".join(
            f"Tool: {r.tool_name}\nResult: {r.to_string()}\n"
            for r in results
        )
