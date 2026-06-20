# tests/test_embeddings.py
from __future__ import annotations

import pytest

from embeddings.base_embedding import EmbeddingValidationError
from embeddings.embedding_factory import (
    EmbeddingProviderNotConfiguredError,
    get_embedding_provider,
    reset_provider_cache,
    resolve_embedding_dimension,
)
from settings import get_settings

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_provider_cache()
    yield
    reset_provider_cache()


class TestEmbeddingFactory:
    def test_unconfigured_provider_raises(self) -> None:
        settings = get_settings()
        with pytest.raises((EmbeddingProviderNotConfiguredError, KeyError, ValueError)):
            get_embedding_provider(settings=settings, provider_name="custom")

    def test_provider_cache_returns_same_instance(self) -> None:
        settings = get_settings()
        try:
            provider1 = get_embedding_provider(settings=settings, provider_name="sentence_transformers")
            provider2 = get_embedding_provider(settings=settings, provider_name="sentence_transformers")
            assert provider1 is provider2
        except ImportError:
            pytest.skip("sentence-transformers not installed")


class TestEmbeddingValidation:
    @pytest.mark.asyncio
    async def test_dimension_mismatch_rejected(self) -> None:
        settings = get_settings()
        try:
            provider = get_embedding_provider(settings=settings, provider_name="sentence_transformers")
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        with pytest.raises(EmbeddingValidationError):
            provider.validate_embeddings([[0.1, 0.2, 0.3]], model="all-mpnet-base-v2")

    def test_nan_vector_rejected(self) -> None:
        settings = get_settings()
        try:
            provider = get_embedding_provider(settings=settings, provider_name="sentence_transformers")
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        dimension = provider.get_dimension("all-MiniLM-L6-v2")
        bad_vector = [float("nan")] * dimension
        with pytest.raises(EmbeddingValidationError):
            provider.validate_embeddings([bad_vector], model="all-MiniLM-L6-v2")

    def test_zero_vector_rejected(self) -> None:
        settings = get_settings()
        try:
            provider = get_embedding_provider(settings=settings, provider_name="sentence_transformers")
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        dimension = provider.get_dimension("all-MiniLM-L6-v2")
        zero_vector = [0.0] * dimension
        with pytest.raises(EmbeddingValidationError):
            provider.validate_embeddings([zero_vector], model="all-MiniLM-L6-v2")


class TestSentenceTransformersEmbedding:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_embed_query_returns_correct_dimension(self) -> None:
        settings = get_settings()
        try:
            provider = get_embedding_provider(settings=settings, provider_name="sentence_transformers")
            vector = await provider.embed_query("test query", model="all-MiniLM-L6-v2")
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        assert len(vector) == 384
        assert all(isinstance(v, float) for v in vector)

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_embed_documents_batch(self) -> None:
        settings = get_settings()
        try:
            provider = get_embedding_provider(settings=settings, provider_name="sentence_transformers")
            vectors = await provider.embed_documents(["doc one", "doc two", "doc three"], model="all-MiniLM-L6-v2")
        except ImportError:
            pytest.skip("sentence-transformers not installed")

        assert len(vectors) == 3
        assert all(len(v) == 384 for v in vectors)


class TestResolveEmbeddingDimension:
    def test_resolves_known_model_dimension(self) -> None:
        settings = get_settings()
        try:
            dimension = resolve_embedding_dimension(settings, "sentence_transformers", "all-MiniLM-L6-v2")
        except ImportError:
            pytest.skip("sentence-transformers not installed")
        assert dimension == 384
