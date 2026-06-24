# backend/api/routes/kb_chunks.py
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.knowledgebase import KnowledgeBase, Chunk
from database.session import get_db
from dependencies import get_current_user
from database.models.user import User

router = APIRouter()


class UpdateChunkRequest(BaseModel):
    text: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


async def _get_kb_or_404(
    db: AsyncSession, kb_id: uuid.UUID, tenant_id: uuid.UUID
) -> KnowledgeBase:
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.organization_id == tenant_id,
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return kb


async def _get_chunk_or_404(
    db: AsyncSession, chunk_id: uuid.UUID, kb_id: uuid.UUID
) -> Chunk:
    result = await db.execute(
        select(Chunk).where(
            Chunk.id == chunk_id,
            Chunk.knowledge_base_id == kb_id,
        )
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found",
        )
    return chunk


def _chunk_response(chunk: Chunk) -> dict:
    return {
        "id": str(chunk.id),
        "document_id": str(chunk.document_id),
        "knowledge_base_id": str(chunk.knowledge_base_id),
        "text": chunk.text,
        "chunk_index": chunk.chunk_index if hasattr(chunk, "chunk_index") else None,
        "embedding_id": (
            str(chunk.embedding_id)
            if hasattr(chunk, "embedding_id") and chunk.embedding_id
            else None
        ),
        "metadata": chunk.metadata_ if hasattr(chunk, "metadata_") else {},
        "created_at": chunk.created_at.isoformat() if hasattr(chunk, "created_at") else None,
        "updated_at": chunk.updated_at.isoformat() if hasattr(chunk, "updated_at") else None,
    }


async def _trigger_reembedding(
    chunk_id: uuid.UUID,
    kb_id: uuid.UUID,
    text: str,
) -> None:
    try:
        from task_queue.tasks.embeddings import reembed_chunk
        reembed_chunk.delay(str(chunk_id), str(kb_id), text)
    except Exception:
        pass


@router.get("/{kb_id}/chunks/{chunk_id}", status_code=status.HTTP_200_OK)
async def get_chunk(
    kb_id: uuid.UUID,
    chunk_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    tenant_id = current_user.organization_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    await _get_kb_or_404(db, kb_id, tenant_id)
    chunk = await _get_chunk_or_404(db, chunk_id, kb_id)
    return _chunk_response(chunk)


@router.patch("/{kb_id}/chunks/{chunk_id}", status_code=status.HTTP_200_OK)
async def update_chunk(
    kb_id: uuid.UUID,
    chunk_id: uuid.UUID,
    payload: UpdateChunkRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    tenant_id = current_user.organization_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    await _get_kb_or_404(db, kb_id, tenant_id)
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
        if hasattr(chunk, "metadata_"):
            chunk.metadata_ = {**(chunk.metadata_ or {}), **payload.metadata}

    await db.commit()
    await db.refresh(chunk)

    if text_changed:
        background_tasks.add_task(
            _trigger_reembedding, chunk.id, kb_id, chunk.text
        )

    return _chunk_response(chunk)


@router.delete("/{kb_id}/chunks/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chunk(
    kb_id: uuid.UUID,
    chunk_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    tenant_id = current_user.organization_id
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")

    await _get_kb_or_404(db, kb_id, tenant_id)
    chunk = await _get_chunk_or_404(db, chunk_id, kb_id)

    embedding_id = getattr(chunk, "embedding_id", None)
    vector_db_backend = None
    try:
        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
        )
        kb = kb_result.scalar_one_or_none()
        if kb:
            vector_db_backend = getattr(kb, "vector_db_backend", None)
    except Exception:
        pass

    await db.delete(chunk)
    await db.commit()

    if embedding_id and vector_db_backend:
        async def _remove_from_vector_store():
            try:
                from vector_stores import get_vector_store
                store = get_vector_store(vector_db_backend)
                await store.delete(str(embedding_id), collection_name=str(kb_id))
            except Exception:
                pass

        background_tasks.add_task(_remove_from_vector_store)
