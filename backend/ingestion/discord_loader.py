# ingestion/discord_loader.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceType
from ingestion.loader_factory import register_loader

_DISCORD_API_BASE = "https://discord.com/api/v10"


@register_loader(SourceType.DISCORD)
class DiscordLoader(BaseLoader):
    source_type = SourceType.DISCORD

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        bot_token: str = source_config["bot_token"]
        channel_ids: list[str] = source_config.get("channel_ids", [])
        guild_id: str | None = source_config.get("guild_id")
        limit: int = min(source_config.get("limit", 100), 100)
        before: str | None = source_config.get("before")
        after: str | None = source_config.get("after")
        timeout: float = source_config.get("timeout", 30.0)

        headers = {"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(headers=headers, base_url=_DISCORD_API_BASE, timeout=timeout) as client:
            async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
                response = await client.get(path, params=params)
                if response.status_code == 401:
                    raise SourceAuthenticationError("invalid Discord bot token", source_type=self.source_type.value)
                if response.status_code == 403:
                    raise SourceAuthenticationError("Discord bot lacks required permissions", source_type=self.source_type.value)
                if response.status_code >= 400:
                    raise SourceConnectionError(f"Discord API error {response.status_code}", source_type=self.source_type.value)
                return response.json()

            if guild_id and not channel_ids:
                channels_data = await _get(f"/guilds/{guild_id}/channels")
                channel_ids = [ch["id"] for ch in channels_data if ch.get("type") == 0]

            async def _load_channel(channel_id: str) -> list[dict[str, Any]]:
                params: dict[str, Any] = {"limit": limit}
                if before:
                    params["before"] = before
                if after:
                    params["after"] = after

                messages = await _get(f"/channels/{channel_id}/messages", params)
                channel_info = await _get(f"/channels/{channel_id}")
                channel_name = channel_info.get("name", channel_id)

                docs: list[dict[str, Any]] = []
                for msg in messages:
                    content = msg.get("content", "").strip()
                    if not content:
                        continue
                    ts_str = msg.get("timestamp", "")
                    try:
                        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")).isoformat() if ts_str else None
                    except ValueError:
                        ts = ts_str

                    author = msg.get("author", {})
                    docs.append(
                        self._build_document(
                            content,
                            metadata={
                                "source_type": self.source_type.value,
                                "channel_id": channel_id,
                                "channel_name": channel_name,
                                "guild_id": guild_id,
                                "message_id": msg["id"],
                                "author": f"{author.get('username', '')}#{author.get('discriminator', '0')}",
                                "timestamp": ts,
                                "attachment_count": len(msg.get("attachments", [])),
                                "reaction_count": sum(r.get("count", 0) for r in msg.get("reactions", [])),
                            },
                            source_id=f"discord:{channel_id}:{msg['id']}",
                        )
                    )
                return docs

            semaphore = asyncio.Semaphore(3)

            async def _safe_load(channel_id: str) -> list[dict[str, Any]]:
                async with semaphore:
                    try:
                        return await _load_channel(channel_id)
                    except Exception:
                        return []

            results = await asyncio.gather(*[_safe_load(ch) for ch in channel_ids])

        return [doc for batch in results for doc in batch]
    