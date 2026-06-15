# vector_stores/elastic.py
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
    DistanceMetric.COSINE: "cosine",
    DistanceMetric.DOT_PRODUCT: "dot_product",
    DistanceMetric.EUCLIDEAN: "l2_norm",
    DistanceMetric.MANHATTAN: "l2_norm",
}


class ElasticsearchVectorStore(BaseVectorStore):
    backend_name = VectorDBBackend.ELASTICSEARCH

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        from elasticsearch import AsyncElasticsearch

        self._config = settings.vector_db.elasticsearch
        self._client = AsyncElasticsearch(
            hosts=self._config.hosts,
            api_key=self._config.api_key.get_secret_value() if self._config.api_key else None,
        )

    def _index_name(self, collection_name: str) -> str:
        return f"{self._config.index_prefix}_{collection_name}".lower()

    async def create_collection(
        self, collection_name: str, dimension: int, metric: DistanceMetric = DistanceMetric.COSINE
    ) -> None:
        await self._client.indices.create(
            index=self._index_name(collection_name),
            mappings={
                "properties": {
                    "vector": {
                        "type": "dense_vector",
                        "dims": dimension,
                        "index": True,
                        "similarity": _METRIC_MAP.get(metric, "cosine"),
                        "index_options": {
                            "type": "hnsw",
                            "m": self._config.hnsw_m,
                            "ef_construction": self._config.hnsw_ef_construction,
                        },
                    },
                    "metadata": {"type": "object", "enabled": True},
                }
            },
        )

    async def delete_collection(self, collection_name: str) -> None:
        await self._client.indices.delete(index=self._index_name(collection_name), ignore_unavailable=True)

    async def collection_exists(self, collection_name: str) -> bool:
        return await self._client.indices.exists(index=self._index_name(collection_name))

    async def upsert(self, collection_name: str, points) -> int:
        from elasticsearch.helpers import async_bulk

        normalized = self._normalize_points(points)
        index = self._index_name(collection_name)
        actions = [
            {"_op_type": "index", "_index": index, "_id": point.id, "vector": point.vector, "metadata": point.metadata}
            for point in normalized
        ]
        await async_bulk(self._client, actions)
        return len(normalized)

    async def delete(self, collection_name: str, ids: list[str]) -> int:
        from elasticsearch.helpers import async_bulk

        index = self._index_name(collection_name)
        actions = [{"_op_type": "delete", "_index": index, "_id": item_id} for item_id in ids]
        await async_bulk(self._client, actions, raise_on_error=False)
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
        index = self._index_name(collection_name)
        if not await self.collection_exists(collection_name):
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)

        knn: dict[str, object] = {
            "field": "vector",
            "query_vector": query_vector,
            "k": top_k,
            "num_candidates": max(top_k * 10, 100),
        }
        query_filter = self._build_filter(filters)
        if query_filter:
            knn["filter"] = query_filter

        try:
            response = await self._client.search(
                index=index,
                knn=knn,
                size=top_k,
                source=not with_vectors,
                fields=["metadata", "vector"] if with_vectors else ["metadata"],
            )
        except Exception as exc:
            raise VectorStoreConnectionError(str(exc), backend=self.backend_name.value) from exc

        results: list[VectorSearchResult] = []
        for hit in response["hits"]["hits"]:
            score = hit["_score"]
            if score_threshold is not None and score < score_threshold:
                continue
            source = hit.get("_source", {})
            results.append(
                VectorSearchResult(
                    id=hit["_id"],
                    score=score,
                    metadata=source.get("metadata", {}),
                    vector=source.get("vector") if with_vectors else None,
                )
            )
        return results

    async def get(self, collection_name: str, ids: list[str]) -> list[VectorPoint]:
        response = await self._client.mget(index=self._index_name(collection_name), ids=ids)
        points: list[VectorPoint] = []
        for doc in response["docs"]:
            if not doc.get("found"):
                continue
            source = doc["_source"]
            points.append(VectorPoint(id=doc["_id"], vector=source.get("vector", []), metadata=source.get("metadata", {})))
        return points

    async def count(self, collection_name: str) -> int:
        response = await self._client.count(index=self._index_name(collection_name))
        return response["count"]

    async def health_check(self) -> bool:
        try:
            health = await self._client.cluster.health()
            return health["status"] in ("green", "yellow")
        except Exception:
            return False

    @staticmethod
    def _build_filter(filters: list[MetadataFilter] | None):
        if not filters:
            return None

        must: list[dict] = []
        must_not: list[dict] = []
        for item in filters:
            field = f"metadata.{item.field}"
            if item.operator == FilterOperator.EQUALS:
                must.append({"term": {field: item.value}})
            elif item.operator == FilterOperator.NOT_EQUALS:
                must_not.append({"term": {field: item.value}})
            elif item.operator == FilterOperator.GT:
                must.append({"range": {field: {"gt": item.value}}})
            elif item.operator == FilterOperator.LT:
                must.append({"range": {field: {"lt": item.value}}})
            elif item.operator == FilterOperator.GTE:
                must.append({"range": {field: {"gte": item.value}}})
            elif item.operator == FilterOperator.LTE:
                must.append({"range": {field: {"lte": item.value}}})
            elif item.operator == FilterOperator.IN:
                must.append({"terms": {field: item.value}})
            elif item.operator == FilterOperator.NOT_IN:
                must_not.append({"terms": {field: item.value}})
            elif item.operator == FilterOperator.CONTAINS:
                must.append({"wildcard": {field: f"*{item.value}*"}})
            elif item.operator == FilterOperator.STARTS_WITH:
                must.append({"prefix": {field: str(item.value)}})
            elif item.operator == FilterOperator.ENDS_WITH:
                must.append({"wildcard": {field: f"*{item.value}"}})
            elif item.operator == FilterOperator.EXISTS:
                (must if item.value else must_not).append({"exists": {"field": field}})

        return {"bool": {"must": must, "must_not": must_not}}
    