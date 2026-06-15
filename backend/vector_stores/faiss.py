# vector_stores/faiss.py
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from settings import DistanceMetric, Settings, VectorDBBackend
from vector_stores.base import (
    BaseVectorStore,
    CollectionNotFoundError,
    FilterOperator,
    MetadataFilter,
    VectorPoint,
    VectorSearchResult,
)


class FaissVectorStore(BaseVectorStore):
    backend_name = VectorDBBackend.FAISS

    def __init__(self, settings: Settings) -> None:
        super().__init__(settings)
        self._config = settings.vector_db.faiss
        self._storage_path = Path(self._config.storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._locks: dict[str, asyncio.Lock] = {}
        self._cache: dict[str, dict] = {}

    def _get_lock(self, collection_name: str) -> asyncio.Lock:
        if collection_name not in self._locks:
            self._locks[collection_name] = asyncio.Lock()
        return self._locks[collection_name]

    def _index_path(self, collection_name: str) -> Path:
        return self._storage_path / f"{collection_name}.index"

    def _meta_path(self, collection_name: str) -> Path:
        return self._storage_path / f"{collection_name}.meta.json"

    def _load_state(self, collection_name: str) -> dict | None:
        if collection_name in self._cache:
            return self._cache[collection_name]

        meta_path = self._meta_path(collection_name)
        index_path = self._index_path(collection_name)
        if not meta_path.exists() or not index_path.exists():
            return None

        import faiss

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        state = {
            "index": faiss.read_index(str(index_path)),
            "dimension": meta["dimension"],
            "metric": meta["metric"],
            "id_to_internal": {key: int(value) for key, value in meta["id_to_internal"].items()},
            "internal_to_id": {int(key): value for key, value in meta["internal_to_id"].items()},
            "metadata": meta["metadata"],
            "next_internal_id": meta["next_internal_id"],
        }
        self._cache[collection_name] = state
        return state

    def _save_state(self, collection_name: str, state: dict) -> None:
        import faiss

        faiss.write_index(state["index"], str(self._index_path(collection_name)))
        meta = {
            "dimension": state["dimension"],
            "metric": state["metric"],
            "id_to_internal": state["id_to_internal"],
            "internal_to_id": {str(key): value for key, value in state["internal_to_id"].items()},
            "metadata": state["metadata"],
            "next_internal_id": state["next_internal_id"],
        }
        self._meta_path(collection_name).write_text(json.dumps(meta), encoding="utf-8")
        self._cache[collection_name] = state

    def _build_index(self, dimension: int, metric: DistanceMetric):
        import faiss

        is_inner_product = metric in (DistanceMetric.COSINE, DistanceMetric.DOT_PRODUCT)
        quantizer = faiss.IndexFlatIP(dimension) if is_inner_product else faiss.IndexFlatL2(dimension)
        nlist = max(1, self._config.nlist)
        metric_type = faiss.METRIC_INNER_PRODUCT if is_inner_product else faiss.METRIC_L2
        index = faiss.IndexIVFFlat(quantizer, dimension, nlist, metric_type)
        return faiss.IndexIDMap2(index)

    async def create_collection(
        self, collection_name: str, dimension: int, metric: DistanceMetric = DistanceMetric.COSINE
    ) -> None:
        async with self._get_lock(collection_name):
            await asyncio.to_thread(self._create_collection_sync, collection_name, dimension, metric)

    def _create_collection_sync(self, collection_name: str, dimension: int, metric: DistanceMetric) -> None:
        state = {
            "index": self._build_index(dimension, metric),
            "dimension": dimension,
            "metric": metric.value,
            "id_to_internal": {},
            "internal_to_id": {},
            "metadata": {},
            "next_internal_id": 0,
        }
        self._save_state(collection_name, state)

    async def delete_collection(self, collection_name: str) -> None:
        async with self._get_lock(collection_name):
            self._cache.pop(collection_name, None)
            self._index_path(collection_name).unlink(missing_ok=True)
            self._meta_path(collection_name).unlink(missing_ok=True)

    async def collection_exists(self, collection_name: str) -> bool:
        return self._index_path(collection_name).exists() and self._meta_path(collection_name).exists()

    async def upsert(self, collection_name: str, points) -> int:
        normalized = self._normalize_points(points)
        async with self._get_lock(collection_name):
            return await asyncio.to_thread(self._upsert_sync, collection_name, normalized)

    def _upsert_sync(self, collection_name: str, points: list[VectorPoint]) -> int:
        import faiss
        import numpy as np

        state = self._load_state(collection_name)
        if state is None:
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)

        index = state["index"]
        vectors = []
        internal_ids = []
        for point in points:
            if point.id in state["id_to_internal"]:
                old_internal_id = state["id_to_internal"][point.id]
                if index.index.is_trained:
                    index.remove_ids(np.array([old_internal_id], dtype=np.int64))
                internal_id = old_internal_id
            else:
                internal_id = state["next_internal_id"]
                state["next_internal_id"] += 1
            state["id_to_internal"][point.id] = internal_id
            state["internal_to_id"][internal_id] = point.id
            state["metadata"][point.id] = point.metadata
            vectors.append(point.vector)
            internal_ids.append(internal_id)

        vector_array = np.array(vectors, dtype=np.float32)
        if state["metric"] in (DistanceMetric.COSINE.value, DistanceMetric.DOT_PRODUCT.value):
            faiss.normalize_L2(vector_array)

        if not index.index.is_trained and vector_array.shape[0] >= getattr(index.index, "nlist", 1):
            index.index.train(vector_array)

        if index.index.is_trained:
            index.add_with_ids(vector_array, np.array(internal_ids, dtype=np.int64))
            try:
                index.index.make_direct_map()
            except RuntimeError:
                pass

        self._save_state(collection_name, state)
        return len(points)

    async def delete(self, collection_name: str, ids: list[str]) -> int:
        async with self._get_lock(collection_name):
            return await asyncio.to_thread(self._delete_sync, collection_name, ids)

    def _delete_sync(self, collection_name: str, ids: list[str]) -> int:
        import numpy as np

        state = self._load_state(collection_name)
        if state is None:
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)

        internal_ids = []
        removed = 0
        for item_id in ids:
            internal_id = state["id_to_internal"].pop(item_id, None)
            if internal_id is not None:
                state["internal_to_id"].pop(internal_id, None)
                state["metadata"].pop(item_id, None)
                internal_ids.append(internal_id)
                removed += 1

        if internal_ids and state["index"].index.is_trained:
            state["index"].remove_ids(np.array(internal_ids, dtype=np.int64))

        self._save_state(collection_name, state)
        return removed

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: list[MetadataFilter] | None = None,
        with_vectors: bool = False,
        score_threshold: float | None = None,
    ) -> list[VectorSearchResult]:
        async with self._get_lock(collection_name):
            return await asyncio.to_thread(
                self._search_sync, collection_name, query_vector, top_k, filters, score_threshold
            )

    def _search_sync(self, collection_name, query_vector, top_k, filters, score_threshold) -> list[VectorSearchResult]:
        import faiss
        import numpy as np

        state = self._load_state(collection_name)
        if state is None:
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)

        index = state["index"]
        if not index.index.is_trained or index.index.ntotal == 0:
            return []

        query = np.array([query_vector], dtype=np.float32)
        if state["metric"] in (DistanceMetric.COSINE.value, DistanceMetric.DOT_PRODUCT.value):
            faiss.normalize_L2(query)

        index.index.nprobe = min(getattr(index.index, "nlist", 1), 32)
        search_k = min(top_k * 4, index.index.ntotal) if filters else top_k
        scores, internal_ids = index.search(query, max(search_k, 1))

        results: list[VectorSearchResult] = []
        for score, internal_id in zip(scores[0], internal_ids[0]):
            if internal_id == -1:
                continue
            point_id = state["internal_to_id"].get(int(internal_id))
            if point_id is None:
                continue
            metadata = state["metadata"].get(point_id, {})
            if filters and not self._matches_filters(metadata, filters):
                continue
            if score_threshold is not None and float(score) < score_threshold:
                continue
            results.append(VectorSearchResult(id=point_id, score=float(score), metadata=metadata))
            if len(results) >= top_k:
                break
        return results

    @staticmethod
    def _matches_filters(metadata: dict, filters: list[MetadataFilter]) -> bool:
        for item in filters:
            value = metadata.get(item.field)
            operator = item.operator
            if operator == FilterOperator.EQUALS and value != item.value:
                return False
            if operator == FilterOperator.NOT_EQUALS and value == item.value:
                return False
            if operator == FilterOperator.GT and not (value is not None and value > item.value):
                return False
            if operator == FilterOperator.LT and not (value is not None and value < item.value):
                return False
            if operator == FilterOperator.GTE and not (value is not None and value >= item.value):
                return False
            if operator == FilterOperator.LTE and not (value is not None and value <= item.value):
                return False
            if operator == FilterOperator.IN and value not in item.value:
                return False
            if operator == FilterOperator.NOT_IN and value in item.value:
                return False
            if operator == FilterOperator.CONTAINS and (value is None or str(item.value) not in str(value)):
                return False
            if operator == FilterOperator.STARTS_WITH and (value is None or not str(value).startswith(str(item.value))):
                return False
            if operator == FilterOperator.ENDS_WITH and (value is None or not str(value).endswith(str(item.value))):
                return False
            if operator == FilterOperator.EXISTS and (item.field in metadata) != bool(item.value):
                return False
        return True

    async def get(self, collection_name: str, ids: list[str]) -> list[VectorPoint]:
        async with self._get_lock(collection_name):
            return await asyncio.to_thread(self._get_sync, collection_name, ids)

    def _get_sync(self, collection_name: str, ids: list[str]) -> list[VectorPoint]:
        import numpy as np

        state = self._load_state(collection_name)
        if state is None:
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)

        points: list[VectorPoint] = []
        for item_id in ids:
            internal_id = state["id_to_internal"].get(item_id)
            if internal_id is None:
                continue
            vector = state["index"].index.reconstruct(internal_id)
            points.append(VectorPoint(id=item_id, vector=np.asarray(vector).tolist(), metadata=state["metadata"].get(item_id, {})))
        return points

    async def count(self, collection_name: str) -> int:
        state = self._load_state(collection_name)
        if state is None:
            raise CollectionNotFoundError(f"collection '{collection_name}' does not exist", backend=self.backend_name.value)
        return state["index"].index.ntotal

    async def health_check(self) -> bool:
        return os.access(self._storage_path, os.W_OK)
    