# embeddings/base_embedding.py
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any

from settings import EmbeddingProviderConfig, EmbeddingProviderName, Settings


class EmbeddingProviderError(Exception):
    def __init__(self, message: str, provider: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class EmbeddingAuthenticationError(EmbeddingProviderError):
    pass


class EmbeddingRateLimitError(EmbeddingProviderError):
    pass


class EmbeddingProviderUnavailableError(EmbeddingProviderError):
    pass


class EmbeddingValidationError(EmbeddingProviderError):
    pass


class BaseEmbeddingProvider(ABC):
    provider_name: EmbeddingProviderName

    def __init__(self, config: EmbeddingProviderConfig, settings: Settings) -> None:
        self.config = config
        self.settings = settings

    @abstractmethod
    async def embed_documents(self, texts: list[str], model: str | None = None) -> list[list[float]]: ...

    async def embed_query(self, text: str, model: str | None = None) -> list[float]:
        embeddings = await self.embed_documents([text], model=model)
        return embeddings[0]

    def resolve_model(self, model: str | None) -> str:
        return model or self.config.default_model

    def get_model_info(self, model: str | None = None) -> dict[str, Any]:
        return self.config.models.get(self.resolve_model(model), {})

    def get_dimension(self, model: str | None = None) -> int:
        info = self.get_model_info(model)
        dimension = info.get("dimension", self.config.dimension)
        if dimension is None:
            raise EmbeddingValidationError("dimension is not configured for this model", provider=self.provider_name.value)
        return int(dimension)

    def get_max_input_tokens(self, model: str | None = None) -> int:
        info = self.get_model_info(model)
        return int(info.get("max_input_tokens", self.config.max_input_tokens or 8192))

    def validate_embeddings(self, embeddings: list[list[float]], model: str | None = None) -> None:
        quality = self.settings.embeddings.quality_validation
        if not quality.enabled:
            return
        expected_dimension = self.get_dimension(model)
        for vector in embeddings:
            if len(vector) != expected_dimension:
                raise EmbeddingValidationError(
                    f"expected dimension {expected_dimension}, got {len(vector)}", provider=self.provider_name.value
                )
            if quality.reject_nan_vectors and any(math.isnan(value) or math.isinf(value) for value in vector):
                raise EmbeddingValidationError("embedding contains NaN or Inf values", provider=self.provider_name.value)
            if quality.reject_zero_vectors:
                norm = math.sqrt(sum(value * value for value in vector))
                if norm < quality.min_norm:
                    raise EmbeddingValidationError("embedding norm is below minimum threshold", provider=self.provider_name.value)

    async def health_check(self) -> bool:
        try:
            await self.embed_query("health check")
            return True
        except EmbeddingProviderError:
            return False


class LocalSentenceTransformerProvider(BaseEmbeddingProvider):
    provider_name: EmbeddingProviderName
    query_prefix: str = ""
    document_prefix: str = ""
    hf_model_ids: dict[str, str] = {}

    def __init__(self, config: EmbeddingProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        self._models: dict[str, Any] = {}

    def _resolve_hf_id(self, model_name: str) -> str:
        return self.hf_model_ids.get(model_name, model_name)

    def _load_model(self, model_name: str) -> Any:
        if model_name in self._models:
            return self._models[model_name]

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingProviderUnavailableError(
                f"sentence-transformers is not installed in this process; "
                f"install requirements-worker.txt to use '{self.provider_name.value}'",
                provider=self.provider_name.value,
            ) from exc

        model = SentenceTransformer(self._resolve_hf_id(model_name), device=self.config.device, trust_remote_code=True)
        self._models[model_name] = model
        return model

    async def embed_documents(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        import asyncio

        model_name = self.resolve_model(model)
        prefixed = [f"{self.document_prefix}{text}" for text in texts]
        embeddings = await asyncio.to_thread(self._encode, model_name, prefixed)
        self.validate_embeddings(embeddings, model_name)
        return embeddings

    async def embed_query(self, text: str, model: str | None = None) -> list[float]:
        import asyncio

        model_name = self.resolve_model(model)
        embeddings = await asyncio.to_thread(self._encode, model_name, [f"{self.query_prefix}{text}"])
        self.validate_embeddings(embeddings, model_name)
        return embeddings[0]

    def _encode(self, model_name: str, texts: list[str]) -> list[list[float]]:
        sentence_model = self._load_model(model_name)
        vectors = sentence_model.encode(
            texts,
            batch_size=self.config.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()