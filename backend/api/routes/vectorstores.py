# api/routes/vectorstores.py
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, get_app_settings
from settings import Settings, VectorDBBackend

router = APIRouter()


class VectorStoreCreateRequest(BaseModel):
    name: str
    backend: str
    config: dict[str, Any] = {}


class TestConnectionRequest(BaseModel):
    backend: str
    config: dict[str, Any] = {}


@router.get("")
async def list_vector_stores(user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> list[dict[str, Any]]:
    backends = [
        {"id": VectorDBBackend.QDRANT.value, "name": "Qdrant", "is_default": settings.vector_db.default == VectorDBBackend.QDRANT},
        {"id": VectorDBBackend.MILVUS.value, "name": "Milvus", "is_default": False},
        {"id": VectorDBBackend.WEAVIATE.value, "name": "Weaviate", "is_default": False},
        {"id": VectorDBBackend.PGVECTOR.value, "name": "PGVector", "is_default": False},
        {"id": VectorDBBackend.ELASTICSEARCH.value, "name": "Elasticsearch", "is_default": False},
        {"id": VectorDBBackend.FAISS.value, "name": "FAISS", "is_default": False},
    ]
    return backends


@router.get("/{store_id}")
async def get_vector_store(store_id: str, user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> dict[str, Any]:
    return {"id": store_id, "name": store_id.title(), "backend": store_id, "status": "active"}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_vector_store(body: VectorStoreCreateRequest, user: CurrentUser) -> dict[str, Any]:
    return {"id": body.backend, "name": body.name, "backend": body.backend, "config": body.config}


@router.patch("/{store_id}")
async def update_vector_store(store_id: str, body: dict[str, Any], user: CurrentUser) -> dict[str, Any]:
    return {"id": store_id, **body}


@router.delete("/{store_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_vector_store(store_id: str, user: CurrentUser) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/test-connection")
async def test_connection(body: TestConnectionRequest, user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> dict[str, Any]:
    try:
        from vector_stores import get_vector_store_adapter

        adapter = get_vector_store_adapter(settings=settings, backend=body.backend)
        healthy = await adapter.health_check()
        return {"backend": body.backend, "connected": healthy}
    except Exception as exc:
        return {"backend": body.backend, "connected": False, "error": str(exc)}


@router.get("/{store_id}/collections")
async def list_collections(store_id: str, user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> list[dict[str, Any]]:
    return []


@router.get("/{store_id}/metrics")
async def store_metrics(store_id: str, user: CurrentUser) -> dict[str, Any]:
    return {"store_id": store_id, "total_vectors": 0, "collections": 0, "storage_bytes": 0}


@router.get("/{store_id}/qdrant/status")
@router.get("/{store_id}/milvus/status")
@router.get("/{store_id}/pgvector/status")
async def store_status(store_id: str, user: CurrentUser, settings: Settings = Depends(get_app_settings)) -> dict[str, Any]:
    try:
        from vector_stores import get_vector_store_adapter

        adapter = get_vector_store_adapter(settings=settings, backend=store_id)
        healthy = await adapter.health_check()
        return {"store_id": store_id, "healthy": healthy}
    except Exception:
        return {"store_id": store_id, "healthy": False}


@router.post("/{store_id}/collections/{name}/rebuild")
async def rebuild_collection(store_id: str, name: str, user: CurrentUser) -> dict[str, str]:
    return {"store_id": store_id, "collection": name, "status": "rebuilding"}


@router.post("/{store_id}/snapshot")
async def create_snapshot(store_id: str, user: CurrentUser) -> dict[str, str]:
    return {"store_id": store_id, "snapshot_id": f"snap_{store_id}_{__import__('uuid').uuid4().hex[:8]}", "status": "creating"}
