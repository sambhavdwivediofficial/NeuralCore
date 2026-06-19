# workflows/workflow_builder.py
from __future__ import annotations

import uuid
from typing import Any

from monitoring.logging import get_logger
from workflows.workflow_registry import StepDefinition, StepType, WorkflowTemplate

logger = get_logger("neuralcore.workflows.builder")


class WorkflowBuilderError(ValueError):
    pass


class WorkflowBuilder:
    def __init__(self, name: str, description: str = "") -> None:
        self.name = name
        self.description = description
        self._steps: list[StepDefinition] = []
        self._input_schema: dict[str, Any] = {}
        self._metadata: dict[str, Any] = {}

    def add_step(
        self,
        step_id: str,
        step_type: StepType,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
        condition: str | None = None,
        retry_count: int = 0,
        timeout_seconds: float = 120.0,
    ) -> "WorkflowBuilder":
        if any(s.id == step_id for s in self._steps):
            raise WorkflowBuilderError(f"Step ID '{step_id}' already exists")

        for dep_id in (depends_on or []):
            if not any(s.id == dep_id for s in self._steps):
                raise WorkflowBuilderError(f"Step '{step_id}' depends on unknown step '{dep_id}'")

        step = StepDefinition(
            id=step_id,
            type=step_type,
            name=name or step_id,
            config=config or {},
            depends_on=depends_on or [],
            condition=condition,
            retry_count=retry_count,
            timeout_seconds=timeout_seconds,
        )
        self._steps.append(step)
        return self

    def add_retrieval_step(
        self, step_id: str, knowledge_base_id: str, query_template: str = "{input}", depends_on: list[str] | None = None
    ) -> "WorkflowBuilder":
        return self.add_step(
            step_id, StepType.RETRIEVAL, config={"knowledge_base_id": knowledge_base_id, "query_template": query_template, "top_k": 10},
            depends_on=depends_on,
        )

    def add_llm_step(
        self, step_id: str, prompt_template: str, provider: str | None = None, depends_on: list[str] | None = None
    ) -> "WorkflowBuilder":
        return self.add_step(
            step_id, StepType.LLM_CALL, config={"prompt_template": prompt_template, "provider": provider, "max_tokens": 1024},
            depends_on=depends_on,
        )

    def add_agent_step(
        self, step_id: str, agent_id: str, task_template: str = "{input}", depends_on: list[str] | None = None
    ) -> "WorkflowBuilder":
        return self.add_step(
            step_id, StepType.AGENT_RUN, config={"agent_id": agent_id, "task_template": task_template},
            depends_on=depends_on,
        )

    def add_tool_step(
        self, step_id: str, tool_name: str, arguments_template: dict[str, Any], depends_on: list[str] | None = None
    ) -> "WorkflowBuilder":
        return self.add_step(
            step_id, StepType.TOOL_CALL, config={"tool_name": tool_name, "arguments_template": arguments_template},
            depends_on=depends_on,
        )

    def add_condition_step(
        self, step_id: str, condition_expr: str, depends_on: list[str] | None = None
    ) -> "WorkflowBuilder":
        return self.add_step(step_id, StepType.CONDITION, condition=condition_expr, depends_on=depends_on)

    def add_parallel_step(
        self, step_id: str, branch_step_ids: list[str], depends_on: list[str] | None = None
    ) -> "WorkflowBuilder":
        return self.add_step(
            step_id, StepType.PARALLEL, config={"branches": branch_step_ids}, depends_on=depends_on,
        )

    def with_input_schema(self, schema: dict[str, Any]) -> "WorkflowBuilder":
        self._input_schema = schema
        return self

    def with_metadata(self, metadata: dict[str, Any]) -> "WorkflowBuilder":
        self._metadata = metadata
        return self

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self._steps:
            errors.append("Workflow must contain at least one step")

        step_ids = {s.id for s in self._steps}
        for step in self._steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    errors.append(f"Step '{step.id}' references unknown dependency '{dep}'")

        if _has_cycle(self._steps):
            errors.append("Workflow contains a circular dependency")

        return errors

    def build(self) -> WorkflowTemplate:
        errors = self.validate()
        if errors:
            raise WorkflowBuilderError(f"Workflow validation failed: {'; '.join(errors)}")

        return WorkflowTemplate(
            template_id=uuid.uuid4().hex,
            name=self.name,
            description=self.description,
            steps=self._steps,
            input_schema=self._input_schema,
            metadata=self._metadata,
        )

    def to_definition_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self._steps],
            "input_schema": self._input_schema,
            "metadata": self._metadata,
        }


def _has_cycle(steps: list[StepDefinition]) -> bool:
    graph = {s.id: s.depends_on for s in steps}
    visiting: set[str] = set()
    visited: set[str] = set()

    def _dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbor in graph.get(node, []):
            if _dfs(neighbor):
                return True
        visiting.discard(node)
        visited.add(node)
        return False

    return any(_dfs(step_id) for step_id in graph)


def builder_from_definition(definition: dict[str, Any]) -> WorkflowBuilder:
    builder = WorkflowBuilder(name=definition["name"], description=definition.get("description", ""))
    for step_data in definition.get("steps", []):
        step = StepDefinition.from_dict(step_data)
        builder.add_step(
            step.id, step.type, name=step.name, config=step.config, depends_on=step.depends_on,
            condition=step.condition, retry_count=step.retry_count, timeout_seconds=step.timeout_seconds,
        )
    builder.with_input_schema(definition.get("input_schema", {}))
    builder.with_metadata(definition.get("metadata", {}))
    return builder
