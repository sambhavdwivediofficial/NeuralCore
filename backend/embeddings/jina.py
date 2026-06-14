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
    provider_name = EmbeddingProviderName.JINA

    def __init__(self, config: EmbeddingProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        if config.api_key is None:
            raise EmbeddingValidationError("Jina API key is not configured", provider=self.provider_name.value)
        self._api_key = config.api_key.get_secret_value()
        self._base_url = config.base_url or _JINA_API_URL

    async def embed_documents(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model_name = self.resolve_model(model)
        info = self.get_model_info(model_name)
        batch_size = self.settings.embeddings.pipeline.batch_size
        all_embeddings: list[list[float]] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            payload: dict[str, object] = {"model": model_name, "input": batch}
            if info.get("multimodal"):
                payload["input"] = [{"text": text} for text in batch]

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self._base_url,
                        headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                        json=payload,
                    )
            except httpx.TransportError as exc:
                raise EmbeddingProviderUnavailableError(str(exc), provider=self.provider_name.value) from exc

            if response.status_code == 401:
                raise EmbeddingAuthenticationError(response.text, provider=self.provider_name.value)
            if response.status_code == 429:
                raise EmbeddingRateLimitError(response.text, provider=self.provider_name.value)
            if response.status_code >= 400:
                raise EmbeddingProviderUnavailableError(response.text, provider=self.provider_name.value)

            data = response.json()
            ordered = sorted(data["data"], key=lambda item: item["index"])
            all_embeddings.extend(item["embedding"] for item in ordered)

        self.validate_embeddings(all_embeddings, model_name)
        return all_embeddings
