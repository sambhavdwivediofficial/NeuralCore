# backend/api/routes/kb_documents.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import CurrentUser, get_db
from database.models.knowledgebase import Document, KnowledgeBase

router = APIRouter()


async def _get_kb_or_404(db: AsyncSession, kb_id: uuid.UUID, org_id: uuid.UUID) -> KnowledgeBase:
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.organization_id == org_id)
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")
    return kb


async def _get_doc_or_404(db: AsyncSession, doc_id: uuid.UUID, kb_id: uuid.UUID) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.knowledge_base_id == kb_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


def _doc_response(doc: Document) -> dict:
    return {
        "id": str(doc.id),
        "knowledge_base_id": str(doc.knowledge_base_id),
        "filename": doc.filename,
        "source_type": doc.source_type,
        "status": doc.status.value if hasattr(doc.status, "value") else str(doc.status),
        "size_bytes": doc.size_bytes,
        "chunk_count": doc.chunk_count,
        "error_message": doc.error_message,
        "metadata": doc.metadata_,
        "uploaded_at": doc.created_at.isoformat() if hasattr(doc, "created_at") else None,
    }


def _chunk_response(chunk) -> dict:
    return {
        "id": str(chunk.id),
        "document_id": str(chunk.document_id),
        "knowledge_base_id": str(chunk.knowledge_base_id),
        "text": chunk.text,
        "chunk_index": chunk.chunk_index,
        "embedding_id": str(chunk.embedding_id) if chunk.embedding_id else None,
        "metadata": chunk.metadata_,
        "created_at": chunk.created_at.isoformat() if hasattr(chunk, "created_at") else None,
    }


@router.get("/{kb_id}/documents/{document_id}", status_code=status.HTTP_200_OK)
async def get_document(
    kb_id: uuid.UUID,
    document_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    await _get_kb_or_404(db, kb_id, user.organization_id)
    doc = await _get_doc_or_404(db, document_id, kb_id)
    return _doc_response(doc)


@router.get("/{kb_id}/documents/{document_id}/chunks", status_code=status.HTTP_200_OK)
async def get_document_chunks(
    kb_id: uuid.UUID,
    document_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if not user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context")
    await _get_kb_or_404(db, kb_id, user.organization_id)
    await _get_doc_or_404(db, document_id, kb_id)

    from database.models.knowledgebase import Chunk
    result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == document_id, Chunk.knowledge_base_id == kb_id)
        .order_by(Chunk.chunk_index)
    )
    return [_chunk_response(c) for c in result.scalars().all()]
