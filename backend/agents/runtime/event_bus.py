# agents/runtime/event_bus.py
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from monitoring.logging import get_logger

logger = get_logger("neuralcore.agents.event_bus")

Listener = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class AgentEvent(str, Enum):
    CREATED = "agent.created"
    STARTED = "agent.started"
    PAUSED = "agent.paused"
    RESUMED = "agent.resumed"
    COMPLETED = "agent.completed"
    FAILED = "agent.failed"
    TOOL_CALLED = "agent.tool.called"
    TOOL_RESULT = "agent.tool.result"
    MESSAGE_SENT = "agent.message.sent"
    MESSAGE_RECEIVED = "agent.message.received"
    MEMORY_STORED = "agent.memory.stored"
    MEMORY_RETRIEVED = "agent.memory.retrieved"
    STEP_STARTED = "agent.step.started"
    STEP_COMPLETED = "agent.step.completed"
    CHECKPOINT_SAVED = "agent.checkpoint.saved"


@dataclass(slots=True)
class EventEnvelope:
    event_id: str
    event_type: AgentEvent
    agent_id: str
    payload: dict[str, Any]
    timestamp: float

    @classmethod
    def create(cls, event_type: AgentEvent, agent_id: str, payload: dict[str, Any] | None = None) -> "EventEnvelope":
        import time
        return cls(
            event_id=uuid.uuid4().hex,
            event_type=event_type,
            agent_id=agent_id,
            payload=payload or {},
            timestamp=time.time(),
        )


class EventBus:
    def __init__(self) -> None:
        self._listeners: dict[AgentEvent, list[Listener]] = defaultdict(list)
        self._wildcard: list[Listener] = []
        self._queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=10000)
        self._running = False
        self._task: asyncio.Task | None = None

    def subscribe(self, event_type: AgentEvent, listener: Listener) -> None:
        self._listeners[event_type].append(listener)

    def subscribe_all(self, listener: Listener) -> None:
        self._wildcard.append(listener)

    def unsubscribe(self, event_type: AgentEvent, listener: Listener) -> None:
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

    async def publish(self, event: EventEnvelope) -> None:
        await self._queue.put(event)

    async def emit(
        self, event_type: AgentEvent, agent_id: str, payload: dict[str, Any] | None = None
    ) -> None:
        envelope = EventEnvelope.create(event_type, agent_id, payload)
        await self.publish(envelope)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._process_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _process_loop(self) -> None:
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                await self._dispatch(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("event_bus_dispatch_error", error=str(exc))

    async def _dispatch(self, event: EventEnvelope) -> None:
        listeners = list(self._listeners.get(event.event_type, [])) + list(self._wildcard)
        if not listeners:
            return
        results = await asyncio.gather(
            *[listener(event.event_type.value, event.payload) for listener in listeners],
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning("event_listener_error", event=event.event_type.value, error=str(result))


_global_event_bus = EventBus()


def get_event_bus() -> EventBus:
    return _global_event_bus
