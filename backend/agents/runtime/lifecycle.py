# agents/runtime/lifecycle.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agents.runtime.event_bus import AgentEvent, get_event_bus
from agents.runtime.state_manager import AgentState, AgentStateManager
from database.models.agent import Agent, AgentStatus
from database.repositories.agent_repository import AgentRepository
from monitoring.logging import get_logger

logger = get_logger("neuralcore.agents.lifecycle")


class AgentLifecycleManager:
    def __init__(self, session: AsyncSession, state_manager: AgentStateManager) -> None:
        self.repo = AgentRepository(session)
        self.state_manager = state_manager
        self.bus = get_event_bus()

    async def initialize(
        self,
        agent: Agent,
        task_description: str = "",
        session_id: str | None = None,
    ) -> AgentState:
        session = session_id or uuid.uuid4().hex
        state = await self.state_manager.create(
            agent_id=str(agent.id),
            status=AgentStatus.CREATED.value,
            max_iterations=agent.max_iterations,
            session_id=session,
            task_description=task_description,
        )
        await self.repo.update_status(agent.id, AgentStatus.CREATED)
        await self.bus.emit(AgentEvent.CREATED, str(agent.id), {"task": task_description})
        logger.info("agent_initialized", agent_id=str(agent.id), session_id=session)
        return state

    async def start(self, agent_id: uuid.UUID) -> AgentState | None:
        state = await self.state_manager.update_status(agent_id=str(agent_id), status=AgentStatus.RUNNING)
        await self.repo.update_status(agent_id, AgentStatus.RUNNING)
        await self.bus.emit(AgentEvent.STARTED, str(agent_id))
        return state

    async def pause(self, agent_id: uuid.UUID) -> AgentState | None:
        state = await self.state_manager.update_status(str(agent_id), AgentStatus.PAUSED)
        await self.repo.update_status(agent_id, AgentStatus.PAUSED)
        await self.bus.emit(AgentEvent.PAUSED, str(agent_id))
        return state

    async def complete(self, agent_id: uuid.UUID, output: str = "") -> AgentState | None:
        state = await self.state_manager.update_status(str(agent_id), AgentStatus.COMPLETED)
        await self.repo.update_status(agent_id, AgentStatus.COMPLETED)
        await self.bus.emit(AgentEvent.COMPLETED, str(agent_id), {"output": output})
        logger.info("agent_completed", agent_id=str(agent_id))
        return state

    async def fail(self, agent_id: uuid.UUID, error: str) -> AgentState | None:
        state = await self.state_manager.load(str(agent_id))
        if state:
            state.error = error
            state.status = AgentStatus.FAILED.value
            await self.state_manager.save(state)
        await self.repo.update_status(agent_id, AgentStatus.FAILED)
        await self.bus.emit(AgentEvent.FAILED, str(agent_id), {"error": error})
        logger.error("agent_failed", agent_id=str(agent_id), error=error)
        return state

    async def can_continue(self, agent_id: uuid.UUID) -> bool:
        state = await self.state_manager.load(str(agent_id))
        if state is None:
            return False
        if state.status not in (AgentStatus.RUNNING.value, AgentStatus.CREATED.value):
            return False
        return state.current_step < state.max_iterations
    