# agents/agent_manager.py
from __future__ import annotations

import uuid
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from agents.communication.broker import AgentMessageBroker
from agents.communication.channels import ChannelRegistry
from agents.communication.router import AgentRouter
from agents.runtime.checkpoint import CheckpointManager
from agents.runtime.event_bus import get_event_bus
from agents.runtime.lifecycle import AgentLifecycleManager
from agents.runtime.runtime import AgentRuntime
from agents.runtime.scheduler import AgentScheduler, TaskPriority
from agents.runtime.state_manager import AgentStateManager
from database.models.agent import Agent
from database.repositories.agent_repository import AgentRepository
from monitoring.logging import get_logger
from multitenancy.tenant_context import TenantContext
from settings import AgentType, Settings

logger = get_logger("neuralcore.agents.manager")


class AgentManagerError(Exception):
    pass


class AgentManager:
    def __init__(
        self,
        tenant: TenantContext,
        db: AsyncSession,
        redis: Redis,
        settings: Settings,
    ) -> None:
        self.tenant = tenant
        self.settings = settings
        self._repo = AgentRepository(db)
        self._state_manager = AgentStateManager(redis)
        self._checkpoint_manager = CheckpointManager(redis)
        self._lifecycle = AgentLifecycleManager(db, self._state_manager)
        self._broker = AgentMessageBroker(redis)
        self._channel_registry = ChannelRegistry(redis)
        self._router = AgentRouter(self._broker, self._channel_registry)
        self._runtime = AgentRuntime(settings, self._state_manager, self._checkpoint_manager, self._lifecycle)
        self._scheduler = AgentScheduler(max_concurrent=settings.agents.limits.max_concurrent_tasks_per_agent)

    async def run_agent(
        self,
        agent_id: uuid.UUID,
        task: str,
        context: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> dict[str, Any]:
        agent = await self._repo.get_by_id(agent_id)
        if agent is None:
            raise AgentManagerError(f"Agent {agent_id} not found")

        active_count = await self._repo.count_by_status(
            agent.project_id, __import__("database.models.agent", fromlist=["AgentStatus"]).AgentStatus.RUNNING
        )
        if active_count >= self.settings.agents.limits.max_agents_per_tenant:
            raise AgentManagerError(f"Max concurrent agents ({self.settings.agents.limits.max_agents_per_tenant}) reached for tenant")

        task_id = await self._scheduler.submit(
            agent_id=str(agent_id),
            coro_factory=lambda: self._runtime.run(agent, task, context=context),
            priority=priority,
        )
        return {"task_id": task_id, "agent_id": str(agent_id), "status": "scheduled"}

    async def get_agent_state(self, agent_id: uuid.UUID) -> dict[str, Any] | None:
        state = await self._state_manager.load(str(agent_id))
        if state is None:
            return None
        return state.to_dict()

    async def send_message_to_agent(
        self, sender_id: str, recipient_id: str, task: str, payload: dict[str, Any] | None = None
    ) -> None:
        await self._router.send_task(
            sender_id=sender_id,
            recipient_id=recipient_id,
            task=task,
            payload=payload,
            wait_for_reply=False,
        )

    async def start_scheduler(self) -> None:
        await self._scheduler.start()

    async def stop_scheduler(self) -> None:
        await self._scheduler.stop()
