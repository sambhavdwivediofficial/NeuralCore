# vector_stores/weaviate.py
from __future__ import annotations

from urllib.parse import urlparse

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
    DistanceMetric.COSINE: "cosine",
    DistanceMetric.DOT_PRODUCT: "dot",
    DistanceMetric.EUCLIDEAN: "l2-squared",
    DistanceMetric.MANHATTAN: "manhattan",
}


class WeaviateVectorStore(BaseVectorStore):
    backend_name = VectorDBBackend.WEAVIATE

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._config = settings.vector_db.weaviate
        self._client = None

    async def _get_client(self):
        if self._client is not None:
            return self._client

        import weaviate

        parsed = urlparse(self._config.url)
        secure = parsed.scheme == "https"
        auth = None
        if self._config.api_key is not None:
            from weaviate.auth import AuthApiKey

            auth = AuthApiKey(self._config.api_key.get_secret_value())

        self._client = weaviate.use_async_with_custom(
            http_host=parsed.hostname,
            http_port=parsed.port or (443 if secure else 80),
            http_secure=secure,
            grpc_host=parsed.hostname,
            grpc_port=50051,
            grpc_secure=secure,
            auth_credentials=auth,
        )
        await self._client.connect()
        return self._client

    @staticmethod
    def _class_name(collection_name: str) -> str:
        sanitized = "".join(part.capitalize() for part in collection_name.replace("-", "_").split("_"))
        return sanitized or "Collection"

    async def create_collection(
        self, collection_name: str, dimension: int, metric: DistanceMetric = DistanceMetric.COSINE
    ) -> None:
        from weaviate.classes.config import Configure, DataType, Property

        client = await self._get_client()
        await client.collections.create(
            name=self._class_name(collection_name),
            vectorizer_config=Configure.Vectorizer.none(),
            vector_index_config=Configure.VectorIndex.hnsw(distance_metric=_METRIC_MAP.get(metric, "cosine")),
            multi_tenancy_config=Configure.multi_tenancy(enabled=self._config.multi_tenancy),
            properties=[
                Property(name="chunk_id", data_type=DataType.TEXT),
                Property(name="metadata_json", data_type=DataType.TEXT),
            ],
        )

    async def delete_collection(self, collection_name: str) -> None:
        client = await self._get_client()
        await client.collections.delete(self._class_name(collection_name))

    async def collection_exists(self, collection_name: str) -> bool:
        client = await self._get_client()
        return await client.collections.exists(self._class_name(collection_name))

    async def upsert(self, collection_name: str, points) -> int:
        import json

        from weaviate.util import generate_uuid5

        normalized = self._normalize_points(points)
        client = await self._get_client()
        collection = client.collections.get(self._class_name(collection_name))

        async with collection.batch.dynamic() as batch:
            for point in normalized:
                await batch.add_object(
                    properties={"chunk_id": point.id, "metadata_json": json.dumps(point.metadata)},
                    uuid=generate_uuid5(point.id),
                    vector=point.vector,
                )
        return len(normalized)

    async def delete(self, collection_name: str, ids: list[str]) -> int:
        from weaviate.classes.query import Filter
        from weaviate.util import generate_uuid5

        client = await self._get_client()
        collection = client.collections.get(self._class_name(collection_name))
        uuids = [generate_uuid5(item_id) for item_id in ids]
        await collection.data.delete_many(where=Filter.by_id().contains_any(uuids))
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
        import json

        from weaviate.classes.query import MetadataQuery

        client = await self._get_client()
        if not await self.collection_exists(collection_name):
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)

        collection = client.collections.get(self._class_name(collection_name))
        where_filter = self._build_filter(filters)

        try:
            response = await collection.query.near_vector(
                near_vector=query_vector,
                limit=top_k,
                filters=where_filter,
                include_vector=with_vectors,
                return_metadata=MetadataQuery(distance=True),
            )
        except Exception as exc:
            raise VectorStoreConnectionError(str(exc), backend=self.backend_name.value) from exc

        results: list[VectorSearchResult] = []
        for obj in response.objects:
            distance = obj.metadata.distance or 0.0
            score = 1.0 - distance
            if score_threshold is not None and score < score_threshold:
                continue
            metadata = json.loads(obj.properties.get("metadata_json", "{}"))
            results.append(
                VectorSearchResult(
                    id=obj.properties.get("chunk_id", str(obj.uuid)),
                    score=score,
                    metadata=metadata,
                    vector=obj.vector.get("default") if with_vectors and obj.vector else None,
                )
            )
        return results

    async def get(self, collection_name: str, ids: list[str]) -> list[VectorPoint]:
        import json

        from weaviate.classes.query import Filter
        from weaviate.util import generate_uuid5

        client = await self._get_client()
        collection = client.collections.get(self._class_name(collection_name))
        uuids = [generate_uuid5(item_id) for item_id in ids]
        response = await collection.query.fetch_objects(filters=Filter.by_id().contains_any(uuids), include_vector=True)

        points: list[VectorPoint] = []
        for obj in response.objects:
            metadata = json.loads(obj.properties.get("metadata_json", "{}"))
            points.append(
                VectorPoint(
                    id=obj.properties.get("chunk_id", str(obj.uuid)),
                    vector=obj.vector.get("default", []) if obj.vector else [],
                    metadata=metadata,
                )
            )
        return points

    async def count(self, collection_name: str) -> int:
        client = await self._get_client()
        collection = client.collections.get(self._class_name(collection_name))
        response = await collection.aggregate.over_all(total_count=True)
        return response.total_count or 0

    async def health_check(self) -> bool:
        try:
            client = await self._get_client()
            return await client.is_ready()
        except Exception:
            return False

    def _build_filter(self, filters: list[MetadataFilter] | None):
        if not filters:
            return None
        from weaviate.classes.query import Filter

        conditions = []
        for item in filters:
            prop = Filter.by_property(item.field)
            if item.operator == FilterOperator.EQUALS:
                conditions.append(prop.equal(item.value))
            elif item.operator == FilterOperator.NOT_EQUALS:
                conditions.append(prop.not_equal(item.value))
            elif item.operator == FilterOperator.GT:
                conditions.append(prop.greater_than(item.value))
            elif item.operator == FilterOperator.LT:
                conditions.append(prop.less_than(item.value))
            elif item.operator == FilterOperator.GTE:
                conditions.append(prop.greater_or_equal(item.value))
            elif item.operator == FilterOperator.LTE:
                conditions.append(prop.less_or_equal(item.value))
            elif item.operator == FilterOperator.IN:
                conditions.append(prop.contains_any(item.value))
            elif item.operator == FilterOperator.CONTAINS:
                conditions.append(prop.like(f"*{item.value}*"))
            elif item.operator == FilterOperator.STARTS_WITH:
                conditions.append(prop.like(f"{item.value}*"))
            elif item.operator == FilterOperator.ENDS_WITH:
                conditions.append(prop.like(f"*{item.value}"))

        if not conditions:
            return None
        combined = conditions[0]
        for condition in conditions[1:]:
            combined = combined & condition
        return combined
    