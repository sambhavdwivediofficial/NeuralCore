# agents/runtime/scheduler.py
from __future__ import annotations

import asyncio
import heapq
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from monitoring.logging import get_logger

logger = get_logger("neuralcore.agents.scheduler")


class TaskPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass(order=True)
class ScheduledTask:
    priority: int
    created_at: float = field(compare=False, default_factory=time.time)
    task_id: str = field(compare=False, default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = field(compare=False, default="")
    coro_factory: Callable[[], Coroutine[Any, Any, Any]] = field(compare=False, default=None)
    metadata: dict[str, Any] = field(compare=False, default_factory=dict)


class AgentScheduler:
    def __init__(
        self,
        max_concurrent: int = 10,
        poll_interval: float = 0.05,
    ) -> None:
        self._heap: list[ScheduledTask] = []
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running_tasks: dict[str, asyncio.Task[Any]] = {}
        self._poll_interval = poll_interval
        self._running = False
        self._loop_task: asyncio.Task[Any] | None = None

    async def submit(
        self,
        agent_id: str,
        coro_factory: Callable[[], Coroutine[Any, Any, Any]],
        priority: TaskPriority = TaskPriority.NORMAL,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        task = ScheduledTask(
            priority=priority.value,
            agent_id=agent_id,
            coro_factory=coro_factory,
            metadata=metadata or {},
        )
        heapq.heappush(self._heap, task)
        logger.debug("task_submitted", agent_id=agent_id, task_id=task.task_id, priority=priority.name)
        return task.task_id

    async def start(self) -> None:
        self._running = True
        self._loop_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        for task in self._running_tasks.values():
            task.cancel()

    async def _dispatch_loop(self) -> None:
        while self._running:
            if self._heap:
                scheduled_task = heapq.heappop(self._heap)
                asyncio_task = asyncio.create_task(self._run_task(scheduled_task))
                self._running_tasks[scheduled_task.task_id] = asyncio_task
                asyncio_task.add_done_callback(lambda t, tid=scheduled_task.task_id: self._running_tasks.pop(tid, None))
            await asyncio.sleep(self._poll_interval)

    async def _run_task(self, scheduled_task: ScheduledTask) -> Any:
        async with self._semaphore:
            try:
                return await scheduled_task.coro_factory()
            except Exception as exc:
                logger.error("scheduled_task_failed", task_id=scheduled_task.task_id, agent_id=scheduled_task.agent_id, error=str(exc))
                raise

    @property
    def queue_size(self) -> int:
        return len(self._heap)

    @property
    def running_count(self) -> int:
        return len(self._running_tasks)
    