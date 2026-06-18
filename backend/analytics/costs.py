# analytics/costs.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from analytics.metrics import TimeRange, generate_empty_time_series, range_to_timedelta
from monitoring.logging import get_logger
from prompt_engine.token_optimizer import estimate_cost

logger = get_logger("neuralcore.analytics.costs")

_LLM_PROVIDERS_DISPLAY = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "deepseek": "DeepSeek",
    "gemini": "Google Gemini",
    "mistral": "Mistral",
    "local": "Local (Free)",
    "ollama": "Ollama (Free)",
}

_EMBEDDING_COST_PER_1K_TOKENS: dict[str, float] = {
    "openai": 0.00002,
    "jina": 0.00002,
    "bge": 0.0,
    "e5": 0.0,
    "nomic": 0.0,
    "sentence_transformers": 0.0,
    "custom": 0.0,
}


def calculate_llm_cost(
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> float:
    return estimate_cost(prompt_tokens, completion_tokens, provider, model)


def calculate_embedding_cost(provider: str, token_count: int) -> float:
    cost_per_1k = _EMBEDDING_COST_PER_1K_TOKENS.get(provider, 0.00002)
    return (token_count / 1000.0) * cost_per_1k


async def get_cost_breakdown(
    db: Any,
    range_str: str,
    organization_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    return {
        "range": range_str,
        "organization_id": str(organization_id) if organization_id else None,
        "project_id": str(project_id) if project_id else None,
        "total_usd": 0.0,
        "breakdown": {
            "llm": {"total_usd": 0.0, "by_provider": [], "by_model": []},
            "embeddings": {"total_usd": 0.0, "by_provider": []},
            "storage": {"total_usd": 0.0, "storage_gb": 0.0, "cost_per_gb": 0.023},
            "api_calls": {"total_usd": 0.0, "total_calls": 0},
        },
        "currency": "USD",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_cost_series(
    db: Any,
    range_str: str,
    organization_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    series = generate_empty_time_series(range_str, "Daily Cost", "USD")
    return {
        "range": range_str,
        "series": series.to_dict(),
        "projected_monthly_usd": 0.0,
        "budget_usd": None,
        "budget_utilization": None,
    }


async def get_top_cost_agents(
    db: Any,
    range_str: str,
    organization_id: uuid.UUID | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    return []


async def get_cost_per_query(
    db: Any,
    range_str: str,
    organization_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    return {
        "range": range_str,
        "avg_cost_per_query_usd": 0.0,
        "avg_cost_per_agent_run_usd": 0.0,
        "avg_cost_per_document_ingest_usd": 0.0,
        "cheapest_provider": "local",
        "most_expensive_provider": "anthropic",
    }
