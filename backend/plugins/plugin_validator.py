# plugins/plugin_validator.py
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

_PLUGIN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{2,63}$")
_SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.]+)?$")


class PluginPermission(str, Enum):
    READ_KNOWLEDGE_BASES = "kb:read"
    WRITE_KNOWLEDGE_BASES = "kb:write"
    READ_AGENTS = "agents:read"
    WRITE_AGENTS = "agents:write"
    EXECUTE_TOOLS = "tools:execute"
    NETWORK_ACCESS = "network:access"
    READ_MEMORY = "memory:read"
    WRITE_MEMORY = "memory:write"
    READ_SECRETS = "secrets:read"


@dataclass(slots=True, frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    permissions: list[PluginPermission] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    homepage: str | None = None
    icon_url: str | None = None
    category: str = "general"
    min_neuralcore_version: str = "1.0.0"


@dataclass(slots=True, frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_plugin_id(plugin_id: str) -> bool:
    return bool(_PLUGIN_ID_PATTERN.match(plugin_id))


def validate_semver(version: str) -> bool:
    return bool(_SEMVER_PATTERN.match(version))


def validate_manifest(data: dict[str, Any]) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    required_fields = ["id", "name", "version", "description", "author", "entry_point"]
    for field_name in required_fields:
        if field_name not in data or not str(data.get(field_name, "")).strip():
            errors.append(f"missing or empty required field: '{field_name}'")

    if "id" in data and not validate_plugin_id(data["id"]):
        errors.append(f"invalid plugin id '{data['id']}': must be lowercase alphanumeric with hyphens/underscores, 3-64 chars")

    if "version" in data and not validate_semver(data["version"]):
        errors.append(f"invalid version '{data.get('version')}': must follow semver (e.g. 1.0.0)")

    if "entry_point" in data:
        entry_point = data["entry_point"]
        if ":" not in entry_point:
            errors.append(f"invalid entry_point '{entry_point}': must be 'module.path:ClassName' format")

    raw_permissions = data.get("permissions", [])
    valid_permission_values = {p.value for p in PluginPermission}
    for perm in raw_permissions:
        if perm not in valid_permission_values:
            errors.append(f"unknown permission: '{perm}'")

    if PluginPermission.NETWORK_ACCESS.value in raw_permissions:
        warnings.append("plugin requests network access — verify before installing from untrusted sources")
    if PluginPermission.READ_SECRETS.value in raw_permissions:
        warnings.append("plugin requests secrets access — review carefully before granting")

    if not data.get("description", "").strip() if "description" in data else True:
        pass
    elif len(data["description"]) < 10:
        warnings.append("description is very short; consider expanding for marketplace listing")

    return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)


def manifest_from_dict(data: dict[str, Any]) -> PluginManifest:
    permissions = [PluginPermission(p) for p in data.get("permissions", []) if p in {x.value for x in PluginPermission}]
    return PluginManifest(
        id=data["id"],
        name=data["name"],
        version=data["version"],
        description=data["description"],
        author=data["author"],
        entry_point=data["entry_point"],
        permissions=permissions,
        config_schema=data.get("config_schema", {}),
        dependencies=data.get("dependencies", []),
        homepage=data.get("homepage"),
        icon_url=data.get("icon_url"),
        category=data.get("category", "general"),
        min_neuralcore_version=data.get("min_neuralcore_version", "1.0.0"),
    )


def check_version_compatibility(plugin_min_version: str, current_version: str) -> bool:
    def _parse(v: str) -> tuple[int, ...]:
        core = v.split("-")[0]
        return tuple(int(part) for part in core.split("."))

    try:
        return _parse(current_version) >= _parse(plugin_min_version)
    except (ValueError, IndexError):
        return False
