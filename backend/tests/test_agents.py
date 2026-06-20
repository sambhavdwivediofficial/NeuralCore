# tests/test_agents.py
from __future__ import annotations

import uuid

import pytest

from agents.communication.messages import AgentMessage, MessagePriority, MessageType
from agents.runtime.event_bus import AgentEvent, EventBus, EventEnvelope
from agents.runtime.state_manager import AgentState, AgentStateManager
from database.models.agent import AgentStatus

pytestmark = pytest.mark.unit


class TestAgentMessage:
    def test_create_task(self) -> None:
        msg = AgentMessage.create_task(sender_id="a1", recipient_id="a2", task_description="Do something")
        assert msg.message_type == MessageType.TASK
        assert msg.sender_id == "a1"
        assert msg.recipient_id == "a2"
        assert not msg.is_expired()

    def test_serialization_roundtrip(self) -> None:
        msg = AgentMessage.create_task(sender_id="a1", recipient_id="a2", task_description="Test task")
        data = msg.to_dict()
        restored = AgentMessage.from_dict(data)
        assert restored.message_id == msg.message_id
        assert restored.content == msg.content

    def test_broadcast_has_no_recipient(self) -> None:
        msg = AgentMessage.create_broadcast(sender_id="a1", content="Hello all")
        assert msg.recipient_id is None
        assert msg.message_type == MessageType.BROADCAST

    def test_expiry(self) -> None:
        import time
        msg = AgentMessage.create_task(sender_id="a1", recipient_id="a2", task_description="task")
        msg.ttl = 0
        msg.timestamp = time.time() - 1
        assert msg.is_expired()


class TestEventBus:
    @pytest.mark.asyncio
    async def test_emit_and_dispatch(self) -> None:
        bus = EventBus()
        received: list[dict] = []

        async def _handler(event_type: str, payload: dict) -> None:
            received.append(payload)

        bus.subscribe(AgentEvent.CREATED, _handler)
        await bus.start()
        try:
            await bus.emit(AgentEvent.CREATED, "agent_1", {"task": "test"})
            import asyncio
            await asyncio.sleep(0.3)
            assert len(received) == 1
            assert received[0]["task"] == "test"
        finally:
            await bus.stop()

    def test_event_envelope_creation(self) -> None:
        envelope = EventEnvelope.create(AgentEvent.STARTED, "agent_1", {"key": "value"})
        assert envelope.event_type == AgentEvent.STARTED
        assert envelope.agent_id == "agent_1"
        assert envelope.payload["key"] == "value"


class TestAgentStateManager:
    @pytest.mark.asyncio
    async def test_create_and_load_state(self, fake_redis) -> None:
        manager = AgentStateManager(fake_redis)
        agent_id = uuid.uuid4().hex

        state = await manager.create(agent_id, task_description="Test task")
        assert state.agent_id == agent_id

        loaded = await manager.load(agent_id)
        assert loaded is not None
        assert loaded.task_description == "Test task"

    @pytest.mark.asyncio
    async def test_update_status(self, fake_redis) -> None:
        manager = AgentStateManager(fake_redis)
        agent_id = uuid.uuid4().hex
        await manager.create(agent_id)

        updated = await manager.update_status(agent_id, AgentStatus.RUNNING)
        assert updated is not None
        assert updated.status == AgentStatus.RUNNING.value
        assert updated.started_at is not None

    @pytest.mark.asyncio
    async def test_increment_step(self, fake_redis) -> None:
        manager = AgentStateManager(fake_redis)
        agent_id = uuid.uuid4().hex
        await manager.create(agent_id)

        step1 = await manager.increment_step(agent_id)
        step2 = await manager.increment_step(agent_id)
        assert step1 == 1
        assert step2 == 2

    @pytest.mark.asyncio
    async def test_record_tool_call(self, fake_redis) -> None:
        manager = AgentStateManager(fake_redis)
        agent_id = uuid.uuid4().hex
        await manager.create(agent_id)

        await manager.record_tool_call(agent_id, "calculator", {"expression": "2+2"}, "4")
        state = await manager.load(agent_id)
        assert len(state.tool_calls) == 1
        assert state.tool_calls[0]["tool"] == "calculator"


class TestAgentState:
    def test_default_status(self) -> None:
        state = AgentState(agent_id="a1")
        assert state.status == AgentStatus.CREATED.value
        assert state.current_step == 0

    def test_to_dict_from_dict_roundtrip(self) -> None:
        state = AgentState(agent_id="a1", task_description="task", current_step=3)
        data = state.to_dict()
        restored = AgentState.from_dict(data)
        assert restored.agent_id == state.agent_id
        assert restored.current_step == 3
