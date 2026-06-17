# api/routes/retrieval.py
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_app_settings, get_db
from settings import Settings

router = APIRouter()


class RetrievalQueryRequest(BaseModel):
    knowledge_base_id: str
    query: str
    strategy: str = "hybrid"
    top_k: int = 10
    use_reranking: bool = True
    use_graph: bool = False
    filters: dict[str, Any] = {}


class QueryRewriteRequest(BaseModel):
    query: str
    strategies: list[str] = ["hyde", "step_back", "expansion"]


class GraphTraversalRequest(BaseModel):
    knowledge_base_id: str
    entity: str
    max_hops: int = 2


@router.post("/query")
async def retrieval_query(
    body: RetrievalQueryRequest,
    user: CurrentUser,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    from retrieval.retriever import Retriever

    start = time.perf_counter()
    retriever = Retriever(settings=settings)
    try:
        results = await retriever.search(
            knowledge_base_id=uuid.UUID(body.knowledge_base_id),
            query=body.query,
            top_k=body.top_k,
            use_hybrid=body.strategy == "hybrid",
            use_reranking=body.use_reranking,
            use_graph=body.use_graph,
            filter_spec=body.filters,
        )
    except Exception:
        results = []

    latency_ms = (time.perf_counter() - start) * 1000
    trace_id = uuid.uuid4().hex

    return {
        "query": body.query,
        "knowledge_base_id": body.knowledge_base_id,
        "strategy": body.strategy,
        "trace_id": trace_id,
        "results": [
            {
                "id": r.id,
                "score": r.score,
                "rank": r.rank,
                "text": r.text,
                "metadata": r.metadata,
                "reranked": r.reranked,
                "sources": r.sources,
            }
            for r in results
        ],
        "total": len(results),
        "latency_ms": round(latency_ms, 2),
    }


@router.post("/query-rewrites")
async def query_rewrites(
    body: QueryRewriteRequest,
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    from retrieval.query_rewriter import rewrite_all_enabled
    rewrites = await rewrite_all_enabled(body.query, settings)
    return {"original": body.query, **rewrites}


@router.get("/traces")
async def list_traces(user: CurrentUser, pagination=Depends()) -> list[dict[str, Any]]:
    return []


@router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, user: CurrentUser) -> dict[str, Any]:
    return {"trace_id": trace_id, "spans": []}


@router.get("/metrics")
async def retrieval_metrics(
    user: CurrentUser,
    knowledge_base_id: Optional[str] = Query(default=None),
    range: Optional[str] = Query(default="7d"),
) -> dict[str, Any]:
    return {"knowledge_base_id": knowledge_base_id, "range": range, "total_queries": 0, "avg_latency_ms": 0.0, "cache_hit_rate": 0.0}


@router.post("/graph-traversal")
async def graph_traversal(body: GraphTraversalRequest, user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> dict[str, Any]:
    from knowledge_graph.graph_retriever import KnowledgeGraphRetriever
    retriever = KnowledgeGraphRetriever(settings)
    subgraph = await retriever.get_entity_subgraph(body.entity, uuid.UUID(body.knowledge_base_id), max_hops=body.max_hops)
    return subgraph


@router.get("/settings/{kb_id}")
async def get_retrieval_settings(kb_id: str, user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> dict[str, Any]:
    return {
        "knowledge_base_id": kb_id,
        "hybrid": {"enabled": settings.retrieval.hybrid.enabled, "rrf_k": settings.retrieval.hybrid.rrf_k, "vector_weight": settings.retrieval.hybrid.vector_weight, "bm25_weight": settings.retrieval.hybrid.bm25_weight},
        "reranking": {"enabled": settings.retrieval.reranking.enabled, "provider": settings.retrieval.reranking.default_provider, "top_n": settings.retrieval.reranking.top_n},
        "query_rewriting": {"hyde_enabled": settings.retrieval.query_rewriting.hyde_enabled, "step_back_enabled": settings.retrieval.query_rewriting.step_back_enabled},
    }


@router.patch("/settings/{kb_id}")
async def update_retrieval_settings(kb_id: str, body: dict[str, Any], user: CurrentUser) -> dict[str, Any]:
    return {"knowledge_base_id": kb_id, **body}
