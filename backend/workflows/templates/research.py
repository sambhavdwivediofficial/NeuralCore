# workflows/templates/research.py
from __future__ import annotations

from workflows.workflow_registry import StepDefinition, StepType, WorkflowTemplate

RESEARCH_TEMPLATE = WorkflowTemplate(
    template_id="research",
    name="Multi-Source Research Pipeline",
    description="Search multiple knowledge bases and the web in parallel, then synthesize a comprehensive research summary.",
    steps=[
        StepDefinition(
            id="kb_search",
            type=StepType.RETRIEVAL,
            name="Knowledge Base Search",
            config={"knowledge_base_id": "{input.knowledge_base_id}", "query_template": "{input.topic}", "top_k": 10},
        ),
        StepDefinition(
            id="web_search",
            type=StepType.TOOL_CALL,
            name="Web Search",
            config={"tool_name": "web_search", "arguments_template": {"query": "{input.topic}", "max_results": 8}},
        ),
        StepDefinition(
            id="synthesize",
            type=StepType.LLM_CALL,
            name="Synthesize Research",
            config={
                "prompt_template": (
                    "Synthesize a comprehensive research summary on: {input.topic}\n\n"
                    "Knowledge base findings: {steps.kb_search.results}\n\n"
                    "Web search findings: {steps.web_search.results}\n\n"
                    "Provide a well-structured summary citing sources."
                ),
                "max_tokens": 2000,
            },
            depends_on=["kb_search", "web_search"],
        ),
    ],
    input_schema={"type": "object", "properties": {"topic": {"type": "string"}, "knowledge_base_id": {"type": "string"}}, "required": ["topic"]},
    metadata={"category": "research", "estimated_duration_seconds": 20},
)
