# evaluation/retrieval_eval.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from evaluation.metrics import (
    compute_hit_rate,
    compute_mean_average_precision,
    compute_mrr,
    compute_ndcg,
    compute_precision_at_k,
    compute_recall_at_k,
)
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.evaluation.retrieval")


@dataclass(slots=True)
class RetrievalEvalQuery:
    query: str
    relevant_doc_ids: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalEvalResult:
    query: str
    ndcg_at_5: float
    ndcg_at_10: float
    mrr: float
    precision_at_5: float
    precision_at_10: float
    recall_at_10: float
    hit_rate_at_5: float
    hit_rate_at_10: float
    latency_ms: float
    num_results: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "ndcg_at_5": round(self.ndcg_at_5, 4),
            "ndcg_at_10": round(self.ndcg_at_10, 4),
            "mrr": round(self.mrr, 4),
            "precision_at_5": round(self.precision_at_5, 4),
            "precision_at_10": round(self.precision_at_10, 4),
            "recall_at_10": round(self.recall_at_10, 4),
            "hit_rate_at_5": round(self.hit_rate_at_5, 4),
            "hit_rate_at_10": round(self.hit_rate_at_10, 4),
            "latency_ms": round(self.latency_ms, 2),
            "num_results": self.num_results,
            "metadata": self.metadata,
        }


async def evaluate_single_query(
    query: RetrievalEvalQuery,
    knowledge_base_id: uuid.UUID,
    settings: Settings,
    top_k: int = 10,
) -> RetrievalEvalResult:
    import time
    from retrieval.retriever import Retriever

    retriever = Retriever(settings=settings)
    start = time.perf_counter()
    results = await retriever.search(
        knowledge_base_id=knowledge_base_id,
        query=query.query,
        top_k=top_k,
        use_hybrid=True,
        use_reranking=True,
    )
    latency_ms = (time.perf_counter() - start) * 1000

    relevant_ids = set(query.relevant_doc_ids)
    enriched_results = [
        {
            "id": r.id,
            "score": r.score,
            "relevant": 1.0 if r.id in relevant_ids or r.metadata.get("source_id") in relevant_ids else 0.0,
        }
        for r in results
    ]
    total_relevant = len(relevant_ids)

    return RetrievalEvalResult(
        query=query.query,
        ndcg_at_5=compute_ndcg(enriched_results, k=5),
        ndcg_at_10=compute_ndcg(enriched_results, k=10),
        mrr=compute_mrr(enriched_results),
        precision_at_5=compute_precision_at_k(enriched_results, k=5),
        precision_at_10=compute_precision_at_k(enriched_results, k=10),
        recall_at_10=compute_recall_at_k(enriched_results, total_relevant, k=10),
        hit_rate_at_5=compute_hit_rate(enriched_results, k=5),
        hit_rate_at_10=compute_hit_rate(enriched_results, k=10),
        latency_ms=latency_ms,
        num_results=len(results),
    )


async def run_retrieval_evaluation(
    knowledge_base_id: uuid.UUID,
    dataset_id: uuid.UUID,
    settings: Settings,
    top_k: int = 10,
    concurrency: int = 4,
) -> dict[str, Any]:
    eval_queries: list[RetrievalEvalQuery] = [
        RetrievalEvalQuery(query="test query", relevant_doc_ids=[]),
    ]

    semaphore = asyncio.Semaphore(concurrency)

    async def _evaluate_one(query: RetrievalEvalQuery) -> RetrievalEvalResult:
        async with semaphore:
            return await evaluate_single_query(query, knowledge_base_id, settings, top_k)

    results = await asyncio.gather(*[_evaluate_one(q) for q in eval_queries], return_exceptions=True)
    valid_results = [r for r in results if isinstance(r, RetrievalEvalResult)]

    if not valid_results:
        return {"knowledge_base_id": str(knowledge_base_id), "dataset_id": str(dataset_id), "total_queries": 0, "error": "No valid results"}

    return {
        "knowledge_base_id": str(knowledge_base_id),
        "dataset_id": str(dataset_id),
        "total_queries": len(valid_results),
        "avg_ndcg_at_5": sum(r.ndcg_at_5 for r in valid_results) / len(valid_results),
        "avg_ndcg_at_10": sum(r.ndcg_at_10 for r in valid_results) / len(valid_results),
        "avg_mrr": sum(r.mrr for r in valid_results) / len(valid_results),
        "avg_precision_at_10": sum(r.precision_at_10 for r in valid_results) / len(valid_results),
        "avg_recall_at_10": sum(r.recall_at_10 for r in valid_results) / len(valid_results),
        "avg_hit_rate_at_10": sum(r.hit_rate_at_10 for r in valid_results) / len(valid_results),
        "avg_latency_ms": sum(r.latency_ms for r in valid_results) / len(valid_results),
        "per_query_results": [r.to_dict() for r in valid_results],
    }
