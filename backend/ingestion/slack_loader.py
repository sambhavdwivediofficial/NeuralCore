# ingestion/slack_loader.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from ingestion.base_loader import BaseLoader, SourceAuthenticationError, SourceConnectionError, SourceType
from ingestion.loader_factory import register_loader

_SLACK_API_BASE = "https://slack.com/api"


@register_loader(SourceType.SLACK)
class SlackLoader(BaseLoader):
    source_type = SourceType.SLACK

    async def load(self, source_config: dict[str, Any]) -> list[dict[str, Any]]:
        token: str = source_config["token"]
        channel_ids: list[str] = source_config.get("channel_ids", [])
        oldest: str | None = source_config.get("oldest")
        latest: str | None = source_config.get("latest")
        limit: int = source_config.get("limit", 200)
        include_replies: bool = source_config.get("include_replies", False)
        timeout: float = source_config.get("timeout", 30.0)

        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
            async def _post(method: str, params: dict[str, Any]) -> dict[str, Any]:
                response = await client.post(f"{_SLACK_API_BASE}/{method}", json=params)
                data = response.json()
                if not data.get("ok"):
                    error = data.get("error", "unknown_error")
                    if error in ("invalid_auth", "not_authed", "token_revoked"):
                        raise SourceAuthenticationError(f"Slack auth error: {error}", source_type=self.source_type.value)
                    raise SourceConnectionError(f"Slack API error: {error}", source_type=self.source_type.value)
                return data

            if not channel_ids:
                channels_data = await _post("conversations.list", {"types": "public_channel,private_channel", "limit": 100})
                channel_ids = [ch["id"] for ch in channels_data.get("channels", [])]

            async def _load_channel(channel_id: str) -> list[dict[str, Any]]:
                params: dict[str, Any] = {"channel": channel_id, "limit": min(limit, 200)}
                if oldest:
                    params["oldest"] = oldest
                if latest:
                    params["latest"] = latest

                history_data = await _post("conversations.history", params)
                messages = history_data.get("messages", [])

                if include_replies:
                    thread_ts = [msg["ts"] for msg in messages if msg.get("reply_count", 0) > 0]
                    for ts in thread_ts:
                        replies_data = await _post("conversations.replies", {"channel": channel_id, "ts": ts})
                        for reply in replies_data.get("messages", [])[1:]:
                            messages.append(reply)

                channel_name = channel_id
                try:
                    info = await _post("conversations.info", {"channel": channel_id})
                    channel_name = info.get("channel", {}).get("name", channel_id)
                except SourceConnectionError:
                    pass

                docs: list[dict[str, Any]] = []
                for msg in messages:
                    text = msg.get("text", "").strip()
                    if not text or msg.get("subtype") in ("bot_message", "channel_join", "channel_leave"):
                        continue
                    ts = msg.get("ts", "")
                    timestamp = datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat() if ts else None
                    docs.append(
                        self._build_document(
                            text,
                            metadata={
                                "source_type": self.source_type.value,
                                "channel_id": channel_id,
                                "channel_name": channel_name,
                                "user": msg.get("user"),
                                "timestamp": timestamp,
                                "thread_ts": msg.get("thread_ts"),
                                "reaction_count": len(msg.get("reactions", [])),
                            },
                            source_id=f"slack:{channel_id}:{ts}",
                        )
                    )
                return docs

            semaphore = asyncio.Semaphore(4)

            async def _safe_load(channel_id: str) -> list[dict[str, Any]]:
                async with semaphore:
                    try:
                        return await _load_channel(channel_id)
                    except Exception:
                        return []

            results = await asyncio.gather(*[_safe_load(ch) for ch in channel_ids])

        return [doc for batch in results for doc in batch]
    