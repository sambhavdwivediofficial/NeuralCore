# model_gateway/base_provider.py
from __future__ import annotations

import enum
import math
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from settings import LLMProviderName, ModelProviderConfig, Settings

try:
    import neuralcore_engine
except ImportError:
    neuralcore_engine = None

try:
    import tiktoken
except ImportError:
    tiktoken = None


class ChatRole(str, enum.Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FinishReason(str, enum.Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallDelta(BaseModel):
    index: int
    id: str | None = None
    name: str | None = None
    arguments_delta: str | None = None


class ChatMessage(BaseModel):
    role: ChatRole
    content: str | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CompletionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    messages: list[ChatMessage]
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float = 1.0
    stop: list[str] | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompletionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    model: str
    provider: str
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    finish_reason: FinishReason
    usage: Usage


class CompletionChunk(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: str
    model: str
    provider: str
    delta: str | None = None
    tool_call_deltas: list[ToolCallDelta] | None = None
    finish_reason: FinishReason | None = None
    usage: Usage | None = None


class ModelProviderError(Exception):
    def __init__(self, message: str, provider: str, status_code: int | None = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(f"[{provider}] {message}")


class AuthenticationError(ModelProviderError):
    pass


class RateLimitError(ModelProviderError):
    pass


class ContextLengthExceededError(ModelProviderError):
    pass


class ProviderUnavailableError(ModelProviderError):
    pass


class InvalidRequestError(ModelProviderError):
    pass


def approximate_token_count(text: str) -> int:
    if neuralcore_engine is not None:
        func = getattr(neuralcore_engine, "py_count_tokens_approximate", None)
        if func is not None:
            try:
                return int(func(text))
            except Exception:
                pass
    if tiktoken is not None:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            pass
    return max(1, math.ceil(len(text) / 4))


class BaseModelProvider(ABC):
    provider_name: LLMProviderName

    def __init__(self, config: ModelProviderConfig, settings: Settings) -> None:
        self.config = config
        self.settings = settings

    @abstractmethod
    async def chat_completion(self, request: CompletionRequest) -> CompletionResponse: ...

    @abstractmethod
    def stream_chat_completion(self, request: CompletionRequest) -> AsyncIterator[CompletionChunk]: ...

    def count_tokens(self, messages: list[ChatMessage], model: str | None = None) -> int:
        text = "\n".join(message.content or "" for message in messages)
        return approximate_token_count(text)

    def resolve_model(self, model: str | None) -> str:
        return model or self.config.default_model

    def context_window(self) -> int:
        return self.config.context_window

    async def health_check(self) -> bool:
        try:
            await self.chat_completion(
                CompletionRequest(messages=[ChatMessage(role=ChatRole.USER, content="ping")], max_tokens=1)
            )
            return True
        except ModelProviderError:
            return False


class OpenAICompatibleProvider(BaseModelProvider):
    provider_name: LLMProviderName = LLMProviderName.OPENAI

    def __init__(self, config: ModelProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=self._resolve_api_key(),
            base_url=self._resolve_base_url(),
            timeout=config.timeout_seconds,
            max_retries=0,
        )

    def _resolve_api_key(self) -> str:
        if self.config.api_key is not None:
            return self.config.api_key.get_secret_value()
        return "not-required"

    def _resolve_base_url(self) -> str | None:
        return self.config.base_url

    async def chat_completion(self, request: CompletionRequest) -> CompletionResponse:
        import openai

        try:
            response = await self._client.chat.completions.create(**self._build_payload(request, stream=False))
        except openai.AuthenticationError as exc:
            raise AuthenticationError(str(exc), provider=self.provider_name.value) from exc
        except openai.RateLimitError as exc:
            raise RateLimitError(str(exc), provider=self.provider_name.value) from exc
        except openai.BadRequestError as exc:
            if "context length" in str(exc).lower() or "maximum context" in str(exc).lower():
                raise ContextLengthExceededError(str(exc), provider=self.provider_name.value) from exc
            raise InvalidRequestError(str(exc), provider=self.provider_name.value) from exc
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            raise ProviderUnavailableError(str(exc), provider=self.provider_name.value) from exc
        except openai.APIStatusError as exc:
            raise ModelProviderError(str(exc), provider=self.provider_name.value, status_code=exc.status_code) from exc

        return self._parse_response(response)

    async def stream_chat_completion(self, request: CompletionRequest) -> AsyncIterator[CompletionChunk]:
        import openai

        try:
            stream = await self._client.chat.completions.create(
                **self._build_payload(request, stream=True),
                stream_options={"include_usage": True},
            )
        except openai.AuthenticationError as exc:
            raise AuthenticationError(str(exc), provider=self.provider_name.value) from exc
        except openai.RateLimitError as exc:
            raise RateLimitError(str(exc), provider=self.provider_name.value) from exc
        except (openai.APIConnectionError, openai.APITimeoutError) as exc:
            raise ProviderUnavailableError(str(exc), provider=self.provider_name.value) from exc

        model_name = self.resolve_model(request.model)
        async for chunk in stream:
            yield self._parse_chunk(chunk, model_name)

    def _build_payload(self, request: CompletionRequest, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.resolve_model(request.model),
            "messages": [self._convert_message(message) for message in request.messages],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": stream,
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
        data: dict[str, Any] = {"role": message.role.value}
        if message.content is not None:
            data["content"] = message.content
        if message.name is not None:
            data["name"] = message.name
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
        usage = response.usage
        return CompletionResponse(
            id=response.id,
            model=response.model,
            provider=self.provider_name.value,
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=self._map_finish_reason(choice.finish_reason),
            usage=Usage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
        )

    def _parse_chunk(self, chunk: Any, model_name: str) -> CompletionChunk:
        choice = chunk.choices[0] if chunk.choices else None
        delta_text: str | None = None
        tool_call_deltas: list[ToolCallDelta] | None = None
        finish_reason: FinishReason | None = None

        if choice is not None:
            delta = choice.delta
            delta_text = delta.content
            if delta.tool_calls:
                tool_call_deltas = [
                    ToolCallDelta(
                        index=call.index,
                        id=call.id,
                        name=call.function.name if call.function else None,
                        arguments_delta=call.function.arguments if call.function else None,
                    )
                    for call in delta.tool_calls
                ]
            if choice.finish_reason:
                finish_reason = self._map_finish_reason(choice.finish_reason)

        usage = None
        if chunk.usage is not None:
            usage = Usage(
                prompt_tokens=chunk.usage.prompt_tokens,
                completion_tokens=chunk.usage.completion_tokens,
                total_tokens=chunk.usage.total_tokens,
            )

        return CompletionChunk(
            id=chunk.id,
            model=model_name,
            provider=self.provider_name.value,
            delta=delta_text,
            tool_call_deltas=tool_call_deltas,
            finish_reason=finish_reason,
            usage=usage,
        )

    @staticmethod
    def _map_finish_reason(reason: str | None) -> FinishReason:
        mapping = {
            "stop": FinishReason.STOP,
            "length": FinishReason.LENGTH,
            "tool_calls": FinishReason.TOOL_CALLS,
            "content_filter": FinishReason.CONTENT_FILTER,
        }
        return mapping.get(reason or "stop", FinishReason.STOP)


def _json_dumps(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value)


def _json_loads(value: str) -> dict[str, Any]:
    import json

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return {}