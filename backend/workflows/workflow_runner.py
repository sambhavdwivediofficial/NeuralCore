# workflows/workflow_runner.py
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from monitoring.tracing import trace_span
from settings import Settings
from workflows.workflow_engine import get_ready_steps
from workflows.workflow_executor import StepExecutor, StepResult, WorkflowExecutionContext
from workflows.workflow_registry import StepDefinition, WorkflowTemplate

logger = get_logger("neuralcore.workflows.runner")


@dataclass(slots=True)
class WorkflowRunResult:
    workflow_run_id: str
    status: str
    step_results: dict[str, StepResult] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_run_id": self.workflow_run_id,
            "status": self.status,
            "step_results": {k: v.to_dict() for k, v in self.step_results.items()},
            "output": self.output,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class WorkflowRunner:
    def __init__(self, settings: Settings, max_parallel_steps: int = 4) -> None:
        self.settings = settings
        self.max_parallel_steps = max_parallel_steps
        self.executor = StepExecutor(settings)

    async def run(
        self,
        template: WorkflowTemplate,
        input_data: dict[str, Any],
        organization_id: str | None = None,
        project_id: str | None = None,
    ) -> WorkflowRunResult:
        run_id = uuid.uuid4().hex
        context = WorkflowExecutionContext(
            workflow_run_id=run_id,
            input=input_data,
            organization_id=organization_id,
            project_id=project_id,
        )

        start = time.perf_counter()
        completed_ids: set[str] = set()
        failed_ids: set[str] = set()
        step_results: dict[str, StepResult] = {}
        semaphore = asyncio.Semaphore(self.max_parallel_steps)

        with trace_span("workflow.run", workflow=template.name, run_id=run_id):
            while len(completed_ids) + len(failed_ids) < len(template.steps):
                ready = get_ready_steps(template.steps, completed_ids, failed_ids)
                if not ready:
                    break

                async def _run_step(step: StepDefinition) -> tuple[str, StepResult]:
                    async with semaphore:
                        result = await self.executor.execute_step(step, context)
                        return step.id, result

                batch_results = await asyncio.gather(*[_run_step(s) for s in ready])

                for step_id, result in batch_results:
                    step_results[step_id] = result
                    context.step_outputs[step_id] = result.output
                    if result.status in ("completed", "skipped"):
                        completed_ids.add(step_id)
                    else:
                        failed_ids.add(step_id)

        duration_ms = (time.perf_counter() - start) * 1000
        overall_status = "completed" if not failed_ids else "failed"
        first_error = next((r.error for r in step_results.values() if r.error), None)

        last_step_output = None
        if template.steps:
            last_step = template.steps[-1]
            last_step_output = context.step_outputs.get(last_step.id)

        logger.info(
            "workflow_run_complete",
            workflow=template.name,
            run_id=run_id,
            status=overall_status,
            duration_ms=round(duration_ms, 2),
            steps_completed=len(completed_ids),
            steps_failed=len(failed_ids),
        )

        return WorkflowRunResult(
            workflow_run_id=run_id,
            status=overall_status,
            step_results=step_results,
            output={"final": last_step_output, "all_steps": context.step_outputs},
            duration_ms=duration_ms,
            error=first_error,
        )

    async def run_by_template_id(
        self,
        template_id: str,
        input_data: dict[str, Any],
        organization_id: str | None = None,
        project_id: str | None = None,
    ) -> WorkflowRunResult:
        from workflows.workflow_registry import get_workflow_registry

        registry = get_workflow_registry()
        template = registry.get_template(template_id)
        if template is None:
            raise ValueError(f"Workflow template '{template_id}' not found")
        return await self.run(template, input_data, organization_id, project_id)
