# vector_stores/qdrant.py
from __future__ import annotations

from settings import DistanceMetric, Settings, VectorDBBackend
from vector_stores.base import (
    BaseVectorStore,
    CollectionNotFoundError,
    FilterOperator,
    MetadataFilter,
    VectorPoint,
    VectorSearchResult,
    VectorStoreConnectionError,
)

_METRIC_MAP = {
    DistanceMetric.COSINE: "Cosine",
    DistanceMetric.DOT_PRODUCT: "Dot",
    DistanceMetric.EUCLIDEAN: "Euclid",
    DistanceMetric.MANHATTAN: "Manhattan",
}


class QdrantVectorStore(BaseVectorStore):
    backend_name = VectorDBBackend.QDRANT

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        from qdrant_client import AsyncQdrantClient

        config = settings.vector_db.qdrant
        self._config = config
        self._client = AsyncQdrantClient(
            host=config.host,
            port=config.port,
            grpc_port=config.grpc_port,
            prefer_grpc=config.prefer_grpc,
            https=config.https,
            api_key=config.api_key.get_secret_value() if config.api_key else None,
            timeout=config.timeout,
        )

    async def create_collection(
        self, collection_name: str, dimension: int, metric: DistanceMetric = DistanceMetric.COSINE
    ) -> None:
        from qdrant_client import models

        quantization_config = None
        if self._config.quantization == "scalar":
            quantization_config = models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(type=models.ScalarType.INT8, quantile=0.99, always_ram=True)
            )

        await self._client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=dimension, distance=models.Distance(_METRIC_MAP.get(metric, "Cosine"))),
            hnsw_config=models.HnswConfigDiff(m=self._config.hnsw_m, ef_construct=self._config.hnsw_ef_construct),
            quantization_config=quantization_config,
        )

    async def delete_collection(self, collection_name: str) -> None:
        await self._client.delete_collection(collection_name)

    async def collection_exists(self, collection_name: str) -> bool:
        return await self._client.collection_exists(collection_name)

    async def upsert(self, collection_name: str, points) -> int:
        from qdrant_client import models

        normalized = self._normalize_points(points)
        await self._client.upsert(
            collection_name=collection_name,
            points=[models.PointStruct(id=point.id, vector=point.vector, payload=point.metadata) for point in normalized],
        )
        return len(normalized)

    async def delete(self, collection_name: str, ids: list[str]) -> int:
        from qdrant_client import models

        await self._client.delete(collection_name=collection_name, points_selector=models.PointIdsList(points=ids))
        return len(ids)

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: list[MetadataFilter] | None = None,
        with_vectors: bool = False,
        score_threshold: float | None = None,
    ) -> list[VectorSearchResult]:
        query_filter = self._build_filter(filters)
        try:
            results = await self._client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=query_filter,
                with_vectors=with_vectors,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            message = str(exc).lower()
            if "not found" in message or "doesn't exist" in message:
                raise CollectionNotFoundError(str(exc), backend=self.backend_name.value) from exc
            raise VectorStoreConnectionError(str(exc), backend=self.backend_name.value) from exc

        return [
            VectorSearchResult(
                id=str(point.id),
                score=point.score,
                metadata=point.payload or {},
                vector=point.vector if with_vectors else None,
            )
            for point in results
        ]

    async def get(self, collection_name: str, ids: list[str]) -> list[VectorPoint]:
        records = await self._client.retrieve(collection_name=collection_name, ids=ids, with_vectors=True)
        return [VectorPoint(id=str(record.id), vector=record.vector or [], metadata=record.payload or {}) for record in records]

    async def count(self, collection_name: str) -> int:
        result = await self._client.count(collection_name=collection_name, exact=True)
        return result.count

    async def health_check(self) -> bool:
        try:
            await self._client.get_collections()
            return True
        except Exception:
            return False

    def _build_filter(self, filters: list[MetadataFilter] | None):
        if not filters:
            return None
        from qdrant_client import models

        conditions: list[object] = []
        for item in filters:
            if item.operator == FilterOperator.EQUALS:
                conditions.append(models.FieldCondition(key=item.field, match=models.MatchValue(value=item.value)))
            elif item.operator == FilterOperator.NOT_EQUALS:
                conditions.append(
                    models.Filter(must_not=[models.FieldCondition(key=item.field, match=models.MatchValue(value=item.value))])
                )
            elif item.operator == FilterOperator.IN:
                conditions.append(models.FieldCondition(key=item.field, match=models.MatchAny(any=item.value)))
            elif item.operator == FilterOperator.NOT_IN:
                conditions.append(
                    models.Filter(must_not=[models.FieldCondition(key=item.field, match=models.MatchAny(any=item.value))])
                )
            elif item.operator in (FilterOperator.GT, FilterOperator.LT, FilterOperator.GTE, FilterOperator.LTE):
                conditions.append(models.FieldCondition(key=item.field, range=models.Range(**{item.operator.value: item.value})))
            elif item.operator == FilterOperator.EXISTS:
                if item.value:
                    conditions.append(models.FieldCondition(key=item.field, match=models.MatchExcept(**{"except": [None]})))
                else:
                    conditions.append(models.IsNullCondition(is_null=models.PayloadField(key=item.field)))
            elif item.operator in (FilterOperator.CONTAINS, FilterOperator.STARTS_WITH, FilterOperator.ENDS_WITH):
                conditions.append(models.FieldCondition(key=item.field, match=models.MatchText(text=str(item.value))))

        return models.Filter(must=conditions)
    