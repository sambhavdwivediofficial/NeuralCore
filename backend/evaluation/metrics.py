# evaluation/metrics.py
from __future__ import annotations

import math
from typing import Any

try:
    import neuralcore_engine
except ImportError:
    neuralcore_engine = None


def _engine_ndcg(results: list[dict], k: int) -> float | None:
    if neuralcore_engine is None:
        return None
    func = getattr(neuralcore_engine, "py_compute_ndcg", None)
    if func is None:
        return None
    try:
        scores = [r.get("score", 0.0) for r in results]
        relevance = [float(r.get("relevant", r.get("relevance_score", 0.0))) for r in results]
        return float(func(scores, relevance, k))
    except Exception:
        return None


def _engine_mrr(results: list[dict]) -> float | None:
    if neuralcore_engine is None:
        return None
    func = getattr(neuralcore_engine, "py_compute_mrr", None)
    if func is None:
        return None
    try:
        relevance = [float(r.get("relevant", r.get("relevance_score", 0.0))) for r in results]
        return float(func(relevance))
    except Exception:
        return None


def compute_ndcg(results: list[dict[str, Any]], k: int = 10) -> float:
    engine_result = _engine_ndcg(results, k)
    if engine_result is not None:
        return engine_result

    relevance_scores = [float(r.get("relevant", r.get("relevance_score", 0.0))) for r in results[:k]]
    if not relevance_scores or sum(relevance_scores) == 0:
        return 0.0

    dcg = sum(rel / math.log2(rank + 2) for rank, rel in enumerate(relevance_scores))
    ideal = sorted(relevance_scores, reverse=True)
    idcg = sum(rel / math.log2(rank + 2) for rank, rel in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def compute_mrr(results: list[dict[str, Any]]) -> float:
    engine_result = _engine_mrr(results)
    if engine_result is not None:
        return engine_result

    for rank, result in enumerate(results, start=1):
        if float(result.get("relevant", result.get("relevance_score", 0.0))) > 0:
            return 1.0 / rank
    return 0.0


def compute_precision_at_k(results: list[dict[str, Any]], k: int = 10, threshold: float = 0.5) -> float:
    top_k = results[:k]
    if not top_k:
        return 0.0
    relevant = sum(1 for r in top_k if float(r.get("relevant", r.get("relevance_score", 0.0))) >= threshold)
    return relevant / len(top_k)


def compute_recall_at_k(results: list[dict[str, Any]], total_relevant: int, k: int = 10, threshold: float = 0.5) -> float:
    if total_relevant == 0:
        return 0.0
    top_k = results[:k]
    relevant = sum(1 for r in top_k if float(r.get("relevant", r.get("relevance_score", 0.0))) >= threshold)
    return relevant / total_relevant


def compute_f1_at_k(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


def compute_hit_rate(results: list[dict[str, Any]], k: int = 10, threshold: float = 0.5) -> float:
    return 1.0 if any(float(r.get("relevant", 0.0)) >= threshold for r in results[:k]) else 0.0


def compute_average_precision(results: list[dict[str, Any]], threshold: float = 0.5) -> float:
    relevant_count = 0
    precision_sum = 0.0
    for rank, result in enumerate(results, start=1):
        if float(result.get("relevant", result.get("relevance_score", 0.0))) >= threshold:
            relevant_count += 1
            precision_sum += relevant_count / rank
    total_relevant = sum(1 for r in results if float(r.get("relevant", r.get("relevance_score", 0.0))) >= threshold)
    return precision_sum / total_relevant if total_relevant > 0 else 0.0


def compute_mean_average_precision(queries_results: list[list[dict[str, Any]]], threshold: float = 0.5) -> float:
    if not queries_results:
        return 0.0
    return sum(compute_average_precision(results, threshold) for results in queries_results) / len(queries_results)


def compute_context_relevance(context: str, query: str) -> float:
    from chunking.base_chunker import count_tokens
    query_terms = set(query.lower().split())
    context_terms = set(context.lower().split())
    if not query_terms or not context_terms:
        return 0.0
    overlap = len(query_terms & context_terms)
    return overlap / len(query_terms)


def compute_faithfulness(answer: str, context: str) -> float:
    answer_sentences = [s.strip() for s in answer.split(".") if s.strip()]
    if not answer_sentences:
        return 0.0
    faithful_count = 0
    for sentence in answer_sentences:
        sentence_terms = set(sentence.lower().split())
        context_terms = set(context.lower().split())
        if sentence_terms and len(sentence_terms & context_terms) / len(sentence_terms) > 0.4:
            faithful_count += 1
    return faithful_count / len(answer_sentences)


def compute_answer_relevance(answer: str, query: str) -> float:
    query_terms = set(query.lower().split())
    answer_terms = set(answer.lower().split())
    if not query_terms or not answer_terms:
        return 0.0
    return len(query_terms & answer_terms) / len(query_terms)
