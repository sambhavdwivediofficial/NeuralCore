# tools/custom/example_tool.py
from __future__ import annotations

from typing import Any

from tools.registry import get_tool_registry
from tools.schemas import ToolParameter, ToolParameterType, ToolSchema


async def _echo_handler(arguments: dict[str, Any]) -> dict[str, Any]:
    message = arguments["message"]
    repeat = int(arguments.get("repeat", 1))
    return {
        "original": message,
        "output": " | ".join([message] * repeat),
        "repeat_count": repeat,
        "char_count": len(message),
    }


ECHO_SCHEMA = ToolSchema(
    name="echo",
    description="Echo back the provided message, optionally repeated. Useful for testing tool integration.",
    parameters=[
        ToolParameter(name="message", type=ToolParameterType.STRING, description="Message to echo", required=True),
        ToolParameter(name="repeat", type=ToolParameterType.INTEGER, description="Times to repeat (default: 1)", required=False, default=1),
    ],
    returns="dict with original and output strings",
    category="utility",
)


def register_example_tools() -> None:
    registry = get_tool_registry()
    registry.register(ECHO_SCHEMA, _echo_handler)
