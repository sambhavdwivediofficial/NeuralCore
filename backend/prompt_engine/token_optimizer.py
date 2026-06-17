# prompt_engine/token_optimizer.py
from __future__ import annotations

import re
from typing import Any

from chunking.base_chunker import count_tokens
from monitoring.logging import get_logger

logger = get_logger("neuralcore.prompt_engine.token_optimizer")

_WHITESPACE_PATTERN = re.compile(r"\n{3,}")
_REPEATED_SPACES = re.compile(r" {2,}")


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    provider: str,
    model: str,
) -> float:
    _PRICING: dict[tuple[str, str], tuple[float, float]] = {
        ("openai", "gpt-4o"): (0.005, 0.015),
        ("openai", "gpt-4o-mini"): (0.00015, 0.0006),
        ("openai", "gpt-4-turbo"): (0.01, 0.03),
        ("anthropic", "claude-opus-4-6"): (0.015, 0.075),
        ("anthropic", "claude-sonnet-4-6"): (0.003, 0.015),
        ("deepseek", "deepseek-chat"): (0.00014, 0.00028),
        ("mistral", "mistral-large-latest"): (0.002, 0.006),
        ("local", "neuralcore-48b"): (0.0, 0.0),
        ("ollama", "llama3.1"): (0.0, 0.0),
    }
    input_price, output_price = _PRICING.get((provider.lower(), model.lower()), (0.001, 0.002))
    return (prompt_tokens * input_price + completion_tokens * output_price) / 1000.0


def check_fits_in_context(
    messages: list[dict[str, Any]],
    max_context_tokens: int,
    reserved_for_completion: int = 1024,
) -> tuple[bool, int]:
    total = sum(count_tokens(msg.get("content", "")) for msg in messages)
    available = max_context_tokens - reserved_for_completion
    return total <= available, total


def trim_messages_to_fit(
    messages: list[dict[str, Any]],
    max_tokens: int,
    keep_system: bool = True,
    reserved_for_completion: int = 1024,
) -> list[dict[str, Any]]:
    budget = max_tokens - reserved_for_completion
    system_messages = [m for m in messages if m.get("role") == "system"] if keep_system else []
    non_system = [m for m in messages if m.get("role") != "system"]

    system_tokens = sum(count_tokens(m.get("content", "")) for m in system_messages)
    remaining = budget - system_tokens

    selected_non_system: list[dict[str, Any]] = []
    used = 0
    for msg in reversed(non_system):
        tokens = count_tokens(msg.get("content", ""))
        if used + tokens > remaining:
            break
        selected_non_system.insert(0, msg)
        used += tokens

    return system_messages + selected_non_system


def normalize_prompt_whitespace(text: str) -> str:
    text = _WHITESPACE_PATTERN.sub("\n\n", text)
    text = _REPEATED_SPACES.sub(" ", text)
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def deduplicate_context_chunks(chunks: list[str], similarity_threshold: float = 0.9) -> list[str]:
    if not chunks:
        return []

    def _jaccard(a: str, b: str) -> float:
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        return len(words_a & words_b) / len(words_a | words_b)

    unique: list[str] = []
    for chunk in chunks:
        if not any(_jaccard(chunk, kept) >= similarity_threshold for kept in unique):
            unique.append(chunk)
    return unique


def format_numbered_context(chunks: list[str]) -> str:
    return "\n\n".join(f"[{i + 1}] {chunk.strip()}" for i, chunk in enumerate(chunks))
