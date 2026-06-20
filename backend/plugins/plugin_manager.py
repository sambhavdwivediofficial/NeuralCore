# plugins/plugin_manager.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from monitoring.logging import get_logger
from plugins.plugin_loader import BasePlugin, PluginLoadError, discover_plugins_in_directory, load_plugin_from_directory
from plugins.plugin_registry import PluginRegistry, PluginStatus, get_plugin_registry
from plugins.plugin_validator import PluginPermission
from settings import Settings

logger = get_logger("neuralcore.plugins.manager")

_PLUGINS_ROOT = "/data/plugins"
_BUILTIN_PLUGINS: dict[str, tuple[str, str]] = {
    "github": ("plugins.builtin.github", "GitHubPlugin"),
    "jira": ("plugins.builtin.jira", "JiraPlugin"),
    "notion": ("plugins.builtin.notion", "NotionPlugin"),
    "slack": ("plugins.builtin.slack", "SlackPlugin"),
}


class PluginPermissionError(Exception):
    pass


class PluginManager:
    def __init__(self, settings: Settings, plugins_root: str = _PLUGINS_ROOT) -> None:
        self.settings = settings
        self.plugins_root = plugins_root
        self.registry: PluginRegistry = get_plugin_registry()

    async def install_builtin(self, plugin_id: str, config: dict[str, Any], organization_id: str) -> dict[str, Any]:
        from plugins.plugin_loader import load_builtin_plugin_class

        builtin_info = _BUILTIN_PLUGINS.get(plugin_id)
        if builtin_info is None:
            raise PluginLoadError(plugin_id, f"'{plugin_id}' is not a recognized built-in plugin")

        module_path, class_name = builtin_info
        plugin_class = load_builtin_plugin_class(module_path, class_name)
        manifest = plugin_class.manifest

        entry = self.registry.register(manifest, config=config, organization_id=organization_id)
        instance = plugin_class(config)
        await instance.on_load()

        self.registry.set_instance(manifest.id, instance, organization_id)
        self.registry.set_status(manifest.id, PluginStatus.LOADED, organization_id)

        logger.info("builtin_plugin_installed", plugin_id=plugin_id, organization_id=organization_id)
        return entry.to_dict()

    async def install_from_directory(self, plugin_dir: str, config: dict[str, Any], organization_id: str) -> dict[str, Any]:
        entry = await load_plugin_from_directory(Path(plugin_dir), config, organization_id)
        return entry.to_dict()

    async def enable(self, plugin_id: str, organization_id: str) -> bool:
        entry = self.registry.get(plugin_id, organization_id)
        if entry is None or entry.instance is None:
            return False
        await entry.instance.on_enable()
        self.registry.set_status(plugin_id, PluginStatus.ACTIVE, organization_id)
        logger.info("plugin_enabled", plugin_id=plugin_id, organization_id=organization_id)
        return True

    async def disable(self, plugin_id: str, organization_id: str) -> bool:
        entry = self.registry.get(plugin_id, organization_id)
        if entry is None or entry.instance is None:
            return False
        await entry.instance.on_disable()
        self.registry.set_status(plugin_id, PluginStatus.DISABLED, organization_id)
        logger.info("plugin_disabled", plugin_id=plugin_id, organization_id=organization_id)
        return True

    async def uninstall(self, plugin_id: str, organization_id: str) -> bool:
        entry = self.registry.get(plugin_id, organization_id)
        if entry is None:
            return False
        if entry.instance is not None:
            await entry.instance.on_unload()
        self.registry.unregister(plugin_id, organization_id)
        logger.info("plugin_uninstalled", plugin_id=plugin_id, organization_id=organization_id)
        return True

    def get_plugin_instance(self, plugin_id: str, organization_id: str) -> Any:
        entry = self.registry.get(plugin_id, organization_id)
        if entry is None or entry.status != PluginStatus.ACTIVE:
            return None
        return entry.instance

    def check_permission(self, plugin_id: str, organization_id: str, permission: PluginPermission) -> bool:
        entry = self.registry.get(plugin_id, organization_id)
        if entry is None:
            return False
        return permission in entry.manifest.permissions

    async def discover_available_plugins(self) -> dict[str, Any]:
        builtin = [{"id": pid, "type": "builtin"} for pid in _BUILTIN_PLUGINS]
        custom_manifests = await discover_plugins_in_directory(self.plugins_root)
        custom = [{"id": m.id, "type": "custom", "name": m.name, "version": m.version} for m in custom_manifests]
        return {"builtin": builtin, "custom": custom, "total": len(builtin) + len(custom)}

    def list_installed(self, organization_id: str) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self.registry.list_plugins(organization_id=organization_id)]
