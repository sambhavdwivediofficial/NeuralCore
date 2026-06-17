# agents/runtime/state_manager.py
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from redis.asyncio import Redis

from database.models.agent import AgentStatus
from monitoring.logging import get_logger

logger = get_logger("neuralcore.agents.state_manager")

_PREFIX = "agent_state"
_DEFAULT_TTL = 86400


@dataclass
class AgentState:
    agent_id: str
    status: str = AgentStatus.CREATED.value
    current_step: int = 0
    max_iterations: int = 10
    session_id: str = ""
    task_description: str = ""
    accumulated_output: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    variables: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: float | None = None
    completed_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class AgentStateManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def _key(self, agent_id: str) -> str:
        return f"{_PREFIX}:{agent_id}"

    async def create(self, agent_id: str, **kwargs: Any) -> AgentState:
        state = AgentState(agent_id=agent_id, **kwargs)
        await self.save(state)
        return state

    async def save(self, state: AgentState) -> None:
        await self.redis.set(
            self._key(state.agent_id),
            json.dumps(state.to_dict()),
            ex=_DEFAULT_TTL,
        )

    async def load(self, agent_id: str) -> AgentState | None:
        raw = await self.redis.get(self._key(agent_id))
        if raw is None:
            return None
        return AgentState.from_dict(json.loads(raw))

    async def update_status(self, agent_id: str, status: AgentStatus) -> AgentState | None:
        state = await self.load(agent_id)
        if state is None:
            return None
        state.status = status.value
        if status == AgentStatus.RUNNING and state.started_at is None:
            state.started_at = time.time()
        if status in (AgentStatus.COMPLETED, AgentStatus.FAILED):
            state.completed_at = time.time()
        await self.save(state)
        return state

    async def increment_step(self, agent_id: str) -> int:
        state = await self.load(agent_id)
        if state is None:
            return 0
        state.current_step += 1
        await self.save(state)
        return state.current_step

    async def set_variable(self, agent_id: str, key: str, value: Any) -> None:
        state = await self.load(agent_id)
        if state is None:
            return
        state.variables[key] = value
        await self.save(state)

    async def record_tool_call(
        self, agent_id: str, tool_name: str, tool_input: Any, tool_result: Any
    ) -> None:
        state = await self.load(agent_id)
        if state is None:
            return
        state.tool_calls.append({
            "tool": tool_name,
            "input": tool_input,
            "result": tool_result,
            "timestamp": time.time(),
        })
        state.tool_calls = state.tool_calls[-100:]
        await self.save(state)

    async def delete(self, agent_id: str) -> None:
        await self.redis.delete(self._key(agent_id))
        