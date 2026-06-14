# embeddings/openai.py
from __future__ import annotations

from embeddings.base_embedding import (
    BaseEmbeddingProvider,
    EmbeddingAuthenticationError,
    EmbeddingProviderUnavailableError,
    EmbeddingRateLimitError,
)
from settings import EmbeddingProviderConfig, EmbeddingProviderName, Settings


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    provider_name = EmbeddingProviderName.OPENAI

    def __init__(self, config: EmbeddingProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=config.api_key.get_secret_value() if config.api_key else None,
            base_url=config.base_url,
            timeout=60.0,
            max_retries=0,
        )

    async def embed_documents(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        import openai

        model_name = self.resolve_model(model)
        batch_size = self.settings.embeddings.pipeline.batch_size
        all_embeddings: list[list[float]] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            try:
                response = await self._client.embeddings.create(model=model_name, input=batch)
            except openai.AuthenticationError as exc:
                raise EmbeddingAuthenticationError(str(exc), provider=self.provider_name.value) from exc
            except openai.RateLimitError as exc:
                raise EmbeddingRateLimitError(str(exc), provider=self.provider_name.value) from exc
            except (openai.APIConnectionError, openai.APITimeoutError) as exc:
                raise EmbeddingProviderUnavailableError(str(exc), provider=self.provider_name.value) from exc

            ordered = sorted(response.data, key=lambda item: item.index)
            all_embeddings.extend(item.embedding for item in ordered)

        self.validate_embeddings(all_embeddings, model_name)
        return all_embeddings
