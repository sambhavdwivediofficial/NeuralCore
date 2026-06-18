# tools/schemas.py
from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class ToolParameterType(str, enum.Enum):
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    name: str
    type: ToolParameterType
    description: str
    required: bool = False
    default: Any = None
    enum_values: list[Any] | None = None
    items: dict[str, Any] | None = None
    properties: dict[str, Any] | None = None


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)
    returns: str = "string"
    examples: list[dict[str, Any]] = Field(default_factory=list)
    category: str = "general"
    version: str = "1.0.0"
    is_async: bool = True

    def to_openai_function(self) -> dict[str, Any]:
        required = [p.name for p in self.parameters if p.required]
        properties: dict[str, Any] = {}
        for param in self.parameters:
            prop: dict[str, Any] = {"type": param.type.value, "description": param.description}
            if param.enum_values:
                prop["enum"] = param.enum_values
            if param.default is not None:
                prop["default"] = param.default
            if param.items:
                prop["items"] = param.items
            if param.properties:
                prop["properties"] = param.properties
            properties[param.name] = prop

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }

    def to_json_schema(self) -> dict[str, Any]:
        return self.to_openai_function()["function"]["parameters"]
