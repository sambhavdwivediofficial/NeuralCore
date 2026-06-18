# mcp/resources.py
from __future__ import annotations

import mimetypes
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from monitoring.logging import get_logger

logger = get_logger("neuralcore.mcp.resources")

ResourceHandler = Callable[[str, dict[str, Any]], Coroutine[Any, Any, Any]]


@dataclass(slots=True, frozen=True)
class MCPResourceDefinition:
    uri: str
    name: str
    description: str
    mime_type: str = "text/plain"
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
            "annotations": self.annotations,
        }


@dataclass(slots=True, frozen=True)
class MCPResourceContent:
    uri: str
    content: str | bytes
    mime_type: str = "text/plain"

    def to_dict(self) -> dict[str, Any]:
        if isinstance(self.content, bytes):
            import base64
            return {"uri": self.uri, "blob": base64.b64encode(self.content).decode("utf-8"), "mimeType": self.mime_type}
        return {"uri": self.uri, "text": self.content, "mimeType": self.mime_type}


class MCPResourceRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, MCPResourceDefinition] = {}
        self._handlers: dict[str, ResourceHandler] = {}
        self._templates: dict[str, str] = {}

    def register(
        self,
        uri: str,
        name: str,
        description: str,
        handler: ResourceHandler,
        mime_type: str = "text/plain",
        annotations: dict[str, Any] | None = None,
    ) -> None:
        definition = MCPResourceDefinition(uri=uri, name=name, description=description, mime_type=mime_type, annotations=annotations or {})
        self._definitions[uri] = definition
        self._handlers[uri] = handler
        logger.debug("mcp_resource_registered", uri=uri)

    def register_template(self, uri_template: str, resource_uri: str) -> None:
        self._templates[uri_template] = resource_uri

    async def read(self, uri: str, params: dict[str, Any] | None = None) -> MCPResourceContent:
        handler = self._handlers.get(uri)
        if handler is None:
            for template_uri, handler_uri in self._templates.items():
                if _match_uri_template(uri, template_uri):
                    handler = self._handlers.get(handler_uri)
                    break

        if handler is None:
            raise KeyError(f"No handler registered for resource: {uri}")

        content = await handler(uri, params or {})
        mime_type = self._definitions.get(uri, MCPResourceDefinition(uri=uri, name="", description="")).mime_type
        return MCPResourceContent(uri=uri, content=content, mime_type=mime_type)

    def list_definitions(self) -> list[dict[str, Any]]:
        return [defn.to_dict() for defn in self._definitions.values()]

    def __len__(self) -> int:
        return len(self._definitions)


def _match_uri_template(uri: str, template: str) -> bool:
    import re
    pattern = re.sub(r"\{[^}]+\}", r"[^/]+", re.escape(template))
    return bool(re.fullmatch(pattern, uri))


def _build_neuralcore_resources(registry: MCPResourceRegistry, settings: Any) -> None:
    async def _kb_list_handler(uri: str, params: dict[str, Any]) -> str:
        return "knowledge_bases: []"

    async def _agent_list_handler(uri: str, params: dict[str, Any]) -> str:
        return "agents: []"

    async def _model_info_handler(uri: str, params: dict[str, Any]) -> str:
        import json
        return json.dumps({
            "default_provider": settings.model_gateway.default_provider.value,
            "fallback_chain": [p.value for p in settings.model_gateway.fallback_chain],
        })

    async def _retrieval_config_handler(uri: str, params: dict[str, Any]) -> str:
        import json
        return json.dumps({
            "hybrid_enabled": settings.retrieval.hybrid.enabled,
            "rrf_k": settings.retrieval.hybrid.rrf_k,
            "reranking_enabled": settings.retrieval.reranking.enabled,
        })

    registry.register("neuralcore://knowledge-bases", "Knowledge Bases", "List of all knowledge bases", _kb_list_handler, "application/json")
    registry.register("neuralcore://agents", "Agents", "List of all agents", _agent_list_handler, "application/json")
    registry.register("neuralcore://model-config", "Model Configuration", "Current model gateway configuration", _model_info_handler, "application/json")
    registry.register("neuralcore://retrieval-config", "Retrieval Configuration", "Current retrieval pipeline configuration", _retrieval_config_handler, "application/json")
    