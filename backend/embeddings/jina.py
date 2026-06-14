# embeddings/jina.py
from __future__ import annotations

import httpx

from embeddings.base_embedding import (
    BaseEmbeddingProvider,
    EmbeddingAuthenticationError,
    EmbeddingProviderUnavailableError,
    EmbeddingRateLimitError,
    EmbeddingValidationError,
)
from settings import EmbeddingProviderConfig, EmbeddingProviderName, Settings

_JINA_API_URL = "https://api.jina.ai/v1/embeddings"


class JinaEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = EmbeddingProviderName