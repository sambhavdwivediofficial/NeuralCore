# api/routes/knowledgebases.py
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel

from api.dependencies import CurrentUser, Pagination, get_app_settings, get_db
from api.exceptions import NotFoundError
from settings import Settings

router = APIRouter()


class KBCreateRequest(BaseModel):
    name: str
    project_id: str
    description: Optional[str] = None
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-large"
    chunking_strategy: str = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 50
    vector_db_backend: Optional[str] = None
    config: dict[str, Any] = {}


class KBUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None


def _kb_response(kb: Any) -> dict[str, Any]:
    return {
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description,
        "project_id": str(kb.project_id),
        "status": kb.status.value,
        "embedding_provider": kb.embedding_provider,
        "embedding_model": kb.embedding_model,
        "embedding_dimension": kb.embedding_dimension,
        "chunking_strategy": kb.chunking_strategy.value,
        "chunk_size": kb.chunk_size,
        "chunk_overlap": kb.chunk_overlap,
        "vector_db_backend": kb.vector_db_backend,
        "document_count": kb.document_count,
        "chunk_count": kb.chunk_count,
        "config": kb.config,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
    }


@router.get("")
async def list_knowledge_bases(
    user: CurrentUser,
    pagination: Pagination,
    db=Depends(get_db),
    project_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    from sqlalchemy import text
    from database.connection import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        if project_id:
            result = await conn.execute(
                text("SELECT * FROM knowledge_bases WHERE project_id = :pid ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
                {"pid": project_id, "limit": pagination.limit, "offset": pagination.offset},
            )
        else:
            result = await conn.execute(
                text("SELECT * FROM knowledge_bases ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
                {"limit": pagination.limit, "offset": pagination.offset},
            )
        rows = result.mappings().all()

    return {
        "items": [dict(r) for r in rows],
        "total": len(rows),
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.get("/chunking-strategies")
async def list_chunking_strategies() -> list[dict[str, Any]]:
    return [
        {"id": "token", "name": "Token", "description": "Split by exact token count"},
        {"id": "recursive", "name": "Recursive", "description": "Hierarchical separator splitting"},
        {"id": "markdown", "name": "Markdown", "description": "Split on markdown headers"},
        {"id": "code", "name": "Code", "description": "Split on code block boundaries"},
        {"id": "ast", "name": "AST", "description": "Python AST-aware splitting"},
        {"id": "semantic", "name": "Semantic", "description": "Sentence similarity grouping"},
        {"id": "hybrid", "name": "Hybrid", "description": "Auto-detect best strategy"},
        {"id": "character", "name": "Character", "description": "Simple character-count splitting"},
    ]


@router.get("/ingestion-sources")
async def list_ingestion_sources() -> list[dict[str, Any]]:
    return [
        {"id": "pdf", "name": "PDF", "description": "PDF documents"},
        {"id": "docx", "name": "Word Document", "description": "Microsoft Word files"},
        {"id": "txt", "name": "Plain Text", "description": "Text files"},
        {"id": "markdown", "name": "Markdown", "description": "Markdown files"},
        {"id": "website", "name": "Website", "description": "Web page crawling"},
        {"id": "github", "name": "GitHub", "description": "GitHub repository"},
        {"id": "notion", "name": "Notion", "description": "Notion pages and databases"},
        {"id": "confluence", "name": "Confluence", "description": "Confluence spaces"},
        {"id": "jira", "name": "Jira", "description": "Jira issues"},
        {"id": "slack", "name": "Slack", "description": "Slack channels"},
        {"id": "postgres", "name": "PostgreSQL", "description": "PostgreSQL database"},
        {"id": "mongodb", "name": "MongoDB", "description": "MongoDB collection"},
        {"id": "youtube", "name": "YouTube", "description": "YouTube transcripts"},
    ]


@router.get("/{kb_id}")
async def get_knowledge_base(kb_id: str, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from sqlalchemy import text
    from database.connection import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT * FROM knowledge_bases WHERE id = :id"), {"id": kb_id})
        row = result.mappings().first()
    if row is None:
        raise NotFoundError("Knowledge base", kb_id)
    return dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_knowledge_base(
    body: KBCreateRequest,
    user: CurrentUser,
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    from embeddings.embedding_factory import resolve_embedding_dimension
    from database.connection import get_engine

    dimension = resolve_embedding_dimension(settings, body.embedding_provider, body.embedding_model)
    kb_id = uuid.uuid4()
    collection_name = f"nc_{kb_id.hex}"
    backend = body.vector_db_backend or settings.vector_db.default.value
    chunking_strategy = body.chunking_strategy

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            """
                INSERT INTO knowledge_bases (id, project_id, name, description, vector_db_backend,
                    collection_name, embedding_provider, embedding_model, embedding_dimension,
                    chunking_strategy, chunk_size, chunk_overlap, status, document_count, chunk_count,
                    config, created_at, updated_at)
                VALUES (:id, :project_id, :name, :description, :backend, :collection, :emb_provider,
                    :emb_model, :emb_dim, :strategy, :chunk_size, :chunk_overlap, 'creating', 0, 0,
                    :config::jsonb, NOW(), NOW())
            """,
            {
                "id": str(kb_id),
                "project_id": body.project_id,
                "name": body.name,
                "description": body.description or "",
                "backend": backend,
                "collection": collection_name,
                "emb_provider": body.embedding_provider,
                "emb_model": body.embedding_model,
                "emb_dim": dimension,
                "strategy": chunking_strategy,
                "chunk_size": body.chunk_size,
                "chunk_overlap": body.chunk_overlap,
                "config": json.dumps(body.config),
            },
        )

    return {
        "id": str(kb_id),
        "name": body.name,
        "description": body.description,
        "project_id": body.project_id,
        "status": "creating",
        "embedding_provider": body.embedding_provider,
        "embedding_model": body.embedding_model,
        "embedding_dimension": dimension,
        "chunking_strategy": chunking_strategy,
        "chunk_size": body.chunk_size,
        "chunk_overlap": body.chunk_overlap,
        "vector_db_backend": backend,
        "collection_name": collection_name,
        "document_count": 0,
        "chunk_count": 0,
        "config": body.config,
    }


@router.patch("/{kb_id}")
async def update_knowledge_base(
    kb_id: str, body: KBUpdateRequest, user: CurrentUser, db=Depends(get_db)
) -> dict[str, Any]:
    from sqlalchemy import text
    from database.connection import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        if body.name:
            await conn.execute(
                text("UPDATE knowledge_bases SET name = :name, updated_at = NOW() WHERE id = :id"),
                {"name": body.name, "id": kb_id},
            )
        if body.description is not None:
            await conn.execute(
                text("UPDATE knowledge_bases SET description = :desc, updated_at = NOW() WHERE id = :id"),
                {"desc": body.description, "id": kb_id},
            )

    return await get_knowledge_base(kb_id, user, db)


@router.delete("/{kb_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_knowledge_base(kb_id: str, user: CurrentUser, db=Depends(get_db)) -> Response:
    from sqlalchemy import text
    from database.connection import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM knowledge_bases WHERE id = :id"), {"id": kb_id})

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{kb_id}/stats")
async def kb_stats(kb_id: str, user: CurrentUser, db=Depends(get_db)) -> dict[str, Any]:
    from sqlalchemy import text
    from database.connection import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT document_count, chunk_count, status FROM knowledge_bases WHERE id = :id"),
            {"id": kb_id},
        )
        row = result.mappings().first()
    if row is None:
        raise NotFoundError("Knowledge base", kb_id)
    return {
        "knowledge_base_id": kb_id,
        "document_count": row["document_count"],
        "chunk_count": row["chunk_count"],
        "status": row["status"],
    }


@router.get("/{kb_id}/documents")
async def list_documents(
    kb_id: str, user: CurrentUser, pagination: Pagination, db=Depends(get_db)
) -> dict[str, Any]:
    from sqlalchemy import text
    from database.connection import get_engine

    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT * FROM kb_documents WHERE knowledge_base_id = :kb_id ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            {"kb_id": kb_id, "limit": pagination.limit, "offset": pagination.offset},
        )
        rows = result.mappings().all()
    return {
        "items": [dict(r) for r in rows],
        "total": len(rows),
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("/{kb_id}/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    kb_id: str,
    user: CurrentUser,
    file: UploadFile = File(...),
    db=Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> dict[str, Any]:
    doc_id = uuid.uuid4().hex
    content = await file.read()
    from task_queue.celery import celery_app

    return {
        "document_id": doc_id,
        "knowledge_base_id": kb_id,
        "filename": file.filename,
        "status": "processing",
        "size_bytes": len(content),
    }


@router.delete("/{kb_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_document(kb_id: str, document_id: str, user: CurrentUser, db=Depends(get_db)) -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{kb_id}/documents/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(kb_id: str, document_id: str, user: CurrentUser) -> dict[str, str]:
    return {"document_id": document_id, "status": "reprocessing"}


@router.get("/{kb_id}/chunks")
async def list_chunks(
    kb_id: str, user: CurrentUser, pagination: Pagination, search: Optional[str] = Query(default=None)
) -> dict[str, Any]:
    return {"items": [], "total": 0, "page": pagination.page, "page_size": pagination.page_size}


@router.post("/{kb_id}/ingestion-sources")
async def add_ingestion_source(kb_id: str, body: dict[str, Any], user: CurrentUser) -> dict[str, Any]:
    return {"knowledge_base_id": kb_id, "source_config": body, "status": "queued"}
