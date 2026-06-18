# mcp/server.py
from __future__ import annotations

import asyncio
from typing import Any

from mcp.protocol import (
    MCPCapabilities,
    MCPClientInfo,
    MCPErrorCode,
    MCPMessageType,
    MCPNotification,
    MCPRequest,
    MCPResponse,
    MCPServerInfo,
    MCPVersion,
    make_request_id,
)
from mcp.resources import MCPResourceRegistry, _build_neuralcore_resources
from mcp.tools import MCPToolRegistry, _build_neuralcore_tools
from mcp.transport import BaseMCPTransport
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.mcp.server")


class MCPServer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.server_info = MCPServerInfo()
        self.capabilities = MCPCapabilities(
            tools={"listChanged": True},
            resources={"listChanged": True, "subscribe": False},
            prompts={"listChanged": False},
            sampling={},
            logging={},
        )
        self.tool_registry = MCPToolRegistry()
        self.resource_registry = MCPResourceRegistry()
        self._initialized = False
        self._client_info: MCPClientInfo | None = None
        self._request_handlers: dict[str, Any] = {
            MCPMessageType.INITIALIZE.value: self._handle_initialize,
            MCPMessageType.PING.value: self._handle_ping,
            MCPMessageType.LIST_TOOLS.value: self._handle_list_tools,
            MCPMessageType.CALL_TOOL.value: self._handle_call_tool,
            MCPMessageType.LIST_RESOURCES.value: self._handle_list_resources,
            MCPMessageType.READ_RESOURCE.value: self._handle_read_resource,
        }
        _build_neuralcore_tools(self.tool_registry, settings)
        _build_neuralcore_resources(self.resource_registry, settings)
        logger.info("mcp_server_created", tools=len(self.tool_registry), resources=len(self.resource_registry))

    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        handler = self._request_handlers.get(request.method)
        if handler is None:
            return MCPResponse.error_response(request.id, MCPErrorCode.METHOD_NOT_FOUND, f"Method not found: {request.method}")
        try:
            result = await handler(request)
            return MCPResponse.success(request.id, result)
        except KeyError as exc:
            return MCPResponse.error_response(request.id, MCPErrorCode.INVALID_PARAMS, str(exc))
        except Exception as exc:
            logger.error("mcp_request_handler_error", method=request.method, error=str(exc))
            return MCPResponse.error_response(request.id, MCPErrorCode.INTERNAL_ERROR, str(exc))

    async def process_message(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        if "method" not in raw:
            if "result" in raw or "error" in raw:
                return None
            return MCPResponse.error_response(raw.get("id"), MCPErrorCode.INVALID_REQUEST, "Invalid message format").to_dict()

        request = MCPRequest.from_dict(raw)

        if request.id is None:
            await self._handle_notification(request)
            return None

        response = await self.handle_request(request)
        return response.to_dict()

    async def run_loop(self, transport: BaseMCPTransport) -> None:
        logger.info("mcp_server_loop_started")
        try:
            while True:
                raw = await transport.receive()
                result = await self.process_message(raw)
                if result is not None:
                    await transport.send(result)
        except asyncio.CancelledError:
            logger.info("mcp_server_loop_cancelled")
        except Exception as exc:
            logger.error("mcp_server_loop_error", error=str(exc))
        finally:
            await transport.close()

    async def _handle_initialize(self, request: MCPRequest) -> dict[str, Any]:
        params = request.params
        client_info_data = params.get("clientInfo", {})
        self._client_info = MCPClientInfo(
            name=client_info_data.get("name", "unknown"),
            version=client_info_data.get("version", "0.0.0"),
        )
        self._initialized = True
        logger.info("mcp_client_connected", client=self._client_info.name, version=self._client_info.version)

        return {
            "protocolVersion": MCPVersion.V1.value,
            "serverInfo": {"name": self.server_info.name, "version": self.server_info.version},
            "capabilities": {
                "tools": self.capabilities.tools,
                "resources": self.capabilities.resources,
                "prompts": self.capabilities.prompts,
                "sampling": self.capabilities.sampling,
                "logging": self.capabilities.logging,
            },
        }

    async def _handle_ping(self, request: MCPRequest) -> dict[str, Any]:
        return {}

    async def _handle_list_tools(self, request: MCPRequest) -> dict[str, Any]:
        cursor = request.params.get("cursor")
        return {"tools": self.tool_registry.list_definitions()}

    async def _handle_call_tool(self, request: MCPRequest) -> dict[str, Any]:
        name = request.params.get("name")
        arguments = request.params.get("arguments", {})
        if not name:
            raise KeyError("'name' is required in tool call params")
        if name not in self.tool_registry:
            raise KeyError(f"Tool '{name}' not found")
        result = await self.tool_registry.call(name, arguments)
        return result.to_dict()

    async def _handle_list_resources(self, request: MCPRequest) -> dict[str, Any]:
        return {"resources": self.resource_registry.list_definitions()}

    async def _handle_read_resource(self, request: MCPRequest) -> dict[str, Any]:
        uri = request.params.get("uri")
        if not uri:
            raise KeyError("'uri' is required in resource read params")
        content = await self.resource_registry.read(uri, request.params)
        return {"contents": [content.to_dict()]}

    async def _handle_notification(self, request: MCPRequest) -> None:
        logger.debug("mcp_notification_received", method=request.method)
    