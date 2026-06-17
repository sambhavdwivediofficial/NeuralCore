# prompt_engine/context_builder.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chunking.base_chunker import count_tokens
from monitoring.logging import get_logger

logger = get_logger("neuralcore.prompt_engine.context_builder")

_SECTION_SEPARATOR = "\n\n---\n\n"


@dataclass(slots=True)
class ContextSection:
    name: str
    content: str
    priority: int = 0
    token_count: int = 0

    def __post_init__(self) -> None:
        if self.token_count == 0:
            self.token_count = count_tokens(self.content)


@dataclass(slots=True)
class BuiltContext:
    sections: list[ContextSection] = field(default_factory=list)
    full_text: str = ""
    total_tokens: int = 0
    sections_included: list[str] = field(default_factory=list)
    sections_truncated: list[str] = field(default_factory=list)
    sections_omitted: list[str] = field(default_factory=list)


class ContextBuilder:
    def __init__(self, max_tokens: int = 4096) -> None:
        self.max_tokens = max_tokens
        self._sections: list[ContextSection] = []

    def add_section(self, name: str, content: str, priority: int = 0) -> "ContextBuilder":
        if content and content.strip():
            section = ContextSection(name=name, content=content.strip(), priority=priority)
            self._sections.append(section)
        return self

    def add_retrieval_results(
        self,
        results: list[dict[str, Any]],
        max_chunks: int = 10,
        header: str = "Retrieved Context",
        priority: int = 10,
    ) -> "ContextBuilder":
        if not results:
            return self
        lines: list[str] = []
        for index, result in enumerate(results[:max_chunks], start=1):
            text = result.get("text") or result.get("content") or result.get("metadata", {}).get("text", "")
            source = result.get("metadata", {}).get("source_type", "")
            score = result.get("score", 0.0)
            if not text:
                continue
            source_label = f" [{source}]" if source else ""
            score_label = f" (relevance: {score:.2f})" if score else ""
            lines.append(f"[{index}]{source_label}{score_label}\n{text.strip()}")
        if lines:
            self.add_section(header, "\n\n".join(lines), priority=priority)
        return self

    def add_graph_context(
        self, graph_context: str, priority: int = 9
    ) -> "ContextBuilder":
        if graph_context.strip():
            self.add_section("Knowledge Graph", graph_context.strip(), priority=priority)
        return self

    def add_memory_context(
        self, memory_text: str, priority: int = 8
    ) -> "ContextBuilder":
        if memory_text.strip():
            self.add_section("Memory Context", memory_text.strip(), priority=priority)
        return self

    def add_conversation_history(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1024,
        priority: int = 7,
    ) -> "ContextBuilder":
        if not messages:
            return self
        history_lines: list[str] = []
        used = 0
        for msg in reversed(messages):
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            line = f"{role}: {content}"
            tokens = count_tokens(line)
            if used + tokens > max_tokens:
                break
            history_lines.insert(0, line)
            used += tokens
        if history_lines:
            self.add_section("Conversation History", "\n".join(history_lines), priority=priority)
        return self

    def build(self) -> BuiltContext:
        sorted_sections = sorted(self._sections, key=lambda s: s.priority, reverse=True)
        included: list[ContextSection] = []
        truncated: list[str] = []
        omitted: list[str] = []
        budget_used = 0

        for section in sorted_sections:
            remaining = self.max_tokens - budget_used
            if remaining <= 0:
                omitted.append(section.name)
                continue

            if section.token_count <= remaining:
                included.append(section)
                budget_used += section.token_count
            else:
                if remaining < 50:
                    omitted.append(section.name)
                    continue
                from chunking.base_chunker import encode_tokens, decode_tokens
                tokens = encode_tokens(section.content)
                truncated_tokens = tokens[:remaining - 10]
                truncated_text = decode_tokens(truncated_tokens).strip() + "..."
                truncated_section = ContextSection(
                    name=section.name,
                    content=truncated_text,
                    priority=section.priority,
                )
                included.append(truncated_section)
                budget_used += truncated_section.token_count
                truncated.append(section.name)

        parts: list[str] = []
        for section in sorted(included, key=lambda s: s.priority, reverse=True):
            parts.append(f"### {section.name}\n{section.content}")

        full_text = _SECTION_SEPARATOR.join(parts)
        return BuiltContext(
            sections=included,
            full_text=full_text,
            total_tokens=budget_used,
            sections_included=[s.name for s in included],
            sections_truncated=truncated,
            sections_omitted=omitted,
        )
    