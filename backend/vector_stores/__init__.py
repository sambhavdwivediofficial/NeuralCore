# vector_stores/__init__.py
from __future__ import annotations

from settings import Settings, VectorDBBackend
from vector_stores.base import BaseVectorStore, VectorStoreError

_store_cache: dict[str, BaseVectorStore] = {}


class VectorStoreNotConfiguredError(VectorStoreError):
    def __init__(self, backend: str) -> None:
        super().__init__("Vector store backend is not configured", backend=backend)


def get_vector_store_adapter(settings: Settings, backend: str | VectorDBBackend | None = None) -> BaseVectorStore:
    resolved = VectorDBBackend(backend) if backend is not None else settings.vector_db.default

    if resolved.value in _store_cache:
        return _store_cache[resolved.value]

    if resolved == VectorDBBackend.QDRANT:
        from vector_stores.qdrant import QdrantVectorStore

        instance: BaseVectorStore = QdrantVectorStore(settings)
    elif resolved == VectorDBBackend.MILVUS:
        from vector_stores.milvus import MilvusVectorStore

        instance = MilvusVectorStore(settings)
    elif resolved == VectorDBBackend.WEAVIATE:
        from vector_stores.weaviate import WeaviateVectorStore

        instance = WeaviateVectorStore(settings)
    elif resolved == VectorDBBackend.PGVECTOR:
        from vector_stores.pgvector import PGVectorStore

        instance = PGVectorStore(settings)
    elif resolved == VectorDBBackend.ELASTICSEARCH:
        from vector_stores.elastic import ElasticsearchVectorStore

        instance = ElasticsearchVectorStore(settings)
    elif resolved == VectorDBBackend.FAISS:
        from vector_stores.faiss import FaissVectorStore

        instance = FaissVectorStore(settings)
    else:
        raise VectorStoreNotConfiguredError(resolved.value)

    _store_cache[resolved.value] = instance
    return instance


def reset_vector_store_cache() -> None:
    _store_cache.clear()


__all__ = [
    "BaseVectorStore",
    "VectorStoreError",
    "VectorStoreNotConfiguredError",
    "get_vector_store_adapter",
    "reset_vector_store_cache",
]
