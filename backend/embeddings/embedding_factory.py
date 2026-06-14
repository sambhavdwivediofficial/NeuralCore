# embeddings/embedding_factory.py
from __future__ import annotations

from embeddings.base_embedding import BaseEmbeddingProvider, EmbeddingProviderError
from embeddings.bge import BGEEmbeddingProvider
from embeddings.custom import CustomEmbeddingProvider
from embeddings.e5 import E5EmbeddingProvider
from embeddings.jina import JinaEmbeddingProvider
from embeddings.nomic import NomicEmbeddingProvider
from embeddings.openai import OpenAIEmbeddingProvider
from embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider
from settings import EmbeddingProviderName, Settings

_PROVIDER_CLASSES: dict[EmbeddingProviderName, type[BaseEmbeddingProvider]] = {
    EmbeddingProviderName.OPENAI: OpenAIEmbeddingProvider,
    EmbeddingProviderName.BGE: BGEEmbeddingProvider,
    EmbeddingProviderName.E5: E5EmbeddingProvider,
    EmbeddingProviderName.JINA: JinaEmbeddingProvider,
    EmbeddingProviderName.NOMIC: NomicEmbeddingProvider,
    EmbeddingProviderName.SENTENCE_TRANSFORMERS: SentenceTransformersEmbeddingProvider,
    EmbeddingProviderName.CUSTOM: CustomEmbeddingProvider,
}

_provider_cache: dict[str, BaseEmbeddingProvider] = {}


class EmbeddingProviderNotConfiguredError(EmbeddingProviderError):
    def __init__(self, provider_name: str) -> None:
        super().__init__("Provider is not enabled or not configured", provider=provider_name)


def get_embedding_provider(settings: Settings, provider_name: str | None = None) -> BaseEmbeddingProvider:
    name = EmbeddingProviderName(provider_name or settings.embeddings.default_provider.value)

    if name.value in _provider_cache:
        return _provider_cache[name.value]

    config = settings.embeddings.providers.get(name.value)
    if config is None or not config.enabled:
        raise EmbeddingProviderNotConfiguredError(name.value)

    provider_class = _PROVIDER_CLASSES[name]
    instance = provider_class(config=config, settings=settings)
    _provider_cache[name.value] = instance
    return instance


def reset_provider_cache() -> None:
    _provider_cache.clear()


def resolve_embedding_dimension(settings: Settings, provider_name: str | None, model: str | None) -> int:
    provider = get_embedding_provider(settings, provider_name)
    return provider.get_dimension(model)
