# analytics/dashboards.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from analytics.costs import get_cost_breakdown, get_cost_series
from analytics.metrics import TimeRange, generate_empty_time_series
from analytics.usage import (
    get_activity_feed,
    get_agent_run_volume,
    get_api_call_volume,
    get_error_rate_series,
    get_latency_distribution,
    get_latency_series,
    get_model_usage_breakdown,
    get_query_volume,
    get_token_usage_series,
    get_usage_summary,
)
from monitoring.logging import get_logger

logger = get_logger("neuralcore.analytics.dashboards")


async def get_main_dashboard(
    db: Any,
    range_str: str,
    organization_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    import asyncio

    summary, query_vol, token_vol, agent_vol, error_rate, latency_p95, cost_breakdown, activity = await asyncio.gather(
        get_usage_summary(db, range_str, organization_id, project_id),
        get_query_volume(db, range_str, organization_id, project_id),
        get_token_usage_series(db, range_str, organization_id),
        get_agent_run_volume(db, range_str, organization_id),
        get_error_rate_series(db, range_str, organization_id),
        get_latency_series(db, range_str, organization_id, percentile="p95"),
        get_cost_breakdown(db, range_str, organization_id, project_id),
        get_activity_feed(db, organization_id, limit=10),
    )

    return {
        "range": range_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "charts": {
            "query_volume": query_vol.to_dict(),
            "token_usage": token_vol.to_dict(),
            "agent_runs": agent_vol.to_dict(),
            "error_rate": error_rate.to_dict(),
            "latency_p95": latency_p95.to_dict(),
        },
        "costs": cost_breakdown,
        "activity_feed": activity,
        "highlights": _compute_highlights(summary, cost_breakdown),
    }


def _compute_highlights(summary: dict[str, Any], costs: dict[str, Any]) -> list[dict[str, Any]]:
    highlights: list[dict[str, Any]] = [
        {"label": "Total Queries", "value": summary.get("total_queries", 0), "unit": "queries", "trend": "neutral"},
        {"label": "Avg Latency", "value": summary.get("avg_query_latency_ms", 0.0), "unit": "ms", "trend": "neutral"},
        {"label": "Error Rate", "value": summary.get("error_rate", 0.0), "unit": "%", "trend": "neutral"},
        {"label": "Total Cost", "value": costs.get("total_usd", 0.0), "unit": "USD", "trend": "neutral"},
        {"label": "Tokens Used", "value": summary.get("total_tokens", 0), "unit": "tokens", "trend": "neutral"},
        {"label": "Agent Runs", "value": summary.get("total_agent_runs", 0), "unit": "runs", "trend": "neutral"},
    ]
    return highlights


async def get_project_dashboard(
    db: Any,
    project_id: uuid.UUID,
    range_str: str,
    organization_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    summary = await get_usage_summary(db, range_str, organization_id, project_id)
    query_vol = await get_query_volume(db, range_str, organization_id, project_id)

    return {
        "project_id": str(project_id),
        "range": range_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "charts": {
            "query_volume": query_vol.to_dict(),
        },
        "knowledge_base_stats": [],
        "agent_stats": [],
        "top_queries": [],
    }


async def get_retrieval_quality_dashboard(
    db: Any,
    knowledge_base_id: uuid.UUID,
    range_str: str,
) -> dict[str, Any]:
    return {
        "knowledge_base_id": str(knowledge_base_id),
        "range": range_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "avg_relevance_score": 0.0,
        "avg_reranking_improvement": 0.0,
        "cache_hit_rate": 0.0,
        "top_queries": [],
        "worst_performing_queries": [],
        "latency_distribution": await get_latency_distribution(db, range_str),
        "model_usage": await get_model_usage_breakdown(db, range_str),
    }


async def get_model_usage_dashboard(
    db: Any,
    range_str: str,
    organization_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    model_usage = await get_model_usage_breakdown(db, range_str, organization_id)
    cost_series = await get_cost_series(db, range_str, organization_id)
    token_vol = await get_token_usage_series(db, range_str, organization_id)

    return {
        "range": range_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model_breakdown": model_usage,
        "cost_series": cost_series,
        "token_usage": token_vol.to_dict(),
        "total_llm_calls": 0,
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "avg_tokens_per_call": 0.0,
    }
