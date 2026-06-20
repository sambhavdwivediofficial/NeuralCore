# plugins/plugin_loader.py
from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from monitoring.logging import get_logger
from plugins.plugin_registry import PluginEntry, PluginStatus, get_plugin_registry
from plugins.plugin_validator import PluginManifest, ValidationResult, manifest_from_dict, validate_manifest

logger = get_logger("neuralcore.plugins.loader")


class PluginLoadError(Exception):
    def __init__(self, plugin_id: str, message: str) -> None:
        self.plugin_id = plugin_id
        super().__init__(f"Failed to load plugin '{plugin_id}': {message}")


class BasePlugin:
    manifest: PluginManifest

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    async def on_load(self) -> None:
        pass

    async def on_unload(self) -> None:
        pass

    async def on_enable(self) -> None:
        pass

    async def on_disable(self) -> None:
        pass


def load_manifest_from_directory(plugin_dir: Path) -> tuple[PluginManifest, ValidationResult]:
    manifest_path = plugin_dir / "manifest.json"
    if not manifest_path.exists():
        raise PluginLoadError(plugin_dir.name, "manifest.json not found")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = validate_manifest(data)
    if not validation.valid:
        raise PluginLoadError(data.get("id", plugin_dir.name), "; ".join(validation.errors))

    return manifest_from_dict(data), validation


def _import_entry_point(plugin_dir: Path, entry_point: str) -> type[BasePlugin]:
    module_path, class_name = entry_point.rsplit(":", 1)
    module_file = plugin_dir / f"{module_path.replace('.', '/')}.py"

    if not module_file.exists():
        raise PluginLoadError(plugin_dir.name, f"entry point module not found: {module_file}")

    spec = importlib.util.spec_from_file_location(f"neuralcore_plugin_{plugin_dir.name}", module_file)
    if spec is None or spec.loader is None:
        raise PluginLoadError(plugin_dir.name, f"could not create import spec for {module_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    plugin_class = getattr(module, class_name, None)
    if plugin_class is None:
        raise PluginLoadError(plugin_dir.name, f"class '{class_name}' not found in {module_path}")
    if not issubclass(plugin_class, BasePlugin):
        raise PluginLoadError(plugin_dir.name, f"'{class_name}' does not extend BasePlugin")

    return plugin_class


async def load_plugin_from_directory(
    plugin_dir: Path,
    config: dict[str, Any] | None = None,
    organization_id: str | None = None,
) -> PluginEntry:
    registry = get_plugin_registry()
    manifest, validation = load_manifest_from_directory(plugin_dir)

    for warning in validation.warnings:
        logger.warning("plugin_manifest_warning", plugin_id=manifest.id, warning=warning)

    entry = registry.register(manifest, config=config, organization_id=organization_id)

    try:
        plugin_class = _import_entry_point(plugin_dir, manifest.entry_point)
        plugin_class.manifest = manifest
        instance = plugin_class(config or {})
        await instance.on_load()

        registry.set_instance(manifest.id, instance, organization_id)
        registry.set_status(manifest.id, PluginStatus.LOADED, organization_id)
        logger.info("plugin_loaded", plugin_id=manifest.id, version=manifest.version)

    except Exception as exc:
        registry.set_status(manifest.id, PluginStatus.ERROR, organization_id, error_message=str(exc))
        logger.error("plugin_load_failed", plugin_id=manifest.id, error=str(exc))
        raise PluginLoadError(manifest.id, str(exc)) from exc

    return entry


def load_builtin_plugin_class(module_path: str, class_name: str) -> type[BasePlugin]:
    module = importlib.import_module(module_path)
    plugin_class = getattr(module, class_name)
    if not issubclass(plugin_class, BasePlugin):
        raise PluginLoadError(class_name, f"'{class_name}' does not extend BasePlugin")
    return plugin_class


async def discover_plugins_in_directory(plugins_root: str) -> list[PluginManifest]:
    root = Path(plugins_root)
    if not root.exists():
        return []

    manifests: list[PluginManifest] = []
    for plugin_dir in root.iterdir():
        if not plugin_dir.is_dir():
            continue
        try:
            manifest, _ = load_manifest_from_directory(plugin_dir)
            manifests.append(manifest)
        except PluginLoadError as exc:
            logger.warning("plugin_discovery_skip", directory=str(plugin_dir), error=str(exc))

    return manifests
