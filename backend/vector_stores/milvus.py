# vector_stores/milvus.py
from __future__ import annotations

import asyncio

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
    DistanceMetric.COSINE: "COSINE",
    DistanceMetric.DOT_PRODUCT: "IP",
    DistanceMetric.EUCLIDEAN: "L2",
    DistanceMetric.MANHATTAN: "L2",
}


def _milvus_literal(value: object) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def _milvus_list(value: list) -> str:
    return "[" + ", ".join(_milvus_literal(item) for item in value) + "]"


class MilvusVectorStore(BaseVectorStore):
    backend_name = VectorDBBackend.MILVUS

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        from pymilvus import MilvusClient

        self._config = settings.vector_db.milvus
        self._client = MilvusClient(uri=f"http://{self._config.host}:{self._config.port}")

    async def create_collection(
        self, collection_name: str, dimension: int, metric: DistanceMetric = DistanceMetric.COSINE
    ) -> None:
        await asyncio.to_thread(self._create_collection_sync, collection_name, dimension, metric)

    def _create_collection_sync(self, collection_name: str, dimension: int, metric: DistanceMetric) -> None:
        from pymilvus import DataType

        index_params = self._client.prepare_index_params()
        params = (
            {"M": self._config.hnsw_m, "efConstruction": self._config.hnsw_ef_construct}
            if self._config.index_type == "HNSW"
            else {"nlist": self._config.nlist}
        )
        index_params.add_index(
            field_name="vector",
            index_type=self._config.index_type,
            metric_type=_METRIC_MAP.get(metric, "COSINE"),
            params=params,
        )

        self._client.create_collection(
            collection_name=collection_name,
            dimension=dimension,
            primary_field_name="id",
            id_type=DataType.VARCHAR,
            max_length=64,
            vector_field_name="vector",
            metric_type=_METRIC_MAP.get(metric, "COSINE"),
            index_params=index_params,
            auto_id=False,
        )

    async def delete_collection(self, collection_name: str) -> None:
        await asyncio.to_thread(self._client.drop_collection, collection_name)

    async def collection_exists(self, collection_name: str) -> bool:
        return await asyncio.to_thread(self._client.has_collection, collection_name)

    async def upsert(self, collection_name: str, points) -> int:
        normalized = self._normalize_points(points)
        rows = [{"id": point.id, "vector": point.vector, **point.metadata} for point in normalized]
        await asyncio.to_thread(self._client.upsert, collection_name, rows)
        return len(normalized)

    async def delete(self, collection_name: str, ids: list[str]) -> int:
        formatted = ", ".join(f'"{item_id}"' for item_id in ids)
        await asyncio.to_thread(self._client.delete, collection_name, filter=f"id in [{formatted}]")
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
        if not await self.collection_exists(collection_name):
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)

        filter_expr = self._build_filter_expression(filters)
        try:
            results = await asyncio.to_thread(
                self._client.search,
                collection_name=collection_name,
                data=[query_vector],
                limit=top_k,
                filter=filter_expr or "",
                output_fields=["*"],
            )
        except Exception as exc:
            raise VectorStoreConnectionError(str(exc), backend=self.backend_name.value) from exc

        search_results: list[VectorSearchResult] = []
        for hit in results[0] if results else []:
            score = float(hit.get("distance", 0.0))
            if score_threshold is not None and score < score_threshold:
                continue
            entity = hit.get("entity", {})
            metadata = {key: value for key, value in entity.items() if key not in ("id", "vector")}
            search_results.append(
                VectorSearchResult(
                    id=str(hit.get("id")),
                    score=score,
                    metadata=metadata,
                    vector=entity.get("vector") if with_vectors else None,
                )
            )
        return search_results

    async def get(self, collection_name: str, ids: list[str]) -> list[VectorPoint]:
        results = await asyncio.to_thread(self._client.get, collection_name=collection_name, ids=ids)
        points: list[VectorPoint] = []
        for item in results:
            item = dict(item)
            vector = item.pop("vector", [])
            item_id = item.pop("id")
            points.append(VectorPoint(id=str(item_id), vector=vector, metadata=item))
        return points

    async def count(self, collection_name: str) -> int:
        stats = await asyncio.to_thread(self._client.get_collection_stats, collection_name)
        return int(stats.get("row_count", 0))

    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self._client.list_collections)
            return True
        except Exception:
            return False

    @staticmethod
    def _build_filter_expression(filters: list[MetadataFilter] | None) -> str | None:
        if not filters:
            return None

        expressions: list[str] = []
        for item in filters:
            field, value = item.field, item.value
            if item.operator == FilterOperator.EQUALS:
                expressions.append(f"{field} == {_milvus_literal(value)}")
            elif item.operator == FilterOperator.NOT_EQUALS:
                expressions.append(f"{field} != {_milvus_literal(value)}")
            elif item.operator == FilterOperator.GT:
                expressions.append(f"{field} > {_milvus_literal(value)}")
            elif item.operator == FilterOperator.LT:
                expressions.append(f"{field} < {_milvus_literal(value)}")
            elif item.operator == FilterOperator.GTE:
                expressions.append(f"{field} >= {_milvus_literal(value)}")
            elif item.operator == FilterOperator.LTE:
                expressions.append(f"{field} <= {_milvus_literal(value)}")
            elif item.operator == FilterOperator.IN:
                expressions.append(f"{field} in {_milvus_list(value)}")
            elif item.operator == FilterOperator.NOT_IN:
                expressions.append(f"{field} not in {_milvus_list(value)}")
            elif item.operator == FilterOperator.CONTAINS:
                expressions.append(f'{field} like "%{value}%"')
            elif item.operator == FilterOperator.STARTS_WITH:
                expressions.append(f'{field} like "{value}%"')
            elif item.operator == FilterOperator.ENDS_WITH:
                expressions.append(f'{field} like "%{value}"')
            elif item.operator == FilterOperator.EXISTS:
                expressions.append(f"{field} is not null" if value else f"{field} is null")

        return " and ".join(expressions) if expressions else None
    