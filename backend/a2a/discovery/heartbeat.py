# a2a/discovery/heartbeat.py
from __future__ import annotations

import asyncio
import time
from typing import Any

from a2a.registry import A2ARegistry
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.heartbeat")

_DEFAULT_INTERVAL = 30.0
_DEFAULT_LOAD_REPORTER: Any = None


class HeartbeatManager:
    def __init__(
        self,
        agent_id: str,
        registry: A2ARegistry,
        interval: float = _DEFAULT_INTERVAL,
    ) -> None:
        self.agent_id = agent_id
        self.registry = registry
        self.interval = interval
        self._task: asyncio.Task[Any] | None = None
        self._running = False
        self._load_factor = 0.0

    def update_load(self, load_factor: float) -> None:
        self._load_factor = min(max(load_factor, 0.0), 1.0)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info("heartbeat_started", agent_id=self.agent_id, interval=self.interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.registry.deregister(self.agent_id)
        logger.info("heartbeat_stopped", agent_id=self.agent_id)

    async def _heartbeat_loop(self) -> None:
        while self._running:
            try:
                is_known = await self.registry.heartbeat(self.agent_id, load_factor=self._load_factor)
                if not is_known:
                    logger.warning("heartbeat_agent_not_in_registry", agent_id=self.agent_id)
            except Exception as exc:
                logger.warning("heartbeat_error", agent_id=self.agent_id, error=str(exc))
            await asyncio.sleep(self.interval)
            