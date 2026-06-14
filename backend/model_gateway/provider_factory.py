# model_gateway/provider_factory.py
from __future__ import annotations

from collections.abc import AsyncIterator

from model_gateway.anthropic_provider import AnthropicProvider
from model_gateway.base_provider import (
    BaseModelProvider,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    ModelProviderError,
    ProviderUnavailableError,
    RateLimitError,
)
from model_gateway.deepseek_provider import DeepSeekProvider
from model_gateway.gemini_provider import GeminiProvider
from model_gateway.llama_provider import LlamaProvider
from model_gateway.mistral_provider import MistralProvider
from model_gateway.ollama_provider import OllamaProvider
from model_gateway.openai_provider import OpenAIProvider
from monitoring.logging import get_logger, log_slow_llm_call
from monitoring.metrics import LLM_CALL_DURATION_SECONDS, record_llm_usage, track_duration
from monitoring.tracing import trace_span
from settings import LLMProviderName, Settings

logger = get_logger("neuralcore.model_gateway")

_PROVIDER_CLASSES: dict[LLMProviderName, type[BaseModelProvider]] = {
    LLMProviderName.OPENAI: OpenAIProvider,
    LLMProviderName.ANTHROPIC: AnthropicProvider,
    LLMProviderName.DEEPSEEK: DeepSeekProvider,
    LLMProviderName.GEMINI: GeminiProvider,
    LLMProviderName.MISTRAL: MistralProvider,
    LLMProviderName.LLAMA: LlamaProvider,
    LLMProviderName.OLLAMA: OllamaProvider,
    LLMProviderName.LOCAL: LlamaProvider,
}

_provider_cache: dict[str, BaseModelProvider] = {}


class ProviderNotConfiguredError(ModelProviderError):
    def __init__(self, provider_name: str) -> None:
        super().__init__("Provider is not enabled or not configured", provider=provider_name)


def get_model_provider(settings: Settings, provider_name: str | None = None) -> BaseModelProvider:
    name = LLMProviderName(provider_name or settings.model_gateway.default_provider.value)

    if name.value in _provider_cache:
        return _provider_cache[name.value]

    config = settings.model_gateway.providers.get(name.value)
    if config is None or not config.enabled:
        raise ProviderNotConfiguredError(name.value)

    provider_class = _PROVIDER_CLASSES[name]
    instance = provider_class(config=config, settings=settings)
    _provider_cache[name.value] = instance
    return instance


def reset_provider_cache() -> None:
    _provider_cache.clear()


class ModelGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _fallback_order(self, provider_name: str | None) -> list[str]:
        if provider_name:
            return [provider_name]
        chain = [provider.value for provider in self.settings.model_gateway.fallback_chain]
        default = self.settings.model_gateway.default_provider.value
        if default not in chain:
            chain = [default] + chain
        return chain

    async def chat_completion(
        self, request: CompletionRequest, provider_name: str | None = None
    ) -> CompletionResponse:
        errors: list[ModelProviderError] = []
        for candidate in self._fallback_order(provider_name):
            try:
                provider = get_model_provider(self.settings, candidate)
            except ProviderNotConfiguredError:
                continue

            model_name = provider.resolve_model(request.model)
            try:
                with trace_span("model_gateway.chat_completion", provider=candidate, model=model_name):
                    with log_slow_llm_call(self.settings, candidate, model_name):
                        with track_duration(LLM_CALL_DURATION_SECONDS, provider=candidate, model=model_name):
                            response = await provider.chat_completion(request)
                record_llm_usage(candidate, model_name, response.usage.prompt_tokens, response.usage.completion_tokens)
                return response
            except (RateLimitError, ProviderUnavailableError) as exc:
                logger.warning("model_provider_fallback", provider=candidate, error=str(exc))
                errors.append(exc)
                continue
            except ModelProviderError as exc:
                logger.error("model_provider_error", provider=candidate, error=str(exc))
                raise

        raise ProviderUnavailableError(
            f"All providers in fallback chain failed: {[str(error) for error in errors]}",
            provider="model_gateway",
        )

    async def stream_chat_completion(
        self, request: CompletionRequest, provider_name: str | None = None
    ) -> AsyncIterator[CompletionChunk]:
        for candidate in self._fallback_order(provider_name):
            try:
                provider = get_model_provider(self.settings, candidate)
            except ProviderNotConfiguredError:
                continue

            model_name = provider.resolve_model(request.model)
            try:
                with trace_span("model_gateway.stream_chat_completion", provider=candidate, model=model_name):
                    async for chunk in provider.stream_chat_completion(request):
                        if chunk.usage is not None:
                            record_llm_usage(candidate, model_name, chunk.usage.prompt_tokens, chunk.usage.completion_tokens)
                        yield chunk
                return
            except (RateLimitError, ProviderUnavailableError) as exc:
                logger.warning("model_provider_stream_fallback", provider=candidate, error=str(exc))
                continue

        raise ProviderUnavailableError("All providers in fallback chain failed", provider="model_gateway")


def get_model_gateway(settings: Settings) -> ModelGateway:
    return ModelGateway(settings)