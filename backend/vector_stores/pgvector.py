# vector_stores/pgvector.py
from __future__ import annotations

import json

from sqlalchemy import text

from database.connection import get_engine
from settings import DistanceMetric, Settings, VectorDBBackend
from vector_stores.base import (
    BaseVectorStore,
    CollectionNotFoundError,
    FilterOperator,
    MetadataFilter,
    VectorPoint,
    VectorSearchResult,
)

_OPERATOR_MAP = {
    DistanceMetric.COSINE: "<=>",
    DistanceMetric.DOT_PRODUCT: "<#>",
    DistanceMetric.EUCLIDEAN: "<->",
    DistanceMetric.MANHATTAN: "<->",
}


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _parse_pgvector(raw) -> list[float]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [float(item) for item in raw.strip("[]").split(",") if item]
    return list(raw)


class PGVectorStore(BaseVectorStore):
    backend_name = VectorDBBackend.PGVECTOR

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._config = settings.vector_db.pgvector

    @staticmethod
    def _table_name(collection_name: str) -> str:
        sanitized = "".join(char if char.isalnum() or char == "_" else "_" for char in collection_name.lower())
        return f"vec_{sanitized}"

    async def create_collection(
        self, collection_name: str, dimension: int, metric: DistanceMetric = DistanceMetric.COSINE
    ) -> None:
        table = self._table_name(collection_name)
        engine = get_engine()
        operator_class = (
            "vector_cosine_ops"
            if metric == DistanceMetric.COSINE
            else "vector_ip_ops"
            if metric == DistanceMetric.DOT_PRODUCT
            else "vector_l2_ops"
        )

        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.execute(
                text(
                    f'CREATE TABLE IF NOT EXISTS "{table}" '
                    f"(id TEXT PRIMARY KEY, embedding vector({dimension}), metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb)"
                )
            )
            if self._config.index_type == "hnsw":
                await conn.execute(
                    text(
                        f'CREATE INDEX IF NOT EXISTS "{table}_hnsw_idx" ON "{table}" '
                        f"USING hnsw (embedding {operator_class}) "
                        f"WITH (m = {self._config.hnsw_m}, ef_construction = {self._config.hnsw_ef_construction})"
                    )
                )
            else:
                await conn.execute(
                    text(
                        f'CREATE INDEX IF NOT EXISTS "{table}_ivfflat_idx" ON "{table}" '
                        f"USING ivfflat (embedding {operator_class}) WITH (lists = {self._config.lists})"
                    )
                )
            await conn.execute(text(f'CREATE INDEX IF NOT EXISTS "{table}_metadata_idx" ON "{table}" USING gin (metadata)'))

    async def delete_collection(self, collection_name: str) -> None:
        table = self._table_name(collection_name)
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{table}"'))

    async def collection_exists(self, collection_name: str) -> bool:
        table = self._table_name(collection_name)
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT to_regclass(:table)"), {"table": table})
            return result.scalar() is not None

    async def upsert(self, collection_name: str, points) -> int:
        normalized = self._normalize_points(points)
        table = self._table_name(collection_name)
        engine = get_engine()
        async with engine.begin() as conn:
            for point in normalized:
                await conn.execute(
                    text(
                        f'INSERT INTO "{table}" (id, embedding, metadata) VALUES (:id, :embedding, :metadata) '
                        f"ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding, metadata = EXCLUDED.metadata"
                    ),
                    {"id": point.id, "embedding": str(point.vector), "metadata": json.dumps(point.metadata)},
                )
        return len(normalized)

    async def delete(self, collection_name: str, ids: list[str]) -> int:
        table = self._table_name(collection_name)
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text(f'DELETE FROM "{table}" WHERE id = ANY(:ids)'), {"ids": ids})
        return result.rowcount or 0

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: list[MetadataFilter] | None = None,
        with_vectors: bool = False,
        score_threshold: float | None = None,
    ) -> list[VectorSearchResult]:
        table = self._table_name(collection_name)
        engine = get_engine()

        if not await self.collection_exists(collection_name):
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)

        operator = _OPERATOR_MAP.get(self._config.metric, "<=>")
        where_clause, params = self._build_filter(filters)
        params.update({"query_vector": str(query_vector), "top_k": top_k})

        vector_select = ", embedding" if with_vectors else ""
        sql = (
            f'SELECT id, metadata{vector_select}, 1 - (embedding {operator} (:query_vector)::vector) AS score '
            f'FROM "{table}" {where_clause} '
            f"ORDER BY embedding {operator} (:query_vector)::vector LIMIT :top_k"
        )

        async with engine.connect() as conn:
            result = await conn.execute(text(sql), params)
            rows = result.mappings().all()

        results: list[VectorSearchResult] = []
        for row in rows:
            score = float(row["score"])
            if score_threshold is not None and score < score_threshold:
                continue
            vector = _parse_pgvector(row["embedding"]) if with_vectors and "embedding" in row else None
            results.append(VectorSearchResult(id=row["id"], score=score, metadata=row["metadata"] or {}, vector=vector))
        return results

    async def get(self, collection_name: str, ids: list[str]) -> list[VectorPoint]:
        table = self._table_name(collection_name)
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text(f'SELECT id, embedding, metadata FROM "{table}" WHERE id = ANY(:ids)'), {"ids": ids})
            rows = result.mappings().all()
        return [VectorPoint(id=row["id"], vector=_parse_pgvector(row["embedding"]), metadata=row["metadata"] or {}) for row in rows]

    async def count(self, collection_name: str) -> int:
        table = self._table_name(collection_name)
        engine = get_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            return int(result.scalar() or 0)

    async def health_check(self) -> bool:
        engine = get_engine()
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    @staticmethod
    def _build_filter(filters: list[MetadataFilter] | None) -> tuple[str, dict]:
        if not filters:
            return "", {}

        clauses: list[str] = []
        params: dict[str, object] = {}
        for index, item in enumerate(filters):
            key = f"filter_{index}"
            path = f"metadata->>{_sql_literal(item.field)}"
            if item.operator == FilterOperator.EQUALS:
                clauses.append(f"{path} = :{key}")
                params[key] = str(item.value)
            elif item.operator == FilterOperator.NOT_EQUALS:
                clauses.append(f"{path} != :{key}")
                params[key] = str(item.value)
            elif item.operator == FilterOperator.GT:
                clauses.append(f"({path})::numeric > :{key}")
                params[key] = item.value
            elif item.operator == FilterOperator.LT:
                clauses.append(f"({path})::numeric < :{key}")
                params[key] = item.value
            elif item.operator == FilterOperator.GTE:
                clauses.append(f"({path})::numeric >= :{key}")
                params[key] = item.value
            elif item.operator == FilterOperator.LTE:
                clauses.append(f"({path})::numeric <= :{key}")
                params[key] = item.value
            elif item.operator == FilterOperator.IN:
                clauses.append(f"{path} = ANY(:{key})")
                params[key] = [str(value) for value in item.value]
            elif item.operator == FilterOperator.NOT_IN:
                clauses.append(f"{path} != ALL(:{key})")
                params[key] = [str(value) for value in item.value]
            elif item.operator == FilterOperator.CONTAINS:
                clauses.append(f"{path} LIKE :{key}")
                params[key] = f"%{item.value}%"
            elif item.operator == FilterOperator.STARTS_WITH:
                clauses.append(f"{path} LIKE :{key}")
                params[key] = f"{item.value}%"
            elif item.operator == FilterOperator.ENDS_WITH:
                clauses.append(f"{path} LIKE :{key}")
                params[key] = f"%{item.value}"
            elif item.operator == FilterOperator.EXISTS:
                if item.value:
                    clauses.append(f"metadata ? {_sql_literal(item.field)}")
                else:
                    clauses.append(f"NOT (metadata ? {_sql_literal(item.field)})")

        where_clause = "WHERE " + " AND ".join(clauses) if clauses else ""
        return where_clause, params
    