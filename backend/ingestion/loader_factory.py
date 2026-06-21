# ingestion/loader_factory.py
from __future__ import annotations

import importlib

from ingestion.base_loader import BaseLoader, SourceType, UnsupportedSourceError
from settings import Settings

_LOADER_REGISTRY: dict[SourceType, type[BaseLoader]] = {}

_ALL_LOADER_MODULES: tuple[str, ...] = (
    "audio_loader",
    "image_loader",
    "bitbucket_loader",
    "confluence_loader",
    "csv_loader",
    "discord_loader",
    "docx_loader",
    "email_loader",
    "github_loader",
    "gitlab_loader",
    "html_loader",
    "jira_loader",
    "json_loader",
    "markdown_loader",
    "mongodb_loader",
    "mysql_loader",
    "notion_loader",
    "pdf_loader",
    "postgres_loader",
    "sitemap_loader",
    "slack_loader",
    "txt_loader",
    "video_loader",
    "website_loader",
    "xlsx_loader",
    "xml_loader",
    "youtube_loader",
)


def register_loader(source_type: SourceType):
    def decorator(cls: type[BaseLoader]) -> type[BaseLoader]:
        _LOADER_REGISTRY[source_type] = cls
        return cls

    return decorator


def get_loader(source_type: str | SourceType, settings: Settings) -> BaseLoader:
    resolved = SourceType(source_type) if isinstance(source_type, str) else source_type

    if resolved not in _LOADER_REGISTRY:
        for module_name in _ALL_LOADER_MODULES:
            try:
                importlib.import_module(f"ingestion.{module_name}")
            except ImportError:
                continue
            if resolved in _LOADER_REGISTRY:
                break

    loader_class = _LOADER_REGISTRY.get(resolved)
    if loader_class is None:
        raise UnsupportedSourceError(f"no loader registered for source type '{resolved.value}'", source_type=resolved.value)

    return loader_class(settings)
