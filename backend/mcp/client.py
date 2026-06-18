# mcp/client.py
from __future__ import annotations

import asyncio
from typing import Any

from mcp.protocol import (
    MCPClientInfo,
    MCPErrorCode,
    MCPMessageType,
    MCPRequest,
    MCPResponse,
    MCPVersion,
    make_request_id,
)
from mcp.transport import BaseMCPTransport, StdioTransport
from monitoring.logging import get_logger

logger = get_logger("neuralcore.mcp.client")


class MCPClientError(Exception):
    def __init__(self, message: str, code: int | None = None) -> None:
        self.code = code
        super().__init__(message)


class MCPClient:
    def __init__(self, client_info: MCPClientInfo | None = None) -> None:
        self._info = client_info or MCPClientInfo(name="NeuralCore Agent", version="1.0.0")
        self._transport: BaseMCPTransport | None = None
        self._pending: dict[str | int, asyncio.Future[MCPResponse]] = {}
        self._recv_task: asyncio.Task[Any] | None = None
        self._initialized = False
        self._server_info: dict[str, Any] = {}
        self._server_capabilities: dict[str, Any] = {}

    async def connect_stdio(self, command: list[str]) -> None:
        transport = StdioTransport()
        await transport.connect(command)
        self._transport = transport
        self._recv_task = asyncio.create_task(self._recv_loop())
        await self._initialize()

    async def connect_transport(self, transport: BaseMCPTransport) -> None:
        self._transport = transport
        self._recv_task = asyncio.create_task(self._recv_loop())
        await self._initialize()

    async def _initialize(self) -> None:
        response = await self._send_request(
            MCPMessageType.INITIALIZE.value,
            {
                "protocolVersion": MCPVersion.V1.value,
                "clientInfo": {"name": self._info.name, "version": self._info.version},
                "capabilities": {"sampling": {}, "roots": {"listChanged": False}},
            },
        )
        if response.is_error():
            raise MCPClientError(f"Initialization failed: {response.error}", response.error.get("code") if response.error else None)
        self._server_info = response.result.get("serverInfo", {}) if response.result else {}
        self._server_capabilities = response.result.get("capabilities", {}) if response.result else {}
        self._initialized = True
        logger.info("mcp_client_initialized", server=self._server_info.get("name"), version=self._server_info.get("version"))

    async def list_tools(self) -> list[dict[str, Any]]:
        response = await self._send_request(MCPMessageType.LIST_TOOLS.value, {})
        if response.is_error():
            raise MCPClientError(f"list_tools failed: {response.error}")
        return response.result.get("tools", []) if response.result else []

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self._send_request(
            MCPMessageType.CALL_TOOL.value,
            {"name": name, "arguments": arguments or {}},
        )
        if response.is_error():
            raise MCPClientError(f"call_tool '{name}' failed: {response.error}")
        return response.result or {}

    async def list_resources(self) -> list[dict[str, Any]]:
        response = await self._send_request(MCPMessageType.LIST_RESOURCES.value, {})
        if response.is_error():
            raise MCPClientError(f"list_resources failed: {response.error}")
        return response.result.get("resources", []) if response.result else []

    async def read_resource(self, uri: str) -> dict[str, Any]:
        response = await self._send_request(MCPMessageType.READ_RESOURCE.value, {"uri": uri})
        if response.is_error():
            raise MCPClientError(f"read_resource '{uri}' failed: {response.error}")
        return response.result or {}

    async def ping(self) -> bool:
        try:
            response = await asyncio.wait_for(
                self._send_request(MCPMessageType.PING.value, {}), timeout=5.0
            )
            return not response.is_error()
        except asyncio.TimeoutError:
            return False

    async def _send_request(self, method: str, params: dict[str, Any], timeout: float = 60.0) -> MCPResponse:
        if self._transport is None:
            raise MCPClientError("Client is not connected")
        request_id = make_request_id()
        request = MCPRequest(method=method, id=request_id, params=params)
        future: asyncio.Future[MCPResponse] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        await self._transport.send_request(request)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError as exc:
            self._pending.pop(request_id, None)
            raise MCPClientError(f"Request '{method}' timed out after {timeout}s") from exc

    async def _recv_loop(self) -> None:
        while True:
            try:
                raw = await self._transport.receive()
                response = MCPResponse.from_dict(raw)
                if response.id in self._pending:
                    future = self._pending.pop(response.id)
                    if not future.done():
                        future.set_result(response)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("mcp_client_recv_error", error=str(exc))
                for future in self._pending.values():
                    if not future.done():
                        future.set_exception(MCPClientError(str(exc)))
                self._pending.clear()
                break

    async def close(self) -> None:
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except asyncio.CancelledError:
                pass
        if self._transport:
            await self._transport.close()
        self._initialized = False
        logger.info("mcp_client_closed")

    @property
    def server_info(self) -> dict[str, Any]:
        return self._server_info

    @property
    def is_connected(self) -> bool:
        return self._initialized
