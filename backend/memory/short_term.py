# memory/short_term.py
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from redis.asyncio import Redis

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.memory.short_term")

_PREFIX = "stm"
_DEFAULT_TTL = 3600
_MAX_ENTRIES = 200


def _key(agent_id: str, session_id: str) -> str:
    return f"{_PREFIX}:{agent_id}:{session_id}"


@dataclass(slots=True)
class ShortTermEntry:
    id: str
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShortTermEntry":
        return cls(
            id=data["id"],
            role=data["role"],
            content=data["content"],
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


class ShortTermMemory:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings
        self._ttl = settings.agents.memory.short_term.ttl_seconds or _DEFAULT_TTL
        self._max_entries = settings.agents.memory.short_term.max_entries or _MAX_ENTRIES

    async def add(
        self,
        agent_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ShortTermEntry:
        entry = ShortTermEntry(
            id=uuid.uuid4().hex,
            role=role,
            content=content,
            metadata=metadata or {},
        )
        key = _key(agent_id, session_id)
        await self.redis.rpush(key, json.dumps(entry.to_dict()))
        await self.redis.ltrim(key, -self._max_entries, -1)
        await self.redis.expire(key, self._ttl)
        return entry

    async def get_all(self, agent_id: str, session_id: str) -> list[ShortTermEntry]:
        key = _key(agent_id, session_id)
        raw_items = await self.redis.lrange(key, 0, -1)
        return [ShortTermEntry.from_dict(json.loads(item)) for item in raw_items]

    async def get_last_n(self, agent_id: str, session_id: str, n: int) -> list[ShortTermEntry]:
        key = _key(agent_id, session_id)
        raw_items = await self.redis.lrange(key, -n, -1)
        return [ShortTermEntry.from_dict(json.loads(item)) for item in raw_items]

    async def clear(self, agent_id: str, session_id: str) -> None:
        await self.redis.delete(_key(agent_id, session_id))

    async def count(self, agent_id: str, session_id: str) -> int:
        return int(await self.redis.llen(_key(agent_id, session_id)))

    async def to_messages(
        self, agent_id: str, session_id: str, max_tokens: int = 4096
    ) -> list[dict[str, str]]:
        from chunking.base_chunker import count_tokens

        entries = await self.get_all(agent_id, session_id)
        messages: list[dict[str, str]] = []
        total_tokens = 0
        for entry in reversed(entries):
            tokens = count_tokens(entry.content)
            if total_tokens + tokens > max_tokens:
                break
            messages.insert(0, {"role": entry.role, "content": entry.content})
            total_tokens += tokens
        return messages
    