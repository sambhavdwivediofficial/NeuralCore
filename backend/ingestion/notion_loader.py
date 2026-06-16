# ingestion/notion_loader.py
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceNotFoundError, SourceType
from ingestion.loader_factory import register_loader

_NOTION_API_BASE = "https://api.notion.com/v1"
_NOTION_VERSION = "2022-06-28"


def _blocks_to_text(blocks: list[dict[str, Any]], depth: int = 0) -> str:
    lines: list[str] = []
    indent = "  " * depth
    for block in blocks:
        block_type = block.get("type", "")
        block_data = block.get(block_type, {})

        if block_type in ("paragraph", "quote", "callout"):
            text = _rich_text_to_str(block_data.get("rich_text", []))
            if text:
                lines.append(f"{indent}{text}")

        elif block_type in ("heading_1", "heading_2", "heading_3"):
            text = _rich_text_to_str(block_data.get("rich_text", []))
            level = int(block_type[-1])
            if text:
                lines.append(f"\n{'#' * level} {text}")

        elif block_type in ("bulleted_list_item", "numbered_list_item", "to_do"):
            text = _rich_text_to_str(block_data.get("rich_text", []))
            checked = block_data.get("checked", False)
            prefix = "- [x]" if block_type == "to_do" and checked else "- [ ]" if block_type == "to_do" else "-"
            if text:
                lines.append(f"{indent}{prefix} {text}")

        elif block_type == "code":
            text = _rich_text_to_str(block_data.get("rich_text", []))
            lang = block_data.get("language", "")
            if text:
                lines.append(f"{indent}```{lang}\n{text}\n```")

        elif block_type == "table_row":
            cells = [_rich_text_to_str(cell) for cell in block_data.get("cells", [])]
            lines.append(f"{indent}| {' | '.join(cells)} |")

        elif block_type == "divider":
            lines.append(f"{indent}---")

        elif block_type == "toggle":
            text = _rich_text_to_str(block_data.get("rich_text", []))
            if text:
                lines.append(f"{indent}▶ {text}")

        if block.get("has_children"):
            lines.append(f"[children:{block['id']}]")

    return "\n".join(lines)


def _rich_text_to_str(rich_text: list[dict[str, Any]]) -> str:
    return "".join(item.get("plain_text", "") for item in rich_text)


@register_loader(SourceType.NOTION)
class NotionLoader(BaseLoader):
    source_type = SourceType.NOTION

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        token: str = source_config["token"]
        page_ids: list[str] = source_config.get("page_ids", [])
        database_id: str | None = source_config.get("database_id")
        timeout: float = source_config.get("timeout", 30.0)

        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": _NOTION_VERSION,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(headers=headers, base_url=_NOTION_API_BASE, timeout=timeout) as client:
            async def _get(path: str) -> Any:
                response = await client.get(path)
                if response.status_code == 401:
                    raise SourceAuthenticationError("invalid Notion token", source_type=self.source_type.value)
                if response.status_code == 404:
                    raise SourceNotFoundError(f"not found: {path}", source_type=self.source_type.value)
                if response.status_code >= 400:
                    raise SourceConnectionError(f"Notion API error {response.status_code}: {response.text}", source_type=self.source_type.value)
                return response.json()

            async def _post(path: str, payload: dict[str, Any]) -> Any:
                response = await client.post(path, json=payload)
                if response.status_code >= 400:
                    raise SourceConnectionError(f"Notion API error {response.status_code}", source_type=self.source_type.value)
                return response.json()

            async def _get_page_content(page_id: str) -> dict[str, Any] | None:
                page_data = await _get(f"/pages/{page_id}")
                title = _rich_text_to_str(
                    page_data.get("properties", {}).get("title", {}).get("title", [])
                    or page_data.get("properties", {}).get("Name", {}).get("title", [])
                )
                blocks_data = await _get(f"/blocks/{page_id}/children?page_size=100")
                blocks = blocks_data.get("results", [])

                child_texts: list[str] = []
                for block in blocks:
                    if block.get("has_children"):
                        child_data = await _get(f"/blocks/{block['id']}/children?page_size=100")
                        block["_children"] = child_data.get("results", [])

                text = _blocks_to_text(blocks)
                if not text.strip():
                    return None

                return self._build_document(
                    text,
                    metadata={
                        "source_type": self.source_type.value,
                        "page_id": page_id,
                        "title": title,
                        "url": page_data.get("url"),
                        "last_edited_time": page_data.get("last_edited_time"),
                    },
                    source_id=f"notion:{page_id}",
                )

            if database_id:
                db_data = await _post(f"/databases/{database_id}/query", {})
                page_ids = page_ids + [page["id"] for page in db_data.get("results", [])]

            tasks = [_get_page_content(page_id) for page_id in page_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        return [doc for doc in results if isinstance(doc, dict) and doc is not None]
    