# model_gateway/openai_provider.py
from __future__ import annotations

from model_gateway.base_provider import OpenAICompatibleProvider
from settings import LLMProviderName


class OpenAIProvider(OpenAICompatibleProvider):
    provider_name = LLMProviderName.OPENAI