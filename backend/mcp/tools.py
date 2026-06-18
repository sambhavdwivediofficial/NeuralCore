# mcp/tools.py
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from monitoring.logging import get_logger

logger = get_logger("neuralcore.mcp.tools")

ToolHandler = Callable[[dict[str, Any], dict[str, Any]], Coroutine[Any, Any, Any]]


@dataclass(slots=True, frozen=True)
class MCPToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": self.annotations,
        }


@dataclass(slots=True)
class MCPToolResult:
    content: list[dict[str, Any]]
    is_error: bool = False

    @classmethod
    def text(cls, text: str) -> "MCPToolResult":
        return cls(content=[{"type": "text", "text": text}])

    @classmethod
    def json_result(cls, data: Any) -> "MCPToolResult":
        return cls(content=[{"type": "text", "text": json.dumps(data, ensure_ascii=False, indent=2)}])

    @classmethod
    def error(cls, message: str) -> "MCPToolResult":
        return cls(content=[{"type": "text", "text": f"Error: {message}"}], is_error=True)

    def to_dict(self) -> dict[str, Any]:
        return {"content": self.content, "isError": self.is_error}


class MCPToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, MCPToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: ToolHandler,
        annotations: dict[str, Any] | None = None,
    ) -> None:
        definition = MCPToolDefinition(name=name, description=description, input_schema=input_schema, annotations=annotations or {})
        self._tools[name] = definition
        self._handlers[name] = handler
        logger.debug("mcp_tool_registered", name=name)

    async def call(self, name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None) -> MCPToolResult:
        handler = self._handlers.get(name)
        if handler is None:
            return MCPToolResult.error(f"Tool '{name}' not found")
        try:
            result = await asyncio.wait_for(handler(arguments, context or {}), timeout=120.0)
            if isinstance(result, MCPToolResult):
                return result
            if isinstance(result, str):
                return MCPToolResult.text(result)
            return MCPToolResult.json_result(result)
        except asyncio.TimeoutError:
            return MCPToolResult.error(f"Tool '{name}' timed out after 120 seconds")
        except Exception as exc:
            logger.error("mcp_tool_execution_error", tool=name, error=str(exc))
            return MCPToolResult.error(str(exc))

    def list_definitions(self) -> list[dict[str, Any]]:
        return [tool.to_dict() for tool in self._tools.values()]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def _build_neuralcore_tools(registry: MCPToolRegistry, settings: Any) -> None:
    async def _rag_query(arguments: dict[str, Any], context: dict[str, Any]) -> MCPToolResult:
        from retrieval.retriever import Retriever
        import uuid as _uuid
        retriever = Retriever(settings=settings)
        results = await retriever.search(
            knowledge_base_id=_uuid.UUID(arguments["knowledge_base_id"]),
            query=arguments["query"],
            top_k=arguments.get("top_k", 5),
            use_hybrid=True,
            use_reranking=arguments.get("use_reranking", True),
        )
        return MCPToolResult.json_result({
            "query": arguments["query"],
            "results": [{"id": r.id, "score": r.score, "text": r.text, "metadata": r.metadata} for r in results],
            "total": len(results),
        })

    async def _embed_text(arguments: dict[str, Any], context: dict[str, Any]) -> MCPToolResult:
        from embeddings.embedding_factory import get_embedding_provider
        provider = get_embedding_provider(settings=settings, provider_name=arguments.get("provider"))
        vector = await provider.embed_query(arguments["text"])
        return MCPToolResult.json_result({"dimension": len(vector), "vector_preview": vector[:5], "text": arguments["text"]})

    async def _list_knowledge_bases(arguments: dict[str, Any], context: dict[str, Any]) -> MCPToolResult:
        return MCPToolResult.json_result({"knowledge_bases": [], "total": 0})

    async def _llm_complete(arguments: dict[str, Any], context: dict[str, Any]) -> MCPToolResult:
        from model_gateway.base_provider import ChatMessage, ChatRole, CompletionRequest
        from model_gateway.provider_factory import get_model_gateway
        gateway = get_model_gateway(settings)
        response = await gateway.chat_completion(
            CompletionRequest(
                messages=[ChatMessage(role=ChatRole.USER, content=arguments["prompt"])],
                max_tokens=arguments.get("max_tokens", 1024),
                temperature=arguments.get("temperature", 0.7),
            ),
            provider_name=arguments.get("provider"),
        )
        return MCPToolResult.json_result({"content": response.content, "provider": response.provider, "model": response.model, "usage": response.usage.model_dump()})

    async def _extract_entities(arguments: dict[str, Any], context: dict[str, Any]) -> MCPToolResult:
        from graphrag.entities.entity_extractor import extract_entities
        import uuid as _uuid
        entities = await extract_entities(
            text=arguments["text"],
            chunk_id=_uuid.uuid4().hex,
            settings=settings,
            max_entities=arguments.get("max_entities", 20),
        )
        return MCPToolResult.json_result({"entities": [{"name": e.name, "type": e.entity_type, "description": e.description, "confidence": e.confidence} for e in entities]})

    async def _count_tokens(arguments: dict[str, Any], context: dict[str, Any]) -> MCPToolResult:
        from chunking.base_chunker import count_tokens

        text = arguments["text"]
        token_count = count_tokens(text)
        max_tokens = arguments.get("max_tokens")
        result: dict[str, Any] = {"text_length": len(text), "token_count": token_count}
        if max_tokens is not None:
            result["fits_in_context"] = token_count <= max_tokens
            result["max_tokens"] = max_tokens
        return MCPToolResult.json_result(result)

    async def _detect_pii(arguments: dict[str, Any], context: dict[str, Any]) -> MCPToolResult:
        from preprocessing.pii_detector import detect_pii, redact_pii
        text = arguments["text"]
        matches = detect_pii(text)
        redacted = redact_pii(text)
        return MCPToolResult.json_result({
            "has_pii": len(matches) > 0,
            "pii_types": list({m.type.value for m in matches}),
            "match_count": len(matches),
            "redacted_text": redacted,
        })

    registry.register(
        "neuralcore_rag_query",
        "Query a NeuralCore knowledge base using RAG",
        {"type": "object", "properties": {"knowledge_base_id": {"type": "string"}, "query": {"type": "string"}, "top_k": {"type": "integer", "default": 5}, "use_reranking": {"type": "boolean", "default": True}}, "required": ["knowledge_base_id", "query"]},
        _rag_query,
    )
    registry.register(
        "neuralcore_embed_text",
        "Generate embeddings for text using NeuralCore embedding providers",
        {"type": "object", "properties": {"text": {"type": "string"}, "provider": {"type": "string"}}, "required": ["text"]},
        _embed_text,
    )
    registry.register(
        "neuralcore_list_knowledge_bases",
        "List all available knowledge bases in NeuralCore",
        {"type": "object", "properties": {"project_id": {"type": "string"}}, "required": []},
        _list_knowledge_bases,
    )
    registry.register(
        "neuralcore_llm_complete",
        "Call an LLM via the NeuralCore model gateway",
        {"type": "object", "properties": {"prompt": {"type": "string"}, "provider": {"type": "string"}, "max_tokens": {"type": "integer", "default": 1024}, "temperature": {"type": "number", "default": 0.7}}, "required": ["prompt"]},
        _llm_complete,
    )
    registry.register(
        "neuralcore_extract_entities",
        "Extract named entities from text using NeuralCore GraphRAG pipeline",
        {"type": "object", "properties": {"text": {"type": "string"}, "max_entities": {"type": "integer", "default": 20}}, "required": ["text"]},
        _extract_entities,
    )
    registry.register(
        "neuralcore_count_tokens",
        "Count tokens in text using the NeuralCore tokenizer (Rust engine or tiktoken fallback)",
        {"type": "object", "properties": {"text": {"type": "string"}, "max_tokens": {"type": "integer"}}, "required": ["text"]},
        _count_tokens,
    )
    registry.register(
        "neuralcore_detect_pii",
        "Detect and redact PII from text",
        {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        _detect_pii,
    )
