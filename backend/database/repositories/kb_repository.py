# backend/database/repositories/kb_repository.py
from __future__ import annotations

import uuid
from typing import Optional

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.knowledgebase import Chunk, Document, KnowledgeBase


async def get_kb(db: AsyncSession, kb_id: uuid.UUID, org_id: uuid.UUID) -> Optional[KnowledgeBase]:
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id, KnowledgeBase.organization_id == org_id)
    )
    return result.scalar_one_or_none()


async def get_document(db: AsyncSession, doc_id: uuid.UUID, kb_id: uuid.UUID) -> Optional[Document]:
    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.knowledge_base_id == kb_id)
    )
    return result.scalar_one_or_none()


async def get_chunk(db: AsyncSession, chunk_id: uuid.UUID, kb_id: uuid.UUID) -> Optional[Chunk]:
    result = await db.execute(
        select(Chunk).where(Chunk.id == chunk_id, Chunk.knowledge_base_id == kb_id)
    )
    return result.scalar_one_or_none()


async def get_chunks_for_document(db: AsyncSession, doc_id: uuid.UUID, kb_id: uuid.UUID) -> list[Chunk]:
    result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == doc_id, Chunk.knowledge_base_id == kb_id)
        .order_by(Chunk.chunk_index)
    )
    return list(result.scalars().all())


async def get_all_chunks_with_embeddings(db: AsyncSession, kb_id: uuid.UUID) -> list[Chunk]:
    result = await db.execute(
        select(Chunk).where(
            Chunk.knowledge_base_id == kb_id,
            Chunk.embedding_vector.is_not(None),
        )
    )
    return list(result.scalars().all())


def _compute_umap(vectors: np.ndarray) -> np.ndarray:
    try:
        import umap
        reducer = umap.UMAP(
            n_components=2,
            random_state=42,
            n_neighbors=min(15, len(vectors) - 1),
        )
        return reducer.fit_transform(vectors)
    except ImportError:
        from sklearn.decomposition import PCA
        return PCA(n_components=2, random_state=42).fit_transform(vectors)


def _compute_tsne(vectors: np.ndarray) -> np.ndarray:
    from sklearn.manifold import TSNE
    return TSNE(
        n_components=2,
        random_state=42,
        perplexity=min(30, len(vectors) - 1),
    ).fit_transform(vectors)


def _cluster(points: np.ndarray) -> list[Optional[int]]:
    try:
        from sklearn.cluster import DBSCAN
        labels = DBSCAN(eps=0.5, min_samples=3).fit_predict(points)
        return [int(l) if l >= 0 else None for l in labels]
    except Exception:
        return [None] * len(points)


async def compute_embedding_visualization(
    db: AsyncSession,
    kb_id: uuid.UUID,
    method: str = "umap",
) -> dict:
    chunks = await get_all_chunks_with_embeddings(db, kb_id)
    if not chunks:
        return {"method": method, "points": []}

    valid = [(c, c.embedding_vector) for c in chunks if c.embedding_vector is not None]
    if not valid:
        return {"method": method, "points": []}

    valid_chunks, raw_vectors = zip(*valid)
    vectors_np = np.array(raw_vectors, dtype=np.float32)

    if len(vectors_np) < 2:
        return {
            "method": method,
            "points": [{
                "id": str(valid_chunks[0].id),
                "x": 0.0,
                "y": 0.0,
                "label": valid_chunks[0].text[:60],
                "cluster": None,
            }],
        }

    coords = _compute_tsne(vectors_np) if method == "tsne" else _compute_umap(vectors_np)
    clusters = _cluster(coords)

    return {
        "method": method,
        "points": [
            {
                "id": str(c.id),
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
                "label": c.text[:60] if c.text else str(c.id),
                "cluster": clusters[i],
            }
            for i, c in enumerate(valid_chunks)
        ],
    }
