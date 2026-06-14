# model_gateway/mistral_provider.py
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from model_gateway.base_provider import (
    AuthenticationError,
    BaseModelProvider,
    ChatMessage,
    CompletionChunk,
    CompletionRequest,
    CompletionResponse,
    ContextLengthExceededError,
    FinishReason,
    InvalidRequestError,
    ModelProviderError,
    ProviderUnavailableError,
    RateLimitError,
    ToolCall,
    ToolCallDelta,
    ToolDefinition,
    Usage,
    approximate_token_count,
)
from settings import LLMProviderName, ModelProviderConfig, Settings


class MistralProvider(BaseModelProvider):
    provider_name = LLMProviderName.MISTRAL

    def __init__(self, config: ModelProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        from mistralai import Mistral

        self._client = Mistral(
            api_key=config.api_key.get_secret_value() if config.api_key else "",
            server_url=config.base_url,
        )

    async def chat_completion(self, request: CompletionRequest) -> CompletionResponse:
        payload = self._build_payload(request)
        try:
            response = await self._client.chat.complete_async(**payload)
        except Exception as exc:
            raise self._map_exception(exc) from exc
        return self._parse_response(response)

    async def stream_chat_completion(self, request: CompletionRequest) -> AsyncIterator[CompletionChunk]:
        payload = self._build_payload(request)
        model_name = self.resolve_model(request.model)
        try:
            stream = await self._client.chat.stream_async(**payload)
            async for event in stream:
                chunk = event.data
                choice = chunk.choices[0] if chunk.choices else None
                delta_text: str | None = None
                tool_call_deltas: list[ToolCallDelta] | None = None
                finish_reason: FinishReason | None = None
                usage = None

                if choice is not None:
                    delta_text = choice.delta.content if choice.delta.content else None
                    if choice.delta.tool_calls:
                        tool_call_deltas = [
                            ToolCallDelta(
                                index=index,
                                id=call.id,
                                name=call.function.name if call.function else None,
                                arguments_delta=call.function.arguments if call.function else None,
                            )
                            for index, call in enumerate(choice.delta.tool_calls)
                        ]
                    if choice.finish_reason:
                        finish_reason = self._map_finish_reason(choice.finish_reason)

                if chunk.usage is not None:
                    usage = Usage(
                        prompt_tokens=chunk.usage.prompt_tokens,
                        completion_tokens=chunk.usage.completion_tokens,
                        total_tokens=chunk.usage.total_tokens,
                    )

                yield CompletionChunk(
                    id=chunk.id,
                    model=model_name,
                    provider=self.provider_name.value,
                    delta=delta_text,
                    tool_call_deltas=tool_call_deltas,
                    finish_reason=finish_reason,
                    usage=usage,
                )
        except Exception as exc:
            raise self._map_exception(exc) from exc

    def count_tokens(self, messages: list[ChatMessage], model: str | None = None) -> int:
        text = "\n".join(message.content or "" for message in messages)
        return approximate_token_count(text)

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.resolve_model(request.model),
            "messages": [self._convert_message(message) for message in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        if request.tools:
            payload["tools"] = [self._convert_tool(tool) for tool in request.tools]
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice
        return payload

    @staticmethod
    def _convert_message(message: ChatMessage) -> dict[str, Any]:
        data: dict[str, Any] = {"role": message.role.value, "content": message.content or ""}
        if message.tool_call_id is not None:
            data["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            data["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": _json_dumps(call.arguments)},
                }
                for call in message.tool_calls
            ]
        return data

    @staticmethod
    def _convert_tool(tool: ToolDefinition) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters},
        }

    def _parse_response(self, response: Any) -> CompletionResponse:
        choice = response.choices[0]
        message = choice.message
        tool_calls: list[ToolCall] | None = None
        if message.tool_calls:
            tool_calls = [
                ToolCall(id=call.id, name=call.function.name, arguments=_json_loads(call.function.arguments))
                for call in message.tool_calls
            ]
        return CompletionResponse(
            id=response.id,
            model=response.model,
            provider=self.provider_name.value,
            content=message.content if isinstance(message.content, str) else None,
            tool_calls=tool_calls,
            finish_reason=self._map_finish_reason(choice.finish_reason),
            usage=Usage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ),
        )

    @staticmethod
    def _map_finish_reason(reason: str | None) -> FinishReason:
        mapping = {
            "stop": FinishReason.STOP,
            "length": FinishReason.LENGTH,
            "tool_calls": FinishReason.TOOL_CALLS,
            "model_length": FinishReason.LENGTH,
        }
        return mapping.get(reason or "stop", FinishReason.STOP)

    def _map_exception(self, exc: Exception) -> ModelProviderError:
        from mistralai.models import SDKError

        if isinstance(exc, SDKError):
            status_code = getattr(exc, "status_code", None)
            if status_code == 401:
                return AuthenticationError(str(exc), provider=self.provider_name.value, status_code=status_code)
            if status_code == 429:
                return RateLimitError(str(exc), provider=self.provider_name.value, status_code=status_code)
            if status_code == 400:
                message = str(exc).lower()
                if "context" in message or "token" in message:
                    return ContextLengthExceededError(str(exc), provider=self.provider_name.value, status_code=status_code)
                return InvalidRequestError(str(exc), provider=self.provider_name.value, status_code=status_code)
            if status_code is not None and status_code >= 500:
                return ProviderUnavailableError(str(exc), provider=self.provider_name.value, status_code=status_code)
        return ModelProviderError(str(exc), provider=self.provider_name.value)


def _json_dumps(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value)


def _json_loads(value: str) -> dict[str, Any]:
    import json

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}