# vector_stores/base.py
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from settings import DistanceMetric, Settings, VectorDBBackend


class VectorStoreError(Exception):
    def __init__(self, message: str, backend: str) -> None:
        self.backend = backend
        super().__init__(f"[{backend}] {message}")


class CollectionNotFoundError(VectorStoreError):
    pass


class VectorStoreConnectionError(VectorStoreError):
    pass


class FilterOperator(str, enum.Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    EXISTS = "exists"


class MetadataFilter(BaseModel):
    field: str
    operator: FilterOperator
    value: Any = None


class VectorPoint(BaseModel):
    id: str
    vector: list[float]
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorSearchResult(BaseModel):
    id: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    vector: list[float] | None = None


class CollectionStats(BaseModel):
    name: str
    vector_count: int
    dimension: int


class BaseVectorStore(ABC):
    backend_name: VectorDBBackend

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    async def create_collection(
        self, collection_name: str, dimension: int, metric: DistanceMetric = DistanceMetric.COSINE
    ) -> None: ...

    async def recreate_collection(
        self, collection_name: str, dimension: int, metric: DistanceMetric = DistanceMetric.COSINE
    ) -> None:
        if await self.collection_exists(collection_name):
            await self.delete_collection(collection_name)
        await self.create_collection(collection_name, dimension, metric)

    @abstractmethod
    async def delete_collection(self, collection_name: str) -> None: ...

    @abstractmethod
    async def collection_exists(self, collection_name: str) -> bool: ...

    @abstractmethod
    async def upsert(self, collection_name: str, points: list[VectorPoint] | list[dict[str, Any]]) -> int: ...

    @abstractmethod
    async def delete(self, collection_name: str, ids: list[str]) -> int: ...

    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: list[MetadataFilter] | None = None,
        with_vectors: bool = False,
        score_threshold: float | None = None,
    ) -> list[VectorSearchResult]: ...

    @abstractmethod
    async def get(self, collection_name: str, ids: list[str]) -> list[VectorPoint]: ...

    @abstractmethod
    async def count(self, collection_name: str) -> int: ...

    @abstractmethod
    async def health_check(self) -> bool: ...

    @staticmethod
    def _normalize_points(points: list[VectorPoint] | list[dict[str, Any]]) -> list[VectorPoint]:
        normalized: list[VectorPoint] = []
        for point in points:
            if isinstance(point, VectorPoint):
                normalized.append(point)
            else:
                normalized.append(VectorPoint.model_validate(point))
        return normalized
