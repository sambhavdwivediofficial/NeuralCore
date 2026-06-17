# prompt_engine/template_engine.py
from __future__ import annotations

import re
import string
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TemplateError(ValueError):
    pass


class TemplateFormat(str, Enum):
    FSTRING = "fstring"
    JINJA2 = "jinja2"
    MUSTACHE = "mustache"


_VARIABLE_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_.]*)\}")
_MUSTACHE_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_.]*)\}\}")


@dataclass(frozen=True)
class PromptTemplate:
    template: str
    input_variables: list[str] = field(default_factory=list)
    format: TemplateFormat = TemplateFormat.FSTRING
    description: str = ""

    def __post_init__(self) -> None:
        if not self.input_variables:
            detected = _detect_variables(self.template, self.format)
            object.__setattr__(self, "input_variables", detected)

    def render(self, **kwargs: Any) -> str:
        missing = set(self.input_variables) - set(kwargs)
        if missing:
            raise TemplateError(f"Missing template variables: {sorted(missing)}")

        if self.format == TemplateFormat.FSTRING:
            try:
                return self.template.format_map(_SafeFormatMap(kwargs))
            except (KeyError, ValueError) as exc:
                raise TemplateError(f"Template render error: {exc}") from exc

        if self.format == TemplateFormat.JINJA2:
            try:
                from jinja2 import Environment, StrictUndefined
                env = Environment(undefined=StrictUndefined)
                tmpl = env.from_string(self.template)
                return tmpl.render(**kwargs)
            except Exception as exc:
                raise TemplateError(f"Jinja2 render error: {exc}") from exc

        if self.format == TemplateFormat.MUSTACHE:
            result = self.template
            for key, value in kwargs.items():
                result = result.replace("{{" + key + "}}", str(value))
            return result

        raise TemplateError(f"Unknown format: {self.format}")

    def partial(self, **kwargs: Any) -> "PromptTemplate":
        rendered_partial = self.template
        remaining: list[str] = []
        for var in self.input_variables:
            if var in kwargs:
                rendered_partial = rendered_partial.replace(f"{{{var}}}", str(kwargs[var]))
            else:
                remaining.append(var)
        return PromptTemplate(
            template=rendered_partial,
            input_variables=remaining,
            format=self.format,
            description=self.description,
        )


class _SafeFormatMap(dict):  # type: ignore[type-arg]
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _detect_variables(template: str, fmt: TemplateFormat) -> list[str]:
    if fmt == TemplateFormat.MUSTACHE:
        return list(dict.fromkeys(_MUSTACHE_PATTERN.findall(template)))
    return list(dict.fromkeys(_VARIABLE_PATTERN.findall(template)))


class TemplateRegistry:
    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}

    def register(self, name: str, template: PromptTemplate) -> None:
        self._templates[name] = template

    def get(self, name: str) -> PromptTemplate:
        if name not in self._templates:
            raise KeyError(f"Template '{name}' not found in registry")
        return self._templates[name]

    def render(self, name: str, **kwargs: Any) -> str:
        return self.get(name).render(**kwargs)

    def list_templates(self) -> list[str]:
        return list(self._templates)


_BUILT_IN_TEMPLATES: dict[str, PromptTemplate] = {
    "rag_qa": PromptTemplate(
        template=(
            "You are a helpful assistant. Use the context below to answer the question accurately.\n"
            "If the answer is not in the context, say you don't know.\n\n"
            "Context:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer:"
        ),
        description="Standard RAG question-answering template",
    ),
    "rag_with_history": PromptTemplate(
        template=(
            "You are a helpful assistant with access to a knowledge base.\n\n"
            "Conversation History:\n{history}\n\n"
            "Retrieved Context:\n{context}\n\n"
            "Current Question: {question}\n\n"
            "Answer:"
        ),
        description="RAG template with conversation history",
    ),
    "summarize": PromptTemplate(
        template=(
            "Summarize the following text concisely in {max_sentences} sentences.\n\n"
            "Text:\n{text}\n\n"
            "Summary:"
        ),
        description="Text summarization template",
    ),
    "agent_system": PromptTemplate(
        template=(
            "You are {agent_name}, an AI agent specialized in {specialization}.\n\n"
            "Capabilities: {capabilities}\n\n"
            "Available Tools: {tools}\n\n"
            "Instructions:\n{instructions}\n\n"
            "Always reason step-by-step before taking actions.\n"
            "Use tools when needed. Be concise and accurate."
        ),
        description="Agent system prompt template",
    ),
    "tool_result": PromptTemplate(
        template=(
            "Tool: {tool_name}\n"
            "Input: {tool_input}\n"
            "Result: {tool_result}"
        ),
        description="Tool call result formatting template",
    ),
    "memory_summary": PromptTemplate(
        template=(
            "Summarize the following conversation into key facts and decisions "
            "that should be remembered for future interactions.\n\n"
            "Conversation:\n{conversation}\n\n"
            "Key facts to remember:"
        ),
        description="Memory summarization template",
    ),
    "graph_rag_qa": PromptTemplate(
        template=(
            "You are an intelligent assistant with access to a structured knowledge graph.\n\n"
            "Knowledge Graph Context:\n{graph_context}\n\n"
            "Document Context:\n{doc_context}\n\n"
            "Question: {question}\n\n"
            "Answer using both the graph relationships and document context:"
        ),
        description="GraphRAG question-answering template",
    ),
    "hyde": PromptTemplate(
        template=(
            "Generate a hypothetical document passage that would perfectly answer the following query.\n"
            "Write only the passage, no explanations or preamble.\n\n"
            "Query: {query}\n\n"
            "Hypothetical passage:"
        ),
        description="HyDE (Hypothetical Document Embedding) template",
    ),
    "step_back": PromptTemplate(
        template=(
            "Given the specific query below, generate a more general version that captures the broader topic.\n"
            "Output only the rewritten question.\n\n"
            "Original query: {query}\n\n"
            "General question:"
        ),
        description="Step-back prompting template",
    ),
    "decompose": PromptTemplate(
        template=(
            "Break the following complex query into {n} simpler sub-questions.\n"
            "Output one sub-question per line, no numbering or bullets.\n\n"
            "Query: {query}\n\n"
            "Sub-questions:"
        ),
        description="Query decomposition template",
    ),
}

default_registry = TemplateRegistry()
for _name, _tmpl in _BUILT_IN_TEMPLATES.items():
    default_registry.register(_name, _tmpl)
    