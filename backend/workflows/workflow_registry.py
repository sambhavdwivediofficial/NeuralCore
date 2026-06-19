# workflows/workflow_registry.py
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Callable

from monitoring.logging import get_logger

logger = get_logger("neuralcore.workflows.registry")


class StepType(str, enum.Enum):
    RETRIEVAL = "retrieval"
    LLM_CALL = "llm_call"
    AGENT_RUN = "agent_run"
    TOOL_CALL = "tool_call"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    TRANSFORM = "transform"
    HUMAN_INPUT = "human_input"


@dataclass(slots=True, frozen=True)
class StepDefinition:
    id: str
    type: StepType
    name: str
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    condition: str | None = None
    retry_count: int = 0
    timeout_seconds: float = 120.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "config": self.config,
            "depends_on": self.depends_on,
            "condition": self.condition,
            "retry_count": self.retry_count,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepDefinition":
        return cls(
            id=data["id"],
            type=StepType(data["type"]),
            name=data.get("name", data["id"]),
            config=data.get("config", {}),
            depends_on=data.get("depends_on", []),
            condition=data.get("condition"),
            retry_count=data.get("retry_count", 0),
            timeout_seconds=data.get("timeout_seconds", 120.0),
        )


@dataclass(slots=True, frozen=True)
class WorkflowTemplate:
    template_id: str
    name: str
    description: str
    steps: list[StepDefinition]
    input_schema: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_definition(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "input_schema": self.input_schema,
            "metadata": self.metadata,
        }


StepHandler = Callable[..., Any]


class WorkflowRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, WorkflowTemplate] = {}
        self._step_handlers: dict[StepType, StepHandler] = {}

    def register_template(self, template: WorkflowTemplate) -> None:
        self._templates[template.template_id] = template
        logger.debug("workflow_template_registered", template_id=template.template_id)

    def get_template(self, template_id: str) -> WorkflowTemplate | None:
        return self._templates.get(template_id)

    def list_templates(self) -> list[WorkflowTemplate]:
        return list(self._templates.values())

    def register_step_handler(self, step_type: StepType, handler: StepHandler) -> None:
        self._step_handlers[step_type] = handler

    def get_step_handler(self, step_type: StepType) -> StepHandler | None:
        return self._step_handlers.get(step_type)


_global_registry: WorkflowRegistry | None = None


def get_workflow_registry() -> WorkflowRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = WorkflowRegistry()
        _register_builtin_templates(_global_registry)
    return _global_registry


def _register_builtin_templates(registry: WorkflowRegistry) -> None:
    from workflows.templates.agentic_rag import AGENTIC_RAG_TEMPLATE
    from workflows.templates.code_assistant import CODE_ASSISTANT_TEMPLATE
    from workflows.templates.rag import RAG_TEMPLATE
    from workflows.templates.research import RESEARCH_TEMPLATE

    registry.register_template(RAG_TEMPLATE)
    registry.register_template(AGENTIC_RAG_TEMPLATE)
    registry.register_template(RESEARCH_TEMPLATE)
    registry.register_template(CODE_ASSISTANT_TEMPLATE)
