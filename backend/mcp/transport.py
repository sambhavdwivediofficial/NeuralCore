# mcp/transport.py
from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from mcp.protocol import MCPRequest, MCPResponse
from monitoring.logging import get_logger

logger = get_logger("neuralcore.mcp.transport")


class MCPTransportError(Exception):
    pass


class BaseMCPTransport(ABC):
    @abstractmethod
    async def send(self, message: dict[str, Any]) -> None: ...

    @abstractmethod
    async def receive(self) -> dict[str, Any]: ...

    @abstractmethod
    async def close(self) -> None: ...

    async def send_request(self, request: MCPRequest) -> None:
        await self.send(request.to_dict())

    async def send_response(self, response: MCPResponse) -> None:
        await self.send(response.to_dict())


class StdioTransport(BaseMCPTransport):
    def __init__(self) -> None:
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self, command: list[str]) -> None:
        proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        if proc.stdin is None or proc.stdout is None:
            raise MCPTransportError("Failed to open subprocess stdio streams")
        self._writer = proc.stdin
        self._reader = proc.stdout
        self._proc = proc

    async def send(self, message: dict[str, Any]) -> None:
        if self._writer is None:
            raise MCPTransportError("Transport not connected")
        data = json.dumps(message, ensure_ascii=False)
        self._writer.write(f"Content-Length: {len(data.encode('utf-8'))}\r\n\r\n{data}".encode("utf-8"))
        await self._writer.drain()

    async def receive(self) -> dict[str, Any]:
        if self._reader is None:
            raise MCPTransportError("Transport not connected")
        header = b""
        while not header.endswith(b"\r\n\r\n"):
            chunk = await self._reader.read(1)
            if not chunk:
                raise MCPTransportError("Connection closed")
            header += chunk

        content_length = 0
        for line in header.decode("utf-8").strip().splitlines():
            if line.lower().startswith("content-length:"):
                content_length = int(line.split(":")[1].strip())
                break

        if content_length == 0:
            raise MCPTransportError("Invalid Content-Length in header")

        body = await self._reader.readexactly(content_length)
        return json.loads(body.decode("utf-8"))

    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()
        if hasattr(self, "_proc"):
            self._proc.terminate()
            await self._proc.wait()


class SSETransport(BaseMCPTransport):
    def __init__(self) -> None:
        self._send_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._recv_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def send(self, message: dict[str, Any]) -> None:
        await self._send_queue.put(message)

    async def receive(self) -> dict[str, Any]:
        return await self._recv_queue.get()

    async def push_incoming(self, message: dict[str, Any]) -> None:
        await self._recv_queue.put(message)

    async def event_stream(self) -> AsyncIterator[str]:
        while True:
            try:
                message = await asyncio.wait_for(self._send_queue.get(), timeout=30.0)
                data = json.dumps(message, ensure_ascii=False)
                yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                yield "data: {\"type\": \"ping\"}\n\n"
            except asyncio.CancelledError:
                break

    async def close(self) -> None:
        pass


class WebSocketTransport(BaseMCPTransport):
    def __init__(self, websocket: Any) -> None:
        self._ws = websocket

    async def send(self, message: dict[str, Any]) -> None:
        await self._ws.send_text(json.dumps(message, ensure_ascii=False))

    async def receive(self) -> dict[str, Any]:
        data = await self._ws.receive_text()
        return json.loads(data)

    async def close(self) -> None:
        await self._ws.close()


class InMemoryTransport(BaseMCPTransport):
    def __init__(self) -> None:
        self._outgoing: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._incoming: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def send(self, message: dict[str, Any]) -> None:
        await self._outgoing.put(message)

    async def receive(self) -> dict[str, Any]:
        return await self._incoming.get()

    async def inject(self, message: dict[str, Any]) -> None:
        await self._incoming.put(message)

    async def read_sent(self) -> dict[str, Any]:
        return await self._outgoing.get()

    async def close(self) -> None:
        pass
    