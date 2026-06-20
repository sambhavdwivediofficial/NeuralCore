# plugins/plugin_registry.py
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from monitoring.logging import get_logger
from plugins.plugin_validator import PluginManifest

logger = get_logger("neuralcore.plugins.registry")


class PluginStatus(str, Enum):
    REGISTERED = "registered"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass(slots=True)
class PluginEntry:
    manifest: PluginManifest
    status: PluginStatus
    instance: Any = None
    config: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    organization_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.manifest.id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "description": self.manifest.description,
            "author": self.manifest.author,
            "category": self.manifest.category,
            "permissions": [p.value for p in self.manifest.permissions],
            "status": self.status.value,
            "error_message": self.error_message,
            "organization_id": self.organization_id,
        }


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, PluginEntry] = {}
        self._hooks: dict[str, list[Callable[..., Coroutine[Any, Any, Any]]]] = {}

    def register(self, manifest: PluginManifest, config: dict[str, Any] | None = None, organization_id: str | None = None) -> PluginEntry:
        entry = PluginEntry(manifest=manifest, status=PluginStatus.REGISTERED, config=config or {}, organization_id=organization_id)
        key = self._entry_key(manifest.id, organization_id)
        self._plugins[key] = entry
        logger.debug("plugin_registered", plugin_id=manifest.id, organization_id=organization_id)
        return entry

    def _entry_key(self, plugin_id: str, organization_id: str | None) -> str:
        return f"{organization_id or 'global'}:{plugin_id}"

    def get(self, plugin_id: str, organization_id: str | None = None) -> PluginEntry | None:
        return self._plugins.get(self._entry_key(plugin_id, organization_id))

    def set_status(self, plugin_id: str, status: PluginStatus, organization_id: str | None = None, error_message: str | None = None) -> None:
        entry = self.get(plugin_id, organization_id)
        if entry is not None:
            entry.status = status
            entry.error_message = error_message

    def set_instance(self, plugin_id: str, instance: Any, organization_id: str | None = None) -> None:
        entry = self.get(plugin_id, organization_id)
        if entry is not None:
            entry.instance = instance

    def unregister(self, plugin_id: str, organization_id: str | None = None) -> bool:
        key = self._entry_key(plugin_id, organization_id)
        if key in self._plugins:
            del self._plugins[key]
            return True
        return False

    def list_plugins(self, organization_id: str | None = None, category: str | None = None, status: PluginStatus | None = None) -> list[PluginEntry]:
        entries = [e for e in self._plugins.values() if organization_id is None or e.organization_id == organization_id or e.organization_id is None]
        if category:
            entries = [e for e in entries if e.manifest.category == category]
        if status:
            entries = [e for e in entries if e.status == status]
        return entries

    def register_hook(self, hook_name: str, handler: Callable[..., Coroutine[Any, Any, Any]]) -> None:
        self._hooks.setdefault(hook_name, []).append(handler)

    async def trigger_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        import asyncio
        handlers = self._hooks.get(hook_name, [])
        if not handlers:
            return []
        results = await asyncio.gather(*[h(*args, **kwargs) for h in handlers], return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning("plugin_hook_error", hook=hook_name, error=str(result))
        return [r for r in results if not isinstance(r, Exception)]

    def __len__(self) -> int:
        return len(self._plugins)


_global_registry: PluginRegistry | None = None


def get_plugin_registry() -> PluginRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry
