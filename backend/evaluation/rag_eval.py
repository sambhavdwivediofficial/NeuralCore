# evaluation/rag_eval.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from evaluation.metrics import compute_answer_relevance, compute_context_relevance, compute_faithfulness
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.evaluation.rag")


@dataclass(slots=True)
class RAGEvalSample:
    query: str
    ground_truth_answer: str
    knowledge_base_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RAGEvalResult:
    query: str
    generated_answer: str
    context_relevance: float
    faithfulness: float
    answer_relevance: float
    context_recall: float
    latency_ms: float

    @property
    def composite_score(self) -> float:
        return (self.context_relevance + self.faithfulness + self.answer_relevance + self.context_recall) / 4.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "generated_answer": self.generated_answer[:200],
            "context_relevance": round(self.context_relevance, 4),
            "faithfulness": round(self.faithfulness, 4),
            "answer_relevance": round(self.answer_relevance, 4),
            "context_recall": round(self.context_recall, 4),
            "composite_score": round(self.composite_score, 4),
            "latency_ms": round(self.latency_ms, 2),
        }


async def evaluate_rag_sample(
    sample: RAGEvalSample,
    settings: Settings,
) -> RAGEvalResult:
    import time
    from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
    from model_gateway.provider_factory import get_model_gateway
    from prompt_engine.template_engine import default_registry
    from retrieval.retriever import Retriever

    retriever = Retriever(settings=settings)
    kb_id = uuid.UUID(sample.knowledge_base_id)

    start = time.perf_counter()
    results = await retriever.search(knowledge_base_id=kb_id, query=sample.query, top_k=5, use_hybrid=True, use_reranking=True)
    context = "\n\n".join(r.text or "" for r in results if r.text)

    gateway = get_model_gateway(settings)
    user_content = default_registry.render("rag_qa", context=context, question=sample.query)
    response = await gateway.chat_completion(
        CompletionRequest(messages=[ChatMessage(role=ChatRole.USER, content=user_content)], max_tokens=512, temperature=0.1)
    )
    latency_ms = (time.perf_counter() - start) * 1000
    answer = (response.content or "").strip()

    return RAGEvalResult(
        query=sample.query,
        generated_answer=answer,
        context_relevance=compute_context_relevance(context, sample.query),
        faithfulness=compute_faithfulness(answer, context),
        answer_relevance=compute_answer_relevance(answer, sample.query),
        context_recall=compute_context_relevance(context, sample.ground_truth_answer),
        latency_ms=latency_ms,
    )


async def run_rag_evaluation(
    samples: list[RAGEvalSample],
    settings: Settings,
    concurrency: int = 3,
) -> dict[str, Any]:
    if not samples:
        return {"total_samples": 0, "avg_composite_score": 0.0}

    semaphore = asyncio.Semaphore(concurrency)

    async def _eval_one(sample: RAGEvalSample) -> RAGEvalResult | None:
        async with semaphore:
            try:
                return await evaluate_rag_sample(sample, settings)
            except Exception as exc:
                logger.warning("rag_eval_sample_failed", query=sample.query[:80], error=str(exc))
                return None

    results_raw = await asyncio.gather(*[_eval_one(s) for s in samples])
    valid = [r for r in results_raw if r is not None]

    if not valid:
        return {"total_samples": len(samples), "valid_samples": 0, "avg_composite_score": 0.0}

    return {
        "total_samples": len(samples),
        "valid_samples": len(valid),
        "avg_composite_score": sum(r.composite_score for r in valid) / len(valid),
        "avg_context_relevance": sum(r.context_relevance for r in valid) / len(valid),
        "avg_faithfulness": sum(r.faithfulness for r in valid) / len(valid),
        "avg_answer_relevance": sum(r.answer_relevance for r in valid) / len(valid),
        "avg_latency_ms": sum(r.latency_ms for r in valid) / len(valid),
        "per_sample_results": [r.to_dict() for r in valid],
    }
