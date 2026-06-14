# monitoring/metrics.py
from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from prometheus_client import Counter, Gauge, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "neuralcore_http_requests_total",
    "Total HTTP requests processed",
    ["method", "path", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "neuralcore_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

LLM_CALL_DURATION_SECONDS = Histogram(
    "neuralcore_llm_call_duration_seconds",
    "LLM provider call latency in seconds",
    ["provider", "model"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)

LLM_TOKENS_TOTAL = Counter(
    "neuralcore_llm_tokens_total",
    "Total LLM tokens processed",
    ["provider", "model", "token_type"],
)

EMBEDDING_CALL_DURATION_SECONDS = Histogram(
    "neuralcore_embedding_call_duration_seconds",
    "Embedding provider call latency in seconds",
    ["provider", "model"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

VECTOR_SEARCH_DURATION_SECONDS = Histogram(
    "neuralcore_vector_search_duration_seconds",
    "Vector store search latency in seconds",
    ["backend"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
)

RERANK_DURATION_SECONDS = Histogram(
    "neuralcore_rerank_duration_seconds",
    "Reranking operation latency in seconds",
    ["provider"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)

AGENT_TASK_DURATION_SECONDS = Histogram(
    "neuralcore_agent_task_duration_seconds",
    "Agent task execution latency in seconds",
    ["agent_type"],
    buckets=(0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600),
)

AGENT_TASK_TOTAL = Counter(
    "neuralcore_agent_task_total",
    "Total agent tasks executed",
    ["agent_type", "status"],
)

INGESTION_DOCUMENTS_TOTAL = Counter(
    "neuralcore_ingestion_documents_total",
    "Total documents ingested",
    ["source_type", "status"],
)

QUEUE_TASK_DURATION_SECONDS = Histogram(
    "neuralcore_queue_task_duration_seconds",
    "Celery task execution latency in seconds",
    ["task_name"],
    buckets=(0.1, 0.5, 1, 5, 10, 30, 60, 300, 900, 1800),
)

CACHE_OPERATIONS_TOTAL = Counter(
    "neuralcore_cache_operations_total",
    "Total cache operations",
    ["cache_type", "result"],
)

ACTIVE_AGENTS = Gauge(
    "neuralcore_active_agents",
    "Number of currently running agents",
    ["organization_id"],
)

DB_POOL_IN_USE = Gauge(
    "neuralcore_db_pool_connections_in_use",
    "Number of database connections currently checked out",
)

QUOTA_USAGE_RATIO = Gauge(
    "neuralcore_quota_usage_ratio",
    "Current usage as a ratio of the quota limit",
    ["organization_id", "quota_type", "period"],
)


@contextmanager
def track_duration(histogram: Histogram, **labels: str) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        histogram.labels(**labels).observe(time.perf_counter() - start)


def record_cache_result(cache_type: str, hit: bool) -> None:
    CACHE_OPERATIONS_TOTAL.labels(cache_type=cache_type, result="hit" if hit else "miss").inc()


def record_llm_usage(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> None:
    LLM_TOKENS_TOTAL.labels(provider=provider, model=model, token_type="prompt").inc(prompt_tokens)
    LLM_TOKENS_TOTAL.labels(provider=provider, model=model, token_type="completion").inc(completion_tokens)