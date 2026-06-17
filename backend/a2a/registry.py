# a2a/registry.py
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from redis.asyncio import Redis

from a2a.protocol import ProtocolHandshake
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.registry")

_REGISTRY_PREFIX = "a2a_registry"
_AGENT_TTL = 120
_CAPABILITY_INDEX_PREFIX = "a2a_cap"


@dataclass(slots=True)
class AgentRecord:
    agent_id: str
    agent_type: str
    capabilities: list[str]
    supported_patterns: list[str]
    status: str = "active"
    registered_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    load_factor: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "capabilities": self.capabilities,
            "supported_patterns": self.supported_patterns,
            "status": self.status,
            "registered_at": self.registered_at,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
            "load_factor": self.load_factor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @classmethod
    def from_handshake(cls, handshake: ProtocolHandshake) -> "AgentRecord":
        return cls(
            agent_id=handshake.agent_id,
            agent_type=handshake.agent_type,
            capabilities=handshake.capabilities,
            supported_patterns=handshake.supported_patterns,
            metadata=handshake.metadata,
        )


class A2ARegistry:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def _agent_key(self, agent_id: str) -> str:
        return f"{_REGISTRY_PREFIX}:agent:{agent_id}"

    def _type_index_key(self, agent_type: str) -> str:
        return f"{_REGISTRY_PREFIX}:type:{agent_type}"

    def _capability_key(self, capability: str) -> str:
        return f"{_CAPABILITY_INDEX_PREFIX}:{capability}"

    async def register(self, record: AgentRecord) -> None:
        import json
        key = self._agent_key(record.agent_id)
        await self.redis.set(key, json.dumps(record.to_dict()), ex=_AGENT_TTL)
        await self.redis.sadd(self._type_index_key(record.agent_type), record.agent_id)
        await self.redis.expire(self._type_index_key(record.agent_type), _AGENT_TTL * 2)
        for capability in record.capabilities:
            await self.redis.sadd(self._capability_key(capability), record.agent_id)
            await self.redis.expire(self._capability_key(capability), _AGENT_TTL * 2)
        logger.info("agent_registered", agent_id=record.agent_id, type=record.agent_type, capabilities=record.capabilities)

    async def deregister(self, agent_id: str) -> None:
        import json
        raw = await self.redis.get(self._agent_key(agent_id))
        if raw:
            record = AgentRecord.from_dict(json.loads(raw))
            await self.redis.srem(self._type_index_key(record.agent_type), agent_id)
            for capability in record.capabilities:
                await self.redis.srem(self._capability_key(capability), agent_id)
        await self.redis.delete(self._agent_key(agent_id))
        logger.info("agent_deregistered", agent_id=agent_id)

    async def get(self, agent_id: str) -> AgentRecord | None:
        import json
        raw = await self.redis.get(self._agent_key(agent_id))
        if raw is None:
            return None
        return AgentRecord.from_dict(json.loads(raw))

    async def heartbeat(self, agent_id: str, load_factor: float = 0.0) -> bool:
        import json
        raw = await self.redis.get(self._agent_key(agent_id))
        if raw is None:
            return False
        record = AgentRecord.from_dict(json.loads(raw))
        record.last_seen = time.time()
        record.load_factor = load_factor
        await self.redis.set(self._agent_key(agent_id), json.dumps(record.to_dict()), ex=_AGENT_TTL)
        return True

    async def find_by_type(self, agent_type: str) -> list[AgentRecord]:
        agent_ids = await self.redis.smembers(self._type_index_key(agent_type))
        records: list[AgentRecord] = []
        for agent_id in agent_ids:
            record = await self.get(agent_id)
            if record and record.status == "active":
                records.append(record)
        return records

    async def find_by_capability(self, capability: str) -> list[AgentRecord]:
        agent_ids = await self.redis.smembers(self._capability_key(capability))
        records: list[AgentRecord] = []
        for agent_id in agent_ids:
            record = await self.get(agent_id)
            if record and record.status == "active":
                records.append(record)
        return sorted(records, key=lambda r: r.load_factor)

    async def find_least_loaded(self, agent_type: str) -> AgentRecord | None:
        records = await self.find_by_type(agent_type)
        if not records:
            return None
        return min(records, key=lambda r: r.load_factor)

    async def list_all(self) -> list[AgentRecord]:
        import json
        keys = []
        async for key in self.redis.scan_iter(f"{_REGISTRY_PREFIX}:agent:*"):
            keys.append(key)
        records: list[AgentRecord] = []
        for key in keys:
            raw = await self.redis.get(key)
            if raw:
                records.append(AgentRecord.from_dict(json.loads(raw)))
        return records
    