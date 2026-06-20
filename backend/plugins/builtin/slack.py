# plugins/builtin/slack.py
from __future__ import annotations

from typing import Any

from plugins.plugin_loader import BasePlugin
from plugins.plugin_validator import PluginManifest, PluginPermission


class SlackPlugin(BasePlugin):
    manifest = PluginManifest(
        id="slack",
        name="Slack",
        version="1.0.0",
        description="Connect Slack workspaces for channel ingestion and agent notifications via Slack messages.",
        author="NeuralCore",
        entry_point="plugins.builtin.slack:SlackPlugin",
        permissions=[PluginPermission.READ_KNOWLEDGE_BASES, PluginPermission.WRITE_KNOWLEDGE_BASES, PluginPermission.NETWORK_ACCESS],
        category="communication",
        config_schema={"type": "object", "properties": {"bot_token": {"type": "string"}}, "required": ["bot_token"]},
    )

    async def on_load(self) -> None:
        self.bot_token = self.config.get("bot_token")

    async def list_channels(self) -> list[dict[str, Any]]:
        import httpx
        async with httpx.AsyncClient(headers={"Authorization": f"Bearer {self.bot_token}"}, timeout=15.0) as client:
            response = await client.get("https://slack.com/api/conversations.list", params={"types": "public_channel,private_channel"})
            data = response.json()
        return [{"id": ch["id"], "name": ch["name"]} for ch in data.get("channels", [])]

    async def ingest_channel(self, channel_id: str, knowledge_base_id: str) -> dict[str, Any]:
        from ingestion.slack_loader import SlackLoader
        from settings import get_settings

        loader = SlackLoader(get_settings())
        documents = await loader.load({"token": self.bot_token, "channel_ids": [channel_id]})
        return {"channel_id": channel_id, "knowledge_base_id": knowledge_base_id, "documents_found": len(documents)}

    async def send_notification(self, channel_id: str, message: str) -> dict[str, Any]:
        import httpx
        async with httpx.AsyncClient(headers={"Authorization": f"Bearer {self.bot_token}"}, timeout=15.0) as client:
            response = await client.post("https://slack.com/api/chat.postMessage", json={"channel": channel_id, "text": message})
            return response.json()
