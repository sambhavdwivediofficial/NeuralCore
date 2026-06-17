# api/routes/pipelines.py
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_app_settings
from settings import Settings

router = APIRouter()


class PipelineRunRequest(BaseModel):
    query: str
    knowledge_base_id: str
    agent_ids: Optional[list[str]] = None
    pipeline_type: str = "rag"


@router.get("")
async def list_pipelines(user: CurrentUser) -> list[dict[str, Any]]:
    return [
        {"id": "rag", "name": "RAG Pipeline", "description": "Standard retrieval augmented generation"},
        {"id": "agentic_rag", "name": "Agentic RAG", "description": "RAG with agent orchestration"},
        {"id": "graphrag", "name": "GraphRAG", "description": "Knowledge graph enhanced RAG"},
    ]


@router.post("/run")
async def run_pipeline(
    body: PipelineRunRequest,
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    import uuid as _uuid
    from retrieval.retriever import Retriever

    retriever = Retriever(settings=settings)
    try:
        results = await retriever.search(
            knowledge_base_id=_uuid.UUID(body.knowledge_base_id),
            query=body.query,
            use_hybrid=True,
            use_reranking=True,
        )
        context = "\n\n".join(r.text or "" for r in results if r.text)
        from prompt_engine.template_engine import default_registry
        from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
        from model_gateway.provider_factory import get_model_gateway

        gateway = get_model_gateway(settings)
        user_content = default_registry.render("rag_qa", context=context, question=body.query)
        response = await gateway.chat_completion(
            CompletionRequest(messages=[ChatMessage(role=ChatRole.USER, content=user_content)], max_tokens=1024)
        )
        return {
            "answer": response.content or "",
            "sources": [{"id": r.id, "score": r.score, "text": r.text} for r in results],
            "pipeline_type": body.pipeline_type,
        }
    except Exception as exc:
        return {"answer": f"Pipeline error: {exc}", "sources": [], "pipeline_type": body.pipeline_type}
    