# memory/session.py
from __future__ import annotations

import json
import time
from typing import Any

from redis.asyncio import Redis

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.memory.session")

_PREFIX = "session"
_DEFAULT_TTL = 86400


def _key(agent_id: str, session_id: str) -> str:
    return f"{_PREFIX}:{agent_id}:{session_id}"


class SessionMemory:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings
        self._ttl = settings.agents.memory.session.ttl_seconds or _DEFAULT_TTL

    async def set(self, agent_id: str, session_id: str, key: str, value: Any) -> None:
        session_key = _key(agent_id, session_id)
        current_raw = await self.redis.get(session_key)
        data: dict[str, Any] = json.loads(current_raw) if current_raw else {}
        data[key] = value
        data["__updated_at__"] = time.time()
        await self.redis.set(session_key, json.dumps(data), ex=self._ttl)

    async def get(self, agent_id: str, session_id: str, key: str, default: Any = None) -> Any:
        session_key = _key(agent_id, session_id)
        raw = await self.redis.get(session_key)
        if raw is None:
            return default
        data: dict[str, Any] = json.loads(raw)
        return data.get(key, default)

    async def get_all(self, agent_id: str, session_id: str) -> dict[str, Any]:
        raw = await self.redis.get(_key(agent_id, session_id))
        if raw is None:
            return {}
        data: dict[str, Any] = json.loads(raw)
        return {k: v for k, v in data.items() if not k.startswith("__")}

    async def delete(self, agent_id: str, session_id: str, key: str) -> None:
        session_key = _key(agent_id, session_id)
        raw = await self.redis.get(session_key)
        if raw is None:
            return
        data: dict[str, Any] = json.loads(raw)
        data.pop(key, None)
        await self.redis.set(session_key, json.dumps(data), ex=self._ttl)

    async def clear(self, agent_id: str, session_id: str) -> None:
        await self.redis.delete(_key(agent_id, session_id))

    async def refresh_ttl(self, agent_id: str, session_id: str) -> None:
        await self.redis.expire(_key(agent_id, session_id), self._ttl)
        