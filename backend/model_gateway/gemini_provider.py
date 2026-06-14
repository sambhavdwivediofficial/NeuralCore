# model_gateway/gemini_provider.py
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from model_gateway.base_provider import (
    AuthenticationError,
    BaseModelProvider,
    ChatMessage,
    ChatRole,
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
    Usage,
    approximate_token_count,
)
from settings import LLMProviderName, ModelProviderConfig, Settings


class GeminiProvider(BaseModelProvider):
    provider_name = LLMProviderName.GEMINI

    def __init__(self, config: ModelProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        import google.generativeai as genai

        if config.api_key is not None:
            genai.configure(api_key=config.api_key.get_secret_value())
        self._genai = genai

    async def chat_completion(self, request: CompletionRequest) -> CompletionResponse:
        model = self._build_model(request)
        contents = self._convert_messages(request.messages)
        try:
            response = await model.generate_content_async(contents)
        except Exception as exc:
            raise self._map_exception(exc) from exc
        return self._parse_response(response, request)

    async def stream_chat_completion(self, request: CompletionRequest) -> AsyncIterator[CompletionChunk]:
        model = self._build_model(request)
        contents = self._convert_messages(request.messages)
        model_name = self.resolve_model(request.model)
        try:
            stream = await model.generate_content_async(contents, stream=True)
            async for chunk in stream:
                text = "".join(
                    part.text for part in chunk.candidates[0].content.parts if getattr(part, "text", None)
                )
                finish_reason = None
                usage = None
                if chunk.candidates[0].finish_reason:
                    finish_reason = self._map_finish_reason(chunk.candidates[0].finish_reason)
                    if chunk.usage_metadata is not None:
                        usage = Usage(
                            prompt_tokens=chunk.usage_metadata.prompt_token_count,
                            completion_tokens=chunk.usage_metadata.candidates_token_count,
                            total_tokens=chunk.usage_metadata.total_token_count,
                        )
                yield CompletionChunk(
                    id="",
                    model=model_name,
                    provider=self.provider_name.value,
                    delta=text or None,
                    finish_reason=finish_reason,
                    usage=usage,
                )
        except Exception as exc:
            raise self._map_exception(exc) from exc

    def count_tokens(self, messages: list[ChatMessage], model: str | None = None) -> int:
        text = "\n".join(message.content or "" for message in messages)
        return approximate_token_count(text)

    def _build_model(self, request: CompletionRequest) -> Any:
        system_instruction, _ = self._split_system(request.messages)
        generation_config = self._genai.types.GenerationConfig(
            temperature=request.temperature,
            top_p=request.top_p,
            max_output_tokens=request.max_tokens,
            stop_sequences=request.stop,
        )
        tools = None
        if request.tools:
            tools = [
                {
                    "function_declarations": [
                        {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
                        for tool in request.tools
                    ]
                }
            ]
        return self._genai.GenerativeModel(
            model_name=self.resolve_model(request.model),
            system_instruction=system_instruction,
            generation_config=generation_config,
            tools=tools,
        )

    @staticmethod
    def _split_system(messages: list[ChatMessage]) -> tuple[str | None, list[ChatMessage]]:
        system_parts = [message.content for message in messages if message.role == ChatRole.SYSTEM and message.content]
        remaining = [message for message in messages if message.role != ChatRole.SYSTEM]
        return ("\n".join(system_parts) if system_parts else None), remaining

    def _convert_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        _, remaining = self._split_system(messages)
        contents: list[dict[str, Any]] = []
        for message in remaining:
            if message.role == ChatRole.TOOL:
                contents.append(
                    {
                        "role": "function",
                        "parts": [
                            {
                                "function_response": {
                                    "name": message.name or "",
                                    "response": {"content": message.content or ""},
                                }
                            }
                        ],
                    }
                )
                continue
            role = "model" if message.role == ChatRole.ASSISTANT else "user"
            parts: list[dict[str, Any]] = []
            if message.content:
                parts.append({"text": message.content})
            if message.tool_calls:
                for call in message.tool_calls:
                    parts.append({"function_call": {"name": call.name, "args": call.arguments}})
            contents.append({"role": role, "parts": parts})
        return contents

    def _parse_response(self, response: Any, request: CompletionRequest) -> CompletionResponse:
        candidate = response.candidates[0]
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for part in candidate.content.parts:
            if getattr(part, "text", None):
                text_parts.append(part.text)
            elif getattr(part, "function_call", None) and part.function_call.name:
                tool_calls.append(
                    ToolCall(
                        id=part.function_call.name,
                        name=part.function_call.name,
                        arguments=dict(part.function_call.args),
                    )
                )

        usage = Usage()
        if response.usage_metadata is not None:
            usage = Usage(
                prompt_tokens=response.usage_metadata.prompt_token_count,
                completion_tokens=response.usage_metadata.candidates_token_count,
                total_tokens=response.usage_metadata.total_token_count,
            )

        return CompletionResponse(
            id="",
            model=self.resolve_model(request.model),
            provider=self.provider_name.value,
            content="".join(text_parts) or None,
            tool_calls=tool_calls or None,
            finish_reason=self._map_finish_reason(candidate.finish_reason),
            usage=usage,
        )

    @staticmethod
    def _map_finish_reason(reason: Any) -> FinishReason:
        name = getattr(reason, "name", str(reason))
        mapping = {
            "STOP": FinishReason.STOP,
            "MAX_TOKENS": FinishReason.LENGTH,
            "SAFETY": FinishReason.CONTENT_FILTER,
            "RECITATION": FinishReason.CONTENT_FILTER,
        }
        return mapping.get(name, FinishReason.STOP)

    def _map_exception(self, exc: Exception) -> ModelProviderError:
        from google.api_core import exceptions as google_exceptions

        if isinstance(exc, (google_exceptions.Unauthenticated, google_exceptions.PermissionDenied)):
            return AuthenticationError(str(exc), provider=self.provider_name.value)
        if isinstance(exc, google_exceptions.ResourceExhausted):
            return RateLimitError(str(exc), provider=self.provider_name.value)
        if isinstance(exc, google_exceptions.InvalidArgument):
            message = str(exc).lower()
            if "token" in message or "context" in message:
                return ContextLengthExceededError(str(exc), provider=self.provider_name.value)
            return InvalidRequestError(str(exc), provider=self.provider_name.value)
        if isinstance(exc, (google_exceptions.ServiceUnavailable, google_exceptions.DeadlineExceeded)):
            return ProviderUnavailableError(str(exc), provider=self.provider_name.value)
        return ModelProviderError(str(exc), provider=self.provider_name.value)