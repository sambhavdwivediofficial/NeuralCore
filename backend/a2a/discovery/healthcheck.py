# a2a/discovery/healthcheck.py
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any

from a2a.registry import A2ARegistry, AgentRecord
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.healthcheck")

_STALE_THRESHOLD = 120.0


@dataclass(slots=True, frozen=True)
class AgentHealthStatus:
    agent_id: str
    is_healthy: bool
    last_seen: float
    staleness_seconds: float
    agent_type: str
    load_factor: float


class A2AHealthChecker:
    def __init__(self, registry: A2ARegistry) -> None:
        self.registry = registry

    async def check_agent(self, agent_id: str) -> AgentHealthStatus | None:
        record = await self.registry.get(agent_id)
        if record is None:
            return None
        now = time.time()
        staleness = now - record.last_seen
        return AgentHealthStatus(
            agent_id=agent_id,
            is_healthy=staleness < _STALE_THRESHOLD and record.status == "active",
            last_seen=record.last_seen,
            staleness_seconds=staleness,
            agent_type=record.agent_type,
            load_factor=record.load_factor,
        )

    async def check_all(self) -> list[AgentHealthStatus]:
        records = await self.registry.list_all()
        results = await asyncio.gather(*[self.check_agent(r.agent_id) for r in records])
        return [r for r in results if r is not None]

    async def get_unhealthy_agents(self) -> list[AgentHealthStatus]:
        statuses = await self.check_all()
        return [s for s in statuses if not s.is_healthy]

    async def prune_stale_agents(self) -> int:
        unhealthy = await self.get_unhealthy_agents()
        for status in unhealthy:
            await self.registry.deregister(status.agent_id)
            logger.info("stale_agent_pruned", agent_id=status.agent_id, staleness=status.staleness_seconds)
        return len(unhealthy)
    