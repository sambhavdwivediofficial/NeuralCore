# queue/tasks/reranking.py
from __future__ import annotations

import logging
import uuid
from typing import Any

from queue.celery import celery_app, run_async
from settings import get_settings

logger = logging.getLogger(__name__)


@celery_app.task(
    name="queue.tasks.reranking.rerank_documents",
    bind=True,
    max_retries=3,
    default_retry_delay=20,
)
def rerank_documents(
    self,
    query: str,
    documents: list[dict[str, Any]],
    provider: str | None = None,
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    return run_async(_rerank_documents(query, documents, provider, top_n))


async def _rerank_documents(
    query: str, documents: list[dict[str, Any]], provider: str | None, top_n: int | None
) -> list[dict[str, Any]]:
    settings = get_settings()
    reranking_config = settings.retrieval.reranking
    provider_name = provider or reranking_config.default_provider
    limit = top_n or reranking_config.top_n

    from reranking.hybrid_reranker import get_reranker

    reranker = get_reranker(provider_name, settings=settings)
    ranked = await reranker.rerank(query=query, documents=documents, top_n=limit)

    logger.info(
        "reranked documents",
        extra={"provider": provider_name, "input": len(documents), "output": len(ranked)},
    )
    return ranked


@celery_app.task(
    name="queue.tasks.reranking.evaluate_retrieval_quality",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    acks_late=True,
)
def evaluate_retrieval_quality(self, knowledge_base_id: str, dataset_id: str) -> dict[str, Any]:
    return run_async(_evaluate_retrieval_quality(uuid.UUID(knowledge_base_id), uuid.UUID(dataset_id)))


async def _evaluate_retrieval_quality(knowledge_base_id: uuid.UUID, dataset_id: uuid.UUID) -> dict[str, Any]:
    settings = get_settings()

    from evaluation.retrieval_eval import run_retrieval_evaluation

    report = await run_retrieval_evaluation(
        knowledge_base_id=knowledge_base_id, dataset_id=dataset_id, settings=settings
    )

    logger.info(
        "evaluated retrieval quality",
        extra={
            "knowledge_base_id": str(knowledge_base_id),
            "dataset_id": str(dataset_id),
            "ndcg": report.get("ndcg"),
        },
    )
    return report