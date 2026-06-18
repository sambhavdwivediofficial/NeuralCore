# evaluation/reranking_eval.py
from __future__ import annotations

from typing import Any

from evaluation.metrics import compute_mrr, compute_ndcg, compute_precision_at_k
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.evaluation.reranking")


async def evaluate_reranking(
    query: str,
    before_results: list[dict[str, Any]],
    after_results: list[dict[str, Any]],
    relevant_ids: list[str],
    k: int = 10,
) -> dict[str, Any]:
    relevant_set = set(relevant_ids)

    def _enrich(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {**r, "relevant": 1.0 if r.get("id") in relevant_set else 0.0}
            for r in results
        ]

    before_enriched = _enrich(before_results)
    after_enriched = _enrich(after_results)

    before_ndcg = compute_ndcg(before_enriched, k=k)
    after_ndcg = compute_ndcg(after_enriched, k=k)
    before_mrr = compute_mrr(before_enriched)
    after_mrr = compute_mrr(after_enriched)
    before_p_at_k = compute_precision_at_k(before_enriched, k=k)
    after_p_at_k = compute_precision_at_k(after_enriched, k=k)

    return {
        "query": query,
        "k": k,
        "before": {
            "ndcg": round(before_ndcg, 4),
            "mrr": round(before_mrr, 4),
            f"precision_at_{k}": round(before_p_at_k, 4),
        },
        "after": {
            "ndcg": round(after_ndcg, 4),
            "mrr": round(after_mrr, 4),
            f"precision_at_{k}": round(after_p_at_k, 4),
        },
        "improvement": {
            "ndcg_delta": round(after_ndcg - before_ndcg, 4),
            "mrr_delta": round(after_mrr - before_mrr, 4),
            f"precision_at_{k}_delta": round(after_p_at_k - before_p_at_k, 4),
        },
        "reranking_improved": after_ndcg > before_ndcg,
    }
