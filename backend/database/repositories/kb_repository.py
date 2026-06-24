# backend/database/repositories/kb_repository.py
from __future__ import annotations

import uuid
from typing import Optional

import numpy as np
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.knowledgebase import Chunk, Document, KnowledgeBase


async def get_kb(
    db: AsyncSession, kb_id: uuid.UUID, tenant_id: uuid.UUID
) -> Optional[KnowledgeBase]:
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.organization_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def get_document(
    db: AsyncSession, document_id: uuid.UUID, kb_id: uuid.UUID
) -> Optional[Document]:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.knowledge_base_id == kb_id,
        )
    )
    return result.scalar_one_or_none()


async def get_chunk(
    db: AsyncSession, chunk_id: uuid.UUID, kb_id: uuid.UUID
) -> Optional[Chunk]:
    result = await db.execute(
        select(Chunk).where(
            Chunk.id == chunk_id,
            Chunk.knowledge_base_id == kb_id,
        )
    )
    return result.scalar_one_or_none()


async def get_chunks_for_document(
    db: AsyncSession, document_id: uuid.UUID, kb_id: uuid.UUID
) -> list[Chunk]:
    result = await db.execute(
        select(Chunk)
        .where(
            Chunk.document_id == document_id,
            Chunk.knowledge_base_id == kb_id,
        )
        .order_by(Chunk.chunk_index)
    )
    return list(result.scalars().all())


async def get_all_chunks_with_embeddings(
    db: AsyncSession, kb_id: uuid.UUID
) -> list[Chunk]:
    result = await db.execute(
        select(Chunk).where(
            Chunk.knowledge_base_id == kb_id,
            Chunk.embedding_vector.is_not(None),
        )
    )
    return list(result.scalars().all())


async def update_chunk_text_and_metadata(
    db: AsyncSession,
    chunk: Chunk,
    text: Optional[str],
    metadata: Optional[dict],
) -> Chunk:
    if text is not None:
        chunk.text = text
    if metadata is not None:
        chunk.metadata_ = {**(chunk.metadata_ or {}), **metadata}
    await db.commit()
    await db.refresh(chunk)
    return chunk


async def delete_chunk(db: AsyncSession, chunk: Chunk) -> None:
    await db.delete(chunk)
    await db.commit()


def _compute_umap(vectors: np.ndarray) -> np.ndarray:
    try:
        import umap
        reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=min(15, len(vectors) - 1))
        return reducer.fit_transform(vectors)
    except ImportError:
        from sklearn.decomposition import PCA
        reducer = PCA(n_components=2, random_state=42)
        return reducer.fit_transform(vectors)


def _compute_tsne(vectors: np.ndarray) -> np.ndarray:
    from sklearn.manifold import TSNE
    perplexity = min(30, len(vectors) - 1)
    reducer = TSNE(n_components=2, random_state=42, perplexity=perplexity)
    return reducer.fit_transform(vectors)


def _cluster_points(points_2d: np.ndarray) -> list[Optional[int]]:
    try:
        from sklearn.cluster import DBSCAN
        labels = DBSCAN(eps=0.5, min_samples=3).fit_predict(points_2d)
        return [int(l) if l >= 0 else None for l in labels]
    except Exception:
        return [None] * len(points_2d)


async def compute_embedding_visualization(
    db: AsyncSession,
    kb_id: uuid.UUID,
    method: str = "umap",
) -> dict:
    chunks = await get_all_chunks_with_embeddings(db, kb_id)

    if not chunks:
        return {"method": method, "points": []}

    raw_vectors = []
    valid_chunks = []
    for chunk in chunks:
        vec = getattr(chunk, "embedding_vector", None)
        if vec is not None:
            raw_vectors.append(vec)
            valid_chunks.append(chunk)

    if not raw_vectors:
        return {"method": method, "points": []}

    vectors_np = np.array(raw_vectors, dtype=np.float32)

    if len(vectors_np) < 2:
        return {
            "method": method,
            "points": [
                {
                    "id": str(valid_chunks[0].id),
                    "x": 0.0,
                    "y": 0.0,
                    "label": valid_chunks[0].text[:60] if valid_chunks[0].text else "",
                    "cluster": None,
                }
            ],
        }

    if method == "tsne":
        coords = _compute_tsne(vectors_np)
    else:
        coords = _compute_umap(vectors_np)

    clusters = _cluster_points(coords)

    points = []
    for i, chunk in enumerate(valid_chunks):
        points.append(
            {
                "id": str(chunk.id),
                "x": float(coords[i, 0]),
                "y": float(coords[i, 1]),
                "label": chunk.text[:60] if chunk.text else str(chunk.id),
                "cluster": clusters[i],
            }
        )

    return {"method": method, "points": points}
