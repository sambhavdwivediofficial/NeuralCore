# tools/validator.py
from __future__ import annotations

import re
from typing import Any

from tools.schemas import ToolParameter, ToolParameterType


class ToolValidationError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"Validation error for '{field}': {message}")


def validate_tool_input(
    arguments: dict[str, Any], parameters: list[ToolParameter]
) -> dict[str, Any]:
    validated: dict[str, Any] = {}
    param_map = {p.name: p for p in parameters}

    for param in parameters:
        if param.required and param.name not in arguments:
            raise ToolValidationError(param.name, "required parameter is missing")

    for name, value in arguments.items():
        param = param_map.get(name)
        if param is None:
            continue

        coerced = _coerce_value(name, value, param)
        validated[name] = coerced

    for param in parameters:
        if param.name not in validated and param.default is not None:
            validated[param.name] = param.default

    return validated


def _coerce_value(name: str, value: Any, param: ToolParameter) -> Any:
    if value is None:
        if param.required:
            raise ToolValidationError(name, "cannot be null")
        return param.default

    if param.type == ToolParameterType.STRING:
        if not isinstance(value, str):
            value = str(value)
        if param.enum_values and value not in param.enum_values:
            raise ToolValidationError(name, f"must be one of {param.enum_values}, got '{value}'")
        return value

    if param.type == ToolParameterType.INTEGER:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ToolValidationError(name, f"must be an integer, got {type(value).__name__}") from exc

    if param.type == ToolParameterType.NUMBER:
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ToolValidationError(name, f"must be a number, got {type(value).__name__}") from exc

    if param.type == ToolParameterType.BOOLEAN:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes"):
                return True
            if value.lower() in ("false", "0", "no"):
                return False
        raise ToolValidationError(name, f"must be a boolean, got '{value}'")

    if param.type == ToolParameterType.ARRAY:
        if not isinstance(value, list):
            raise ToolValidationError(name, f"must be an array, got {type(value).__name__}")
        return value

    if param.type == ToolParameterType.OBJECT:
        if not isinstance(value, dict):
            raise ToolValidationError(name, f"must be an object, got {type(value).__name__}")
        return value

    return value


def sanitize_tool_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip())
    if sanitized and sanitized[0].isdigit():
        sanitized = f"tool_{sanitized}"
    return sanitized[:64]
