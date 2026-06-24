# backend/api/routes/kb_chunks.py
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_db
from database.models.knowledgebase import Chunk, KnowledgeBase

router = APIRouter()


class UpdateChunkRequest(BaseModel):
    text: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


async def _get_kb_or_404(db: AsyncSession, kb_id: uuid.UUID, org_id: uuid.UUID) -> KnowledgeBase:
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.organization_id == org_id)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return kb


async def _get_chunk_or_404(db: AsyncSession, chunk_id: uuid.UUID, kb_id: uuid.UUID) -> Chunk:
    result = await db.execute(
        select(Chunk).where(Chunk.id == chunk_id, Chunk.knowledge_base_id == kb_id)
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chunk not found")
    return chunk


def _chunk_response(chunk: Chunk) -> dict:
    return {
        "id": str(chunk.id),
        "document_id": str(chunk.document_id),
        "knowledge_base_id": str(chunk.knowledge_base_id),
        "text": chunk.text,
        "chunk_index": chunk.chunk_index,
        "embedding_id": str(chunk.embedding_id) if chunk.embedding_id else None,
        "metadata": chunk.metadata_,
        "created_at": chunk.created_at.isoformat() if hasattr(chunk, "created_at") else None,
        "updated_at": chunk.updated_at.isoformat() if hasattr(chunk, "updated_at") else None,
    }


@router.get("/{kb_id}/chunks/{chunk_id}", status_code=status.HTTP_200_OK)
async def get_chunk(
    kb_id: uuid.UUID,
    chunk_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    await _get_kb_or_404(db, kb_id, user.organization_id)
    chunk = await _get_chunk_or_404(db, chunk_id, kb_id)
    return _chunk_response(chunk)


@router.patch("/{kb_id}/chunks/{chunk_id}", status_code=status.HTTP_200_OK)
async def update_chunk(
    kb_id: uuid.UUID,
    chunk_id: uuid.UUID,
    payload: UpdateChunkRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    await _get_kb_or_404(db, kb_id, user.organization_id)
    chunk = await _get_chunk_or_404(db, chunk_id, kb_id)

    text_changed = False
    if payload.text is not None:
        stripped = payload.text.strip()
        if not stripped:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Chunk text cannot be empty",
            )
        if stripped != chunk.text:
            chunk.text = stripped
            text_changed = True

    if payload.metadata is not None:
        chunk.metadata_ = {**(chunk.metadata_ or {}), **payload.metadata}

    await db.commit()
    await db.refresh(chunk)

    if text_changed:
        async def _reembed():
            try:
                from task_queue.tasks.embeddings import reembed_chunk
                reembed_chunk.delay(str(chunk_id), str(kb_id), chunk.text)
            except Exception:
                pass
        background_tasks.add_task(_reembed)

    return _chunk_response(chunk)


@router.delete(
    "/{kb_id}/chunks/{chunk_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_chunk(
    kb_id: uuid.UUID,
    chunk_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> Response:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    kb = await _get_kb_or_404(db, kb_id, user.organization_id)
    chunk = await _get_chunk_or_404(db, chunk_id, kb_id)

    embedding_id = chunk.embedding_id
    vector_db_backend = kb.vector_db_backend

    await db.delete(chunk)
    await db.commit()

    if embedding_id and vector_db_backend:
        async def _remove_vector():
            try:
                from vector_stores import get_vector_store_adapter
                from settings import get_settings
                store = get_vector_store_adapter(settings=get_settings())
                await store.delete(str(embedding_id), collection_name=str(kb_id))
            except Exception:
                pass
        background_tasks.add_task(_remove_vector)

    return Response(status_code=status.HTTP_204_NO_CONTENT)
