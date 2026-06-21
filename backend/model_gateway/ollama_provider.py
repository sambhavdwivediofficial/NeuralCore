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

    async def supports_vision(self, model_name: str | None = None) -> bool:
        import httpx

        model = model_name or self.config.default_model
        base_url = self._resolve_base_url() or "http://localhost:11434/v1"
        ollama_base = base_url.removesuffix("/v1")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(f"{ollama_base}/api/show", json={"name": model})
                if response.status_code != 200:
                    return False
                data = response.json()
                families = data.get("details", {}).get("families", []) or []
                return any(family in ("clip", "mllama") for family in families)
        except Exception:
            return False
