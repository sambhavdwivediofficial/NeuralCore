# model_gateway/deepseek_provider.py
from __future__ import annotations

from model_gateway.base_provider import OpenAICompatibleProvider
from settings import LLMProviderName


class DeepSeekProvider(OpenAICompatibleProvider):
    provider_name = LLMProviderName.DEEPSEEK