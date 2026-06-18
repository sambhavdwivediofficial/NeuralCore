# tools/registry.py
from __future__ import annotations

import asyncio
from typing import Any, Callable, Coroutine

from model_gateway.base_provider import ToolDefinition
from monitoring.logging import get_logger
from tools.schemas import ToolParameter, ToolSchema

logger = get_logger("neuralcore.tools.registry")

ToolHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, Any]]

_GLOBAL_REGISTRY: "ToolRegistry | None" = None


class ToolNotFoundError(KeyError):
    pass


class ToolExecutionError(RuntimeError):
    def __init__(self, tool_name: str, cause: Exception) -> None:
        self.tool_name = tool_name
        self.cause = cause
        super().__init__(f"Tool '{tool_name}' execution failed: {cause}")


class RegisteredTool:
    __slots__ = ("schema", "handler", "enabled")

    def __init__(self, schema: ToolSchema, handler: ToolHandler, enabled: bool = True) -> None:
        self.schema = schema
        self.handler = handler
        self.enabled = enabled

    @property
    def description(self) -> str:
        return self.schema.description


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        schema: ToolSchema,
        handler: ToolHandler,
        enabled: bool = True,
    ) -> None:
        self._tools[schema.name] = RegisteredTool(schema=schema, handler=handler, enabled=enabled)
        logger.debug("tool_registered", name=schema.name, category=schema.category)

    def register_simple(
        self,
        name: str,
        description: str,
        handler: ToolHandler,
        parameters: list[ToolParameter] | None = None,
        category: str = "general",
    ) -> None:
        schema = ToolSchema(name=name, description=description, parameters=parameters or [], category=category)
        self.register(schema, handler)

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def enable(self, name: str) -> None:
        if name in self._tools:
            self._tools[name].enabled = True

    def disable(self, name: str) -> None:
        if name in self._tools:
            self._tools[name].enabled = False

    async def execute(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool '{name}' is not registered")
        if not tool.enabled:
            raise ToolNotFoundError(f"Tool '{name}' is disabled")

        from tools.validator import validate_tool_input
        try:
            validated = validate_tool_input(arguments, tool.schema.parameters)
        except Exception as exc:
            raise ToolExecutionError(name, exc) from exc

        try:
            result = await asyncio.wait_for(tool.handler(validated), timeout=120.0)
            logger.debug("tool_executed", name=name)
            return result
        except asyncio.TimeoutError as exc:
            raise ToolExecutionError(name, TimeoutError(f"Tool '{name}' timed out")) from exc
        except ToolExecutionError:
            raise
        except Exception as exc:
            logger.warning("tool_execution_error", name=name, error=str(exc))
            raise ToolExecutionError(name, exc) from exc

    def get_definitions(self, names: list[str] | None = None) -> list[ToolDefinition]:
        tools = self._tools.values() if names is None else [
            self._tools[n] for n in names if n in self._tools
        ]
        return [
            ToolDefinition(
                name=tool.schema.name,
                description=tool.schema.description,
                parameters=tool.schema.to_json_schema(),
            )
            for tool in tools
            if tool.enabled
        ]

    def list_schemas(self, category: str | None = None) -> list[ToolSchema]:
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.schema.category == category]
        return [t.schema for t in tools if t.enabled]

    def __contains__(self, name: str) -> bool:
        return name in self._tools and self._tools[name].enabled

    def __len__(self) -> int:
        return sum(1 for t in self._tools.values() if t.enabled)


def get_tool_registry() -> ToolRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = ToolRegistry()
        _register_builtin_tools(_GLOBAL_REGISTRY)
    return _GLOBAL_REGISTRY


def reset_tool_registry() -> None:
    global _GLOBAL_REGISTRY
    _GLOBAL_REGISTRY = None


def _register_builtin_tools(registry: ToolRegistry) -> None:
    from tools.builtin.calculator import CALCULATOR_SCHEMA, calculator_handler
    from tools.builtin.file_reader import FILE_READER_SCHEMA, file_reader_handler
    from tools.builtin.memory import MEMORY_READ_SCHEMA, MEMORY_WRITE_SCHEMA, memory_read_handler, memory_write_handler
    from tools.builtin.retrieval import RETRIEVAL_SCHEMA, retrieval_handler
    from tools.builtin.web_search import WEB_SEARCH_SCHEMA, web_search_handler

    registry.register(CALCULATOR_SCHEMA, calculator_handler)
    registry.register(FILE_READER_SCHEMA, file_reader_handler)
    registry.register(MEMORY_READ_SCHEMA, memory_read_handler)
    registry.register(MEMORY_WRITE_SCHEMA, memory_write_handler)
    registry.register(RETRIEVAL_SCHEMA, retrieval_handler)
    registry.register(WEB_SEARCH_SCHEMA, web_search_handler)
