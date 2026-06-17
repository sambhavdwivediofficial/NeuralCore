# agents/runtime/checkpoint.py
from __future__ import annotations

import json
import time
import uuid
from typing import Any

from redis.asyncio import Redis

from agents.runtime.state_manager import AgentState
from monitoring.logging import get_logger

logger = get_logger("neuralcore.agents.checkpoint")

_CHECKPOINT_PREFIX = "agent_checkpoint"
_CHECKPOINT_TTL = 604800


class CheckpointManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def _key(self, agent_id: str, checkpoint_id: str) -> str:
        return f"{_CHECKPOINT_PREFIX}:{agent_id}:{checkpoint_id}"

    def _index_key(self, agent_id: str) -> str:
        return f"{_CHECKPOINT_PREFIX}:index:{agent_id}"

    async def save(
        self,
        state: AgentState,
        messages: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        checkpoint_id = uuid.uuid4().hex
        payload = {
            "checkpoint_id": checkpoint_id,
            "state": state.to_dict(),
            "messages": messages or [],
            "metadata": metadata or {},
            "saved_at": time.time(),
        }
        key = self._key(state.agent_id, checkpoint_id)
        await self.redis.set(key, json.dumps(payload), ex=_CHECKPOINT_TTL)
        await self.redis.rpush(self._index_key(state.agent_id), checkpoint_id)
        await self.redis.ltrim(self._index_key(state.agent_id), -20, -1)
        logger.debug("checkpoint_saved", agent_id=state.agent_id, checkpoint_id=checkpoint_id)
        return checkpoint_id

    async def load(self, agent_id: str, checkpoint_id: str) -> dict[str, Any] | None:
        raw = await self.redis.get(self._key(agent_id, checkpoint_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def load_latest(self, agent_id: str) -> dict[str, Any] | None:
        checkpoint_ids = await self.redis.lrange(self._index_key(agent_id), -1, -1)
        if not checkpoint_ids:
            return None
        return await self.load(agent_id, checkpoint_ids[-1])

    async def list_checkpoints(self, agent_id: str) -> list[str]:
        return await self.redis.lrange(self._index_key(agent_id), 0, -1)

    async def delete(self, agent_id: str, checkpoint_id: str) -> None:
        await self.redis.delete(self._key(agent_id, checkpoint_id))

    async def clear_all(self, agent_id: str) -> None:
        checkpoint_ids = await self.list_checkpoints(agent_id)
        for cid in checkpoint_ids:
            await self.delete(agent_id, cid)
        await self.redis.delete(self._index_key(agent_id))
        