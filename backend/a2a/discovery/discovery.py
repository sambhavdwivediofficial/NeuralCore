# a2a/discovery/discovery.py
from __future__ import annotations

import asyncio
import time
from typing import Any

from a2a.protocol import ProtocolHandshake
from a2a.registry import A2ARegistry, AgentRecord
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.discovery")


class ServiceDiscovery:
    def __init__(self, registry: A2ARegistry) -> None:
        self.registry = registry

    async def announce(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: list[str],
        supported_patterns: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentRecord:
        handshake = ProtocolHandshake(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=capabilities,
            supported_patterns=supported_patterns or ["direct", "broadcast"],
            metadata=metadata or {},
        )
        record = AgentRecord.from_handshake(handshake)
        await self.registry.register(record)
        logger.info("agent_announced", agent_id=agent_id, capabilities=capabilities)
        return record

    async def discover_by_capability(self, capability: str) -> list[AgentRecord]:
        return await self.registry.find_by_capability(capability)

    async def discover_by_type(self, agent_type: str) -> list[AgentRecord]:
        return await self.registry.find_by_type(agent_type)

    async def discover_all(self) -> list[AgentRecord]:
        return await self.registry.list_all()

    async def select_agent(
        self,
        capability: str | None = None,
        agent_type: str | None = None,
        strategy: str = "least_loaded",
    ) -> AgentRecord | None:
        if capability:
            candidates = await self.discover_by_capability(capability)
        elif agent_type:
            candidates = await self.discover_by_type(agent_type)
        else:
            candidates = await self.discover_all()

        if not candidates:
            return None

        if strategy == "least_loaded":
            return min(candidates, key=lambda r: r.load_factor)
        if strategy == "random":
            import random
            return random.choice(candidates)
        if strategy == "newest":
            return max(candidates, key=lambda r: r.registered_at)

        return candidates[0]
    