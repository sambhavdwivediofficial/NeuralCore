# model_gateway/ollama_provider.py
from __future__ import annotations

from model_gateway.base_provider import OpenAICompatibleProvider
from settings import LLMProviderName


class OllamaProvider(OpenAICompatibleProvider):
    provider_name = LLMProviderName.OLLAMA

    def _resolve_api_key(self) -> str:
        return "ollama"

    def _resolve_base_url(self) -> str | None:
        base_url = self.config.base_url
        if base_url is None:
            return None
        normalized = base_url.rstrip("/")
        if not normalized.endswith("/v1"):
            normalized = f"{normalized}/v1"
        return normalized