# ingestion/html_loader.py
from __future__ import annotations

import asyncio
from typing import Any

from ingestion.base_loader import BaseLoader, SourceType
from ingestion.loader_factory import register_loader


@register_loader(SourceType.HTML)
class HtmlLoader(BaseLoader):
    source_type = SourceType.HTML

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        html_content = await self._read_text(source_config)
        text, extra_metadata = await asyncio.to_thread(self._parse_html, html_content)
        source_id = source_config.get("file_path") or source_config.get("url")
        metadata = {"source_type": self.source_type.value, "file_path": source_config.get("file_path"), "url": source_config.get("url"), **extra_metadata}
        return [self._build_document(text, metadata=metadata, source_id=source_id)]

    @staticmethod
    def _parse_html(html_content: str) -> tuple[str, dict[str, Any]]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "lxml")
        for tag in soup(["script", "style", "noscript", "template"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else None
        description_tag = soup.find("meta", attrs={"name": "description"})
        description = description_tag.get("content") if description_tag else None

        raw_text = soup.get_text(separator="\n")
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        return "\n".join(lines), {"title": title, "description": description}
