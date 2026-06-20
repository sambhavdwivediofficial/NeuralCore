# tests/test_retrieval.py
from __future__ import annotations

import pytest

from retrieval.bm25 import BM25Index
from retrieval.hybrid_retriever import _reciprocal_rank_fusion
from retrieval.metadata_search import apply_metadata_filters_in_memory, build_metadata_filters, validate_filter_spec
from retrieval.query_rewriter import rewrite_all_enabled
from vector_stores.base import FilterOperator, MetadataFilter

pytestmark = pytest.mark.unit


class TestBM25Index:
    def test_search_ranks_relevant_documents_higher(self) -> None:
        index = BM25Index()
        index.add("doc1", "NeuralCore is an enterprise AI RAG platform with hybrid retrieval")
        index.add("doc2", "Python is a programming language used for machine learning")
        index.add("doc3", "Vector databases store embeddings for semantic similarity search")

        results = index.search("vector search RAG", top_k=3)
        result_ids = [r.id for r in results]
        assert "doc1" in result_ids or "doc3" in result_ids

    def test_empty_query_returns_empty(self) -> None:
        index = BM25Index()
        index.add("doc1", "some content here")
        results = index.search("", top_k=5)
        assert results == []

    def test_remove_updates_results(self) -> None:
        index = BM25Index()
        index.add("doc1", "unique searchable content about robots")
        results_before = index.search("robots", top_k=5)
        assert len(results_before) == 1

        index.remove("doc1")
        results_after = index.search("robots", top_k=5)
        assert len(results_after) == 0

    def test_index_length(self) -> None:
        index = BM25Index()
        assert len(index) == 0
        index.add("doc1", "test content")
        assert len(index) == 1

    def test_batch_add(self) -> None:
        index = BM25Index()
        index.add_batch([
            {"id": "d1", "text": "first document about cats"},
            {"id": "d2", "text": "second document about dogs"},
        ])
        assert len(index) == 2


class TestReciprocalRankFusion:
    def test_fuses_two_ranked_lists(self) -> None:
        list_a = [("doc1", 0.9), ("doc2", 0.8), ("doc3", 0.7)]
        list_b = [("doc2", 0.95), ("doc1", 0.85), ("doc4", 0.6)]
        fused = _reciprocal_rank_fusion([list_a, list_b], k=60)
        fused_ids = [item[0] for item in fused]
        assert "doc1" in fused_ids
        assert "doc2" in fused_ids
        assert len(fused) == 4

    def test_weighted_fusion(self) -> None:
        list_a = [("doc1", 1.0)]
        list_b = [("doc2", 1.0)]
        fused = _reciprocal_rank_fusion([list_a, list_b], k=60, weights=[2.0, 0.5])
        assert fused[0][0] == "doc1"


class TestMetadataFilters:
    def test_build_filters_from_spec(self) -> None:
        spec = {"department__equals": "engineering", "year__gte": 2024}
        filters = build_metadata_filters(spec)
        assert len(filters) == 2
        assert any(f.field == "department" and f.operator == FilterOperator.EQUALS for f in filters)
        assert any(f.field == "year" and f.operator == FilterOperator.GTE for f in filters)

    def test_validate_filter_spec_catches_bad_operator(self) -> None:
        errors = validate_filter_spec({"field__invalid_op": "value"})
        assert len(errors) > 0

    def test_apply_filters_in_memory(self) -> None:
        documents = [
            {"metadata": {"category": "tech"}},
            {"metadata": {"category": "sports"}},
        ]
        filters = [MetadataFilter(field="category", operator=FilterOperator.EQUALS, value="tech")]
        filtered = apply_metadata_filters_in_memory(documents, filters)
        assert len(filtered) == 1
        assert filtered[0]["metadata"]["category"] == "tech"

    def test_exists_operator(self) -> None:
        documents = [{"metadata": {"tag": "x"}}, {"metadata": {}}]
        filters = [MetadataFilter(field="tag", operator=FilterOperator.EXISTS, value=True)]
        filtered = apply_metadata_filters_in_memory(documents, filters)
        assert len(filtered) == 1


class TestQueryRewriting:
    @pytest.mark.asyncio
    async def test_rewrite_disabled_returns_original(self) -> None:
        from settings import get_settings

        settings = get_settings()
        settings.retrieval.query_rewriting.hyde_enabled = False
        settings.retrieval.query_rewriting.step_back_enabled = False
        settings.retrieval.query_rewriting.expansion_enabled = False
        settings.retrieval.query_rewriting.decomposition_enabled = False

        result = await rewrite_all_enabled("what is RAG", settings)
        assert result["original"] == "what is RAG"
