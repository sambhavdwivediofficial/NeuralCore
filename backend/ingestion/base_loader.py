# ingestion/base_loader.py
from __future__ import annotations

import base64
import enum
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from settings import Settings


class SourceType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    XLSX = "xlsx"
    AUDIO = "audio"
    VIDEO = "video"
    IMAGE = "image"
    EMAIL = "email"
    WEBSITE = "website"
    SITEMAP = "sitemap"
    YOUTUBE = "youtube"
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    NOTION = "notion"
    CONFLUENCE = "confluence"
    JIRA = "jira"
    SLACK = "slack"
    DISCORD = "discord"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class LoaderError(Exception):
    def __init__(self, message: str, source_type: str) -> None:
        self.source_type = source_type
        super().__init__(f"[{source_type}] {message}")


class SourceNotFoundError(LoaderError):
    pass


class SourceAuthenticationError(LoaderError):
    pass


class SourceConnectionError(LoaderError):
    pass


class UnsupportedSourceError(LoaderError):
    pass


class BaseLoader(ABC):
    source_type: SourceType

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]: ...

    def _build_document(
        self, text: str, metadata: dict[str, Any] | None = None, source_id: str | None = None
    ) -> dict[str, Any]:
        return {
            "text": text,
            "metadata": {"loaded_at": datetime.now(timezone.utc).isoformat(), **(metadata or {})},
            "source_id": source_id,
        }

    async def _read_bytes(self, source_config: dict[str, Any]) -> bytes:
        import asyncio

        if "content_base64" in source_config:
            return base64.b64decode(source_config["content_base64"])
        if "file_path" in source_config:
            path = Path(source_config["file_path"])
            if not path.is_file():
                raise SourceNotFoundError(f"file not found: {path}", source_type=self.source_type.value)
            return await asyncio.to_thread(path.read_bytes)
        raise LoaderError("source_config must contain 'file_path' or 'content_base64'", source_type=self.source_type.value)

    async def _read_text(self, source_config: dict[str, Any], encoding: str = "utf-8") -> str:
        if "content" in source_config:
            return source_config["content"]
        raw = await self._read_bytes(source_config)
        return raw.decode(encoding, errors="replace")
