# backend/api/routes/embeddings.py
from __future__ import annotations

import uuid
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select

from api.dependencies import CurrentUser, get_app_settings, get_db
from settings import Settings

router = APIRouter()


class EmbedRequest(BaseModel):
    text: str
    provider: Optional[str] = None


class TestProviderRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None


@router.get("/providers")
async def list_providers(
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> list[dict[str, Any]]:
    return [
        {
            "id": name,
            "name": name.replace("_", " ").title(),
            "enabled": config.enabled,
            "default_model": config.default_model,
            "models": list(config.models.keys()),
            "dimension": config.dimension,
        }
        for name, config in settings.embeddings.providers.items()
    ]


@router.get("/providers/{provider_id}")
async def get_provider(
    provider_id: str,
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    config = settings.embeddings.providers.get(provider_id)
    if config is None:
        from api.exceptions import NotFoundError
        raise NotFoundError("Provider", provider_id)
    return {
        "id": provider_id,
        "enabled": config.enabled,
        "default_model": config.default_model,
        "models": config.models,
        "dimension": config.dimension,
    }


@router.post("/providers/test")
async def test_provider(
    body: TestProviderRequest,
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    try:
        from embeddings.embedding_factory import get_embedding_provider
        provider = get_embedding_provider(settings=settings, provider_name=body.provider)
        healthy = await provider.health_check()
        return {"provider": body.provider, "healthy": healthy}
    except Exception as exc:
        return {"provider": body.provider, "healthy": False, "error": str(exc)}


@router.post("/generate")
async def generate_embedding(
    body: EmbedRequest,
    user: CurrentUser,
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    from embeddings.embedding_factory import get_embedding_provider
    provider = get_embedding_provider(settings=settings, provider_name=body.provider)
    vector = await provider.embed_query(body.text)
    return {
        "text": body.text,
        "vector": vector,
        "dimension": len(vector),
        "provider": body.provider or settings.embeddings.default_provider.value,
    }


@router.get("/visualize")
async def visualize_embeddings(
    user: CurrentUser,
    db=Depends(get_db),
    kb_id: uuid.UUID = Query(..., description="Knowledge base ID"),
    method: Literal["umap", "tsne"] = Query(default="umap"),
) -> dict[str, Any]:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    from database.models.knowledgebase import KnowledgeBase
    kb_result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.organization_id == user.organization_id,
        )
    )
    if not kb_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    from database.repositories.kb_repository import compute_embedding_visualization
    return await compute_embedding_visualization(db, kb_id, method)


@router.get("/cache/stats")
async def cache_stats(user: CurrentUser) -> dict[str, Any]:
    try:
        import neuralcore_engine
        func = getattr(neuralcore_engine, "py_embedding_cache_stats", None)
        if func:
            return func()
    except ImportError:
        pass
    return {"hits": 0, "misses": 0, "hit_rate": 0.0, "size": 0, "capacity": 0}


@router.post("/cache/clear")
async def clear_cache(user: CurrentUser) -> dict[str, str]:
    try:
        import neuralcore_engine
        func = getattr(neuralcore_engine, "py_embedding_cache_invalidate", None)
        if func:
            func()
    except ImportError:
        pass
    return {"message": "Cache cleared"}
