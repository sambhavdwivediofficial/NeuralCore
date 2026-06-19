# workflows/templates/agentic_rag.py
from __future__ import annotations

from workflows.workflow_registry import StepDefinition, StepType, WorkflowTemplate

AGENTIC_RAG_TEMPLATE = WorkflowTemplate(
    template_id="agentic_rag",
    name="Agentic RAG Pipeline",
    description=(
        "Multi-step RAG with query decomposition, hybrid+graph retrieval, reranking, "
        "and agent-driven synthesis with tool access for complex multi-hop questions."
    ),
    steps=[
        StepDefinition(
            id="decompose",
            type=StepType.LLM_CALL,
            name="Decompose Query",
            config={
                "prompt_template": "Break this question into sub-questions if complex, otherwise return as-is: {input.query}",
                "max_tokens": 256,
            },
        ),
        StepDefinition(
            id="retrieve",
            type=StepType.RETRIEVAL,
            name="Hybrid + Graph Retrieval",
            config={"knowledge_base_id": "{input.knowledge_base_id}", "query_template": "{input.query}", "top_k": 15},
            depends_on=["decompose"],
        ),
        StepDefinition(
            id="agent_synthesis",
            type=StepType.AGENT_RUN,
            name="Agent Synthesis with Tools",
            config={"agent_id": "{input.agent_id}", "task_template": "Answer using retrieved context: {steps.retrieve.results}\n\nQuestion: {input.query}"},
            depends_on=["retrieve"],
            timeout_seconds=180.0,
        ),
        StepDefinition(
            id="verify",
            type=StepType.CONDITION,
            name="Verify Quality",
            condition="steps.agent_synthesis.status == completed",
            depends_on=["agent_synthesis"],
        ),
    ],
    input_schema={"type": "object", "properties": {"query": {"type": "string"}, "knowledge_base_id": {"type": "string"}, "agent_id": {"type": "string"}}, "required": ["query", "knowledge_base_id", "agent_id"]},
    metadata={"category": "agentic_rag", "estimated_duration_seconds": 30},
)
