# plugins/builtin/notion.py
from __future__ import annotations

from typing import Any

from plugins.plugin_loader import BasePlugin
from plugins.plugin_validator import PluginManifest, PluginPermission


class NotionPlugin(BasePlugin):
    manifest = PluginManifest(
        id="notion",
        name="Notion",
        version="1.0.0",
        description="Connect Notion workspaces for page and database ingestion with automatic block-to-markdown conversion.",
        author="NeuralCore",
        entry_point="plugins.builtin.notion:NotionPlugin",
        permissions=[PluginPermission.READ_KNOWLEDGE_BASES, PluginPermission.WRITE_KNOWLEDGE_BASES, PluginPermission.NETWORK_ACCESS],
        category="productivity",
        config_schema={"type": "object", "properties": {"token": {"type": "string"}}, "required": ["token"]},
    )

    async def on_load(self) -> None:
        self.token = self.config.get("token")

    async def list_pages(self, query: str = "") -> list[dict[str, Any]]:
        import httpx
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.token}", "Notion-Version": "2022-06-28"}, timeout=15.0
        ) as client:
            response = await client.post("https://api.notion.com/v1/search", json={"query": query, "filter": {"property": "object", "value": "page"}})
            data = response.json()
        return [{"id": r["id"], "url": r.get("url", "")} for r in data.get("results", [])]

    async def ingest_pages(self, page_ids: list[str], knowledge_base_id: str) -> dict[str, Any]:
        from ingestion.notion_loader import NotionLoader
        from settings import get_settings

        loader = NotionLoader(get_settings())
        documents = await loader.load({"token": self.token, "page_ids": page_ids})
        return {"page_ids": page_ids, "knowledge_base_id": knowledge_base_id, "documents_found": len(documents)}
