# api/routes/reranking.py
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_app_settings
from settings import Settings

router = APIRouter()


class RerankRequest(BaseModel):
    query: str
    documents: list[dict[str, Any]]
    provider: Optional[str] = None
    top_n: Optional[int] = None


class RerankCompareRequest(BaseModel):
    knowledge_base_id: str
    query: str
    rerank_strategy: str


@router.get("/strategies")
async def list_strategies(user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> list[dict[str, Any]]:
    return [
        {"id": "bge", "name": "BGE Reranker", "description": "BAAI BGE cross-encoder model"},
        {"id": "cross_encoder", "name": "Cross Encoder", "description": "MS-MARCO cross-encoder"},
        {"id": "jina", "name": "Jina Reranker", "description": "Jina multilingual reranker API"},
        {"id": "hybrid", "name": "Hybrid", "description": "Automatic fallback chain"},
    ]


@router.post("/run")
async def run_reranking(
    body: RerankRequest,
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    from reranking.hybrid_reranker import get_reranker
    reranker = get_reranker(body.provider or settings.retrieval.reranking.default_provider, settings)
    try:
        ranked = await reranker.rerank(body.query, body.documents, top_n=body.top_n)
    except Exception as exc:
        ranked = body.documents
    return {"query": body.query, "results": ranked, "provider": body.provider}


@router.post("/compare")
async def compare_reranking(
    body: RerankCompareRequest,
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    import uuid as _uuid
    from retrieval.retriever import Retriever
    retriever = Retriever(settings=settings)
    try:
        before_results = await retriever.search(
            knowledge_base_id=_uuid.UUID(body.knowledge_base_id),
            query=body.query,
            use_reranking=False,
        )
        after_results = await retriever.search(
            knowledge_base_id=_uuid.UUID(body.knowledge_base_id),
            query=body.query,
            use_reranking=True,
        )
    except Exception:
        before_results = []
        after_results = []

    def _to_dict(r: Any) -> dict[str, Any]:
        return {"id": r.id, "score": r.score, "rank": r.rank, "text": r.text, "metadata": r.metadata}

    return {"query": body.query, "before": [_to_dict(r) for r in before_results], "after": [_to_dict(r) for r in after_results]}


@router.get("/metrics")
async def reranking_metrics(
    user: CurrentUser,
    knowledge_base_id: Optional[str] = Query(default=None),
    range: Optional[str] = Query(default="7d"),
) -> dict[str, Any]:
    return {"knowledge_base_id": knowledge_base_id, "range": range, "total_reranking_calls": 0, "avg_latency_ms": 0.0}
