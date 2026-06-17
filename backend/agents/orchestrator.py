# agents/orchestrator.py
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from agents.agent_manager import AgentManager
from agents.communication.messages import AgentMessage, MessageType
from agents.runtime.event_bus import AgentEvent, get_event_bus
from monitoring.logging import get_logger
from settings import AgentType, Settings

logger = get_logger("neuralcore.agents.orchestrator")


@dataclass(slots=True)
class OrchestrationPlan:
    task: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    agent_assignments: dict[str, str] = field(default_factory=dict)


class AgentOrchestrator:
    def __init__(
        self,
        tenant: Any,
        db: Any,
        redis: Any,
        settings: Settings,
    ) -> None:
        self.settings = settings
        self.manager = AgentManager(tenant=tenant, db=db, redis=redis, settings=settings)
        self.bus = get_event_bus()

    async def run_pipeline(
        self,
        task: str,
        agent_ids: list[uuid.UUID],
        context: str = "",
        max_parallel: int = 3,
    ) -> dict[str, Any]:
        semaphore = asyncio.Semaphore(max_parallel)
        results: dict[str, Any] = {}

        async def _run_one(agent_id: uuid.UUID) -> None:
            async with semaphore:
                try:
                    result = await self.manager._runtime.run(
                        agent=await self.manager._repo.get_by_id(agent_id),
                        task=task,
                        context=context,
                    )
                    results[str(agent_id)] = result
                except Exception as exc:
                    results[str(agent_id)] = {"status": "failed", "error": str(exc)}

        await asyncio.gather(*[_run_one(agent_id) for agent_id in agent_ids])
        return {
            "task": task,
            "agents_run": len(agent_ids),
            "results": results,
        }

    async def run_sequential_chain(
        self,
        initial_task: str,
        agent_ids: list[uuid.UUID],
        context: str = "",
    ) -> dict[str, Any]:
        current_input = initial_task
        chain_results: list[dict[str, Any]] = []

        for agent_id in agent_ids:
            agent = await self.manager._repo.get_by_id(agent_id)
            if agent is None:
                logger.warning("agent_not_found_in_chain", agent_id=str(agent_id))
                continue
            try:
                result = await self.manager._runtime.run(agent, current_input, context=context)
                chain_results.append({"agent_id": str(agent_id), **result})
                if result.get("output"):
                    current_input = result["output"]
            except Exception as exc:
                chain_results.append({"agent_id": str(agent_id), "status": "failed", "error": str(exc)})
                break

        return {"initial_task": initial_task, "chain_length": len(chain_results), "results": chain_results, "final_output": current_input}
