# workflows/templates/code_assistant.py
from __future__ import annotations

from workflows.workflow_registry import StepDefinition, StepType, WorkflowTemplate

CODE_ASSISTANT_TEMPLATE = WorkflowTemplate(
    template_id="code_assistant",
    name="Code Assistant Pipeline",
    description="Retrieve relevant code context from a codebase knowledge base, generate code, then run an automated review pass.",
    steps=[
        StepDefinition(
            id="retrieve_code_context",
            type=StepType.RETRIEVAL,
            name="Retrieve Code Context",
            config={"knowledge_base_id": "{input.knowledge_base_id}", "query_template": "{input.task}", "top_k": 8},
        ),
        StepDefinition(
            id="generate_code",
            type=StepType.AGENT_RUN,
            name="Generate Code",
            config={"agent_id": "{input.coding_agent_id}", "task_template": "Context:\n{steps.retrieve_code_context.results}\n\nTask: {input.task}"},
            depends_on=["retrieve_code_context"],
            timeout_seconds=180.0,
        ),
        StepDefinition(
            id="review_code",
            type=StepType.LLM_CALL,
            name="Review Generated Code",
            config={
                "prompt_template": "Review this code for correctness, security, and best practices:\n\n{steps.generate_code.output}",
                "max_tokens": 1024,
                "temperature": 0.1,
            },
            depends_on=["generate_code"],
        ),
    ],
    input_schema={"type": "object", "properties": {"task": {"type": "string"}, "knowledge_base_id": {"type": "string"}, "coding_agent_id": {"type": "string"}}, "required": ["task", "coding_agent_id"]},
    metadata={"category": "code_assistant", "estimated_duration_seconds": 25},
)
