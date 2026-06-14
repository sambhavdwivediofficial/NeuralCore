# model_gateway/anthropic_provider.py
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
    ToolCallDelta,
    ToolDefinition,
    Usage,
    approximate_token_count,
)
from settings import LLMProviderName, ModelProviderConfig, Settings


class AnthropicProvider(BaseModelProvider):
    provider_name = LLMProviderName.ANTHROPIC

    def __init__(self, config: ModelProviderConfig, settings: Settings) -> None:
        super().__init__(config, settings)
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(
            api_key=config.api_key.get_secret_value() if config.api_key else None,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
            max_retries=0,
        )

    async def chat_completion(self, request: CompletionRequest) -> CompletionResponse:
        import anthropic

        payload = self._build_payload(request)
        try:
            response = await self._client.messages.create(**payload)
        except anthropic.AuthenticationError as exc:
            raise AuthenticationError(str(exc), provider=self.provider_name.value) from exc
        except anthropic.RateLimitError as exc:
            raise RateLimitError(str(exc), provider=self.provider_name.value) from exc
        except anthropic.BadRequestError as exc:
            message = str(exc).lower()
            if "max_tokens" in message or "context" in message or "too long" in message:
                raise ContextLengthExceededError(str(exc), provider=self.provider_name.value) from exc
            raise InvalidRequestError(str(exc), provider=self.provider_name.value) from exc
        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
            raise ProviderUnavailableError(str(exc), provider=self.provider_name.value) from exc
        except anthropic.APIStatusError as exc:
            raise ModelProviderError(str(exc), provider=self.provider_name.value, status_code=exc.status_code) from exc

        return self._parse_response(response)

    async def stream_chat_completion(self, request: CompletionRequest) -> AsyncIterator[CompletionChunk]:
        import anthropic

        payload = self._build_payload(request)
        model_name = self.resolve_model(request.model)
        tool_buffers: dict[int, dict[str, Any]] = {}

        try:
            async with self._client.messages.stream(**payload) as stream:
                message_id = ""
                async for event in stream:
                    if event.type == "message_start":
                        message_id = event.message.id
                    elif event.type == "content_block_start":
                        if event.content_block.type == "tool_use":
                            tool_buffers[event.index] = {
                                "id": event.content_block.id,
                                "name": event.content_block.name,
                                "arguments": "",
                            }
                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            yield CompletionChunk(
                                id=message_id,
                                model=model_name,
                                provider=self.provider_name.value,
                                delta=event.delta.text,
                            )
                        elif event.delta.type == "input_json_delta":
                            buffer = tool_buffers.setdefault(event.index, {"id": "", "name": "", "arguments": ""})
                            buffer["arguments"] += event.delta.partial_json
                            yield CompletionChunk(
                                id=message_id,
                                model=model_name,
                                provider=self.provider_name.value,
                                tool_call_deltas=[
                                    ToolCallDelta(
                                        index=event.index,
                                        id=buffer["id"] or None,
                                        name=buffer["name"] or None,
                                        arguments_delta=event.delta.partial_json,
                                    )
                                ],
                            )
                    elif event.type == "message_delta":
                        finish_reason = self._map_stop_reason(event.delta.stop_reason)
                        usage = Usage(
                            prompt_tokens=getattr(event.usage, "input_tokens", 0) or 0,
                            completion_tokens=getattr(event.usage, "output_tokens", 0) or 0,
                            total_tokens=(getattr(event.usage, "input_tokens", 0) or 0)
                            + (getattr(event.usage, "output_tokens", 0) or 0),
                        )
                        yield CompletionChunk(
                            id=message_id,
                            model=model_name,
                            provider=self.provider_name.value,
                            finish_reason=finish_reason,
                            usage=usage,
                        )
        except anthropic.AuthenticationError as exc:
            raise AuthenticationError(str(exc), provider=self.provider_name.value) from exc
        except anthropic.RateLimitError as exc:
            raise RateLimitError(str(exc), provider=self.provider_name.value) from exc
        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
            raise ProviderUnavailableError(str(exc), provider=self.provider_name.value) from exc

    def count_tokens(self, messages: list[ChatMessage], model: str | None = None) -> int:
        text = "\n".join(message.content or "" for message in messages)
        return approximate_token_count(text)

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        system_prompt, converted_messages = self._convert_messages(request.messages)
        payload: dict[str, Any] = {
            "model": self.resolve_model(request.model),
            "max_tokens": request.max_tokens or 4096,
            "messages": converted_messages,
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        if system_prompt:
            payload["system"] = system_prompt
        if request.stop:
            payload["stop_sequences"] = request.stop
        if request.tools:
            payload["tools"] = [self._convert_tool(tool) for tool in request.tools]
            if request.tool_choice == "auto":
                payload["tool_choice"] = {"type": "auto"}
            elif request.tool_choice == "none":
                payload["tool_choice"] = {"type": "none"}
            elif request.tool_choice:
                payload["tool_choice"] = {"type": "tool", "name": request.tool_choice}
        return payload

    @staticmethod
    def _convert_messages(messages: list[ChatMessage]) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts: list[str] = []
        converted: list[dict[str, Any]] = []
        for message in messages:
            if message.role == ChatRole.SYSTEM:
                if message.content:
                    system_parts.append(message.content)
                continue
            if message.role == ChatRole.TOOL:
                converted.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_call_id,
                                "content": message.content or "",
                            }
                        ],
                    }
                )
                continue
            if message.role == ChatRole.ASSISTANT and message.tool_calls:
                content: list[dict[str, Any]] = []
                if message.content:
                    content.append({"type": "text", "text": message.content})
                for call in message.tool_calls:
                    content.append({"type": "tool_use", "id": call.id, "name": call.name, "input": call.arguments})
                converted.append({"role": "assistant", "content": content})
                continue
            converted.append({"role": message.role.value, "content": message.content or ""})
        system_prompt = "\n".join(system_parts) if system_parts else None
        return system_prompt, converted

    @staticmethod
    def _convert_tool(tool: ToolDefinition) -> dict[str, Any]:
        return {"name": tool.name, "description": tool.description, "input_schema": tool.parameters}

    def _parse_response(self, response: Any) -> CompletionResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))

        return CompletionResponse(
            id=response.id,
            model=response.model,
            provider=self.provider_name.value,
            content="".join(text_parts) or None,
            tool_calls=tool_calls or None,
            finish_reason=self._map_stop_reason(response.stop_reason),
            usage=Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            ),
        )

    @staticmethod
    def _map_stop_reason(reason: str | None) -> FinishReason:
        mapping = {
            "end_turn": FinishReason.STOP,
            "max_tokens": FinishReason.LENGTH,
            "tool_use": FinishReason.TOOL_CALLS,
            "stop_sequence": FinishReason.STOP,
        }
        return mapping.get(reason or "end_turn", FinishReason.STOP)