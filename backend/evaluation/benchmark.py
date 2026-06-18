# evaluation/benchmark.py
from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.evaluation.benchmark")


@dataclass(slots=True)
class BenchmarkConfig:
    name: str
    concurrency: int = 4
    warmup_queries: int = 2
    total_queries: int = 20
    top_k: int = 10
    knowledge_base_id: str = ""
    sample_queries: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkResult:
    name: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_qps: float
    total_duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "total_queries": self.total_queries,
            "successful_queries": self.successful_queries,
            "failed_queries": self.failed_queries,
            "success_rate": self.successful_queries / max(self.total_queries, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p95_latency_ms": round(self.p95_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "min_latency_ms": round(self.min_latency_ms, 2),
            "max_latency_ms": round(self.max_latency_ms, 2),
            "throughput_qps": round(self.throughput_qps, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "metadata": self.metadata,
        }


async def run_retrieval_benchmark(
    config: BenchmarkConfig,
    settings: Settings,
) -> BenchmarkResult:
    from retrieval.retriever import Retriever

    retriever = Retriever(settings=settings)
    kb_id = uuid.UUID(config.knowledge_base_id) if config.knowledge_base_id else uuid.UUID(int=0)
    queries = config.sample_queries or ["test query"] * config.total_queries
    if len(queries) < config.total_queries:
        queries = (queries * ((config.total_queries // len(queries)) + 1))[:config.total_queries]

    if config.warmup_queries > 0:
        warmup = queries[:config.warmup_queries]
        for q in warmup:
            try:
                await retriever.search(knowledge_base_id=kb_id, query=q, top_k=config.top_k)
            except Exception:
                pass

    latencies: list[float] = []
    failures = 0
    semaphore = asyncio.Semaphore(config.concurrency)
    benchmark_start = time.perf_counter()

    async def _one_query(query: str) -> None:
        nonlocal failures
        async with semaphore:
            start = time.perf_counter()
            try:
                await retriever.search(knowledge_base_id=kb_id, query=query, top_k=config.top_k)
                latencies.append((time.perf_counter() - start) * 1000)
            except Exception:
                failures += 1
                latencies.append((time.perf_counter() - start) * 1000)

    await asyncio.gather(*[_one_query(q) for q in queries])
    total_duration_ms = (time.perf_counter() - benchmark_start) * 1000

    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)

    def _percentile(p: float) -> float:
        if not sorted_latencies:
            return 0.0
        idx = int(n * p / 100)
        return sorted_latencies[min(idx, n - 1)]

    return BenchmarkResult(
        name=config.name,
        total_queries=config.total_queries,
        successful_queries=config.total_queries - failures,
        failed_queries=failures,
        avg_latency_ms=sum(latencies) / max(len(latencies), 1),
        p50_latency_ms=_percentile(50),
        p95_latency_ms=_percentile(95),
        p99_latency_ms=_percentile(99),
        min_latency_ms=min(latencies) if latencies else 0.0,
        max_latency_ms=max(latencies) if latencies else 0.0,
        throughput_qps=(config.total_queries / total_duration_ms * 1000) if total_duration_ms > 0 else 0.0,
        total_duration_ms=total_duration_ms,
        metadata=config.metadata,
    )
