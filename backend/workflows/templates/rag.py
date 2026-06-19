# workflows/templates/rag.py
from __future__ import annotations

from workflows.workflow_registry import StepDefinition, StepType, WorkflowTemplate

RAG_TEMPLATE = WorkflowTemplate(
    template_id="rag",
    name="Standard RAG Pipeline",
    description="Retrieve relevant context from a knowledge base and generate an answer using an LLM.",
    steps=[
        StepDefinition(
            id="retrieve",
            type=StepType.RETRIEVAL,
            name="Retrieve Context",
            config={"knowledge_base_id": "{input.knowledge_base_id}", "query_template": "{input.query}", "top_k": 10},
        ),
        StepDefinition(
            id="generate",
            type=StepType.LLM_CALL,
            name="Generate Answer",
            config={
                "prompt_template": (
                    "Use the context below to answer the question.\n\n"
                    "Context: {steps.retrieve.results}\n\n"
                    "Question: {input.query}\n\nAnswer:"
                ),
                "max_tokens": 1024,
            },
            depends_on=["retrieve"],
        ),
    ],
    input_schema={"type": "object", "properties": {"query": {"type": "string"}, "knowledge_base_id": {"type": "string"}}, "required": ["query", "knowledge_base_id"]},
    metadata={"category": "rag", "estimated_duration_seconds": 5},
)
