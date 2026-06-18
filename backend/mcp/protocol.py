# mcp/protocol.py
from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class MCPVersion(str, enum.Enum):
    V1 = "2024-11-05"


class MCPMessageType(str, enum.Enum):
    INITIALIZE = "initialize"
    INITIALIZED = "initialized"
    PING = "ping"
    PONG = "pong"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    CREATE_MESSAGE = "sampling/createMessage"
    NOTIFICATION = "notifications/message"
    PROGRESS = "notifications/progress"
    RESOURCES_CHANGED = "notifications/resources/list_changed"
    TOOLS_CHANGED = "notifications/tools/list_changed"
    ERROR = "error"


class MCPErrorCode(int, enum.Enum):
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    TOOL_NOT_FOUND = -32001
    RESOURCE_NOT_FOUND = -32002
    UNAUTHORIZED = -32003
    RATE_LIMITED = -32004
    TIMEOUT = -32005


@dataclass(slots=True, frozen=True)
class MCPClientInfo:
    name: str
    version: str


@dataclass(slots=True, frozen=True)
class MCPServerInfo:
    name: str = "NeuralCore MCP Server"
    version: str = "1.0.0"


@dataclass(slots=True, frozen=True)
class MCPCapabilities:
    tools: dict[str, Any] = field(default_factory=dict)
    resources: dict[str, Any] = field(default_factory=dict)
    prompts: dict[str, Any] = field(default_factory=dict)
    sampling: dict[str, Any] = field(default_factory=dict)
    logging: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MCPRequest:
    method: str
    id: str | int | None = None
    params: dict[str, Any] = field(default_factory=dict)
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method}
        if self.id is not None:
            data["id"] = self.id
        if self.params:
            data["params"] = self.params
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPRequest":
        return cls(
            method=data["method"],
            id=data.get("id"),
            params=data.get("params", {}),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )


@dataclass(slots=True)
class MCPResponse:
    id: str | int | None
    result: Any = None
    error: dict[str, Any] | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            data["error"] = self.error
        else:
            data["result"] = self.result
        return data

    @classmethod
    def success(cls, request_id: Any, result: Any) -> "MCPResponse":
        return cls(id=request_id, result=result)

    @classmethod
    def error_response(cls, request_id: Any, code: MCPErrorCode, message: str, data: Any = None) -> "MCPResponse":
        error: dict[str, Any] = {"code": code.value, "message": message}
        if data is not None:
            error["data"] = data
        return cls(id=request_id, error=error)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPResponse":
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error"),
            jsonrpc=data.get("jsonrpc", "2.0"),
        )

    def is_error(self) -> bool:
        return self.error is not None


@dataclass(slots=True, frozen=True)
class MCPNotification:
    method: str
    params: dict[str, Any] = field(default_factory=dict)
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        return {"jsonrpc": self.jsonrpc, "method": self.method, "params": self.params}


def make_request_id() -> str:
    return uuid.uuid4().hex
