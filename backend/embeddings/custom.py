# embeddings/custom.py
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


class CustomEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = EmbeddingProviderName.CUSTOM

    def __init__(self, config: EmbeddingProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        if not config.base_url:
            raise EmbeddingValidationError(
                "base_url is not configured for the custom embedding provider", provider=self.provider_name.value
            )

    async def embed_documents(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model_name = self.resolve_model(model)
        info = self.get_model_info(model_name)
        endpoint = info.get("endpoint", self.config.base_url)
        headers = {"Content-Type": "application/json", **info.get("headers", {})}
        if self.config.api_key is not None:
            headers["Authorization"] = f"Bearer {self.config.api_key.get_secret_value()}"

        batch_size = self.settings.embeddings.pipeline.batch_size
        all_embeddings: list[list[float]] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            payload = {"model": model_name, "input": batch}

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(endpoint, headers=headers, json=payload)
            except httpx.TransportError as exc:
                raise EmbeddingProviderUnavailableError(str(exc), provider=self.provider_name.value) from exc

            if response.status_code == 401:
                raise EmbeddingAuthenticationError(response.text, provider=self.provider_name.value)
            if response.status_code == 429:
                raise EmbeddingRateLimitError(response.text, provider=self.provider_name.value)
            if response.status_code >= 400:
                raise EmbeddingProviderUnavailableError(response.text, provider=self.provider_name.value)

            data = response.json()
            all_embeddings.extend(self._extract_embeddings(data))

        self.validate_embeddings(all_embeddings, model_name)
        return all_embeddings

    @staticmethod
    def _extract_embeddings(data: object) -> list[list[float]]:
        if isinstance(data, list):
            return [list(map(float, item)) for item in data]
        if isinstance(data, dict) and "data" in data:
            ordered = sorted(data["data"], key=lambda item: item.get("index", 0))
            return [list(map(float, item["embedding"])) for item in ordered]
        if isinstance(data, dict) and "embeddings" in data:
            return [list(map(float, item)) for item in data["embeddings"]]
        raise EmbeddingValidationError(
            "unrecognized response format from custom embedding endpoint",
            provider=EmbeddingProviderName.CUSTOM.value,
        )
