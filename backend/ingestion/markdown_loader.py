# ingestion/markdown_loader.py
from __future__ import annotations

from typing import Any

import yaml

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.MARKDOWN)
class MarkdownLoader(BaseLoader):
    source_type = SourceType.MARKDOWN

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        raw_text = await self._read_text(source_config)
        front_matter, content = self._extract_front_matter(raw_text)
        source_id = source_config.get("file_path")
        metadata = {"source_type": self.source_type.value, "file_path": source_id, **front_matter}
        return [self._build_document(content.strip(), metadata=metadata, source_id=source_id)]

    @staticmethod
    def _extract_front_matter(text: str) -> tuple[dict[str, Any], str]:
        if not text.startswith("---"):
            return {}, text

        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, text

        try:
            parsed = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            return {}, text

        front_matter = parsed if isinstance(parsed, dict) else {}
        return front_matter, parts[2]
