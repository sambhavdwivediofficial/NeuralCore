# model_gateway/llama_provider.py
from __future__ import annotations

from model_gateway.base_provider import OpenAICompatibleProvider
from settings import LLMProviderName


class LlamaProvider(OpenAICompatibleProvider):
    provider_name = LLMProviderName.LLAMA

    def _resolve_api_key(self) -> str:
        return "not-required"