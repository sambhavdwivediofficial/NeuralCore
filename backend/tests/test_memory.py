# tests/test_memory.py
from __future__ import annotations

import time
import uuid

import pytest

from memory.memory_manager import MemoryContext
from memory.session import SessionMemory
from memory.short_term import ShortTermEntry, ShortTermMemory

pytestmark = pytest.mark.unit


class TestShortTermEntry:
    def test_to_dict_roundtrip(self) -> None:
        entry = ShortTermEntry(id="e1", role="user", content="hello", timestamp=time.time(), metadata={"k": "v"})
        data = entry.to_dict()
        restored = ShortTermEntry.from_dict(data)
        assert restored.id == entry.id
        assert restored.role == entry.role
        assert restored.content == entry.content


class TestShortTermMemory:
    @pytest.mark.asyncio
    async def test_add_and_retrieve(self, fake_redis, test_settings) -> None:
        memory = ShortTermMemory(fake_redis, test_settings)
        agent_id = uuid.uuid4().hex
        session_id = "session_1"

        await memory.add(agent_id, session_id, "user", "Hello there")
        await memory.add(agent_id, session_id, "assistant", "Hi! How can I help?")

        entries = await memory.get_all(agent_id, session_id)
        assert len(entries) == 2
        assert entries[0].content == "Hello there"
        assert entries[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_get_last_n(self, fake_redis, test_settings) -> None:
        memory = ShortTermMemory(fake_redis, test_settings)
        agent_id = uuid.uuid4().hex
        session_id = "session_1"

        for i in range(5):
            await memory.add(agent_id, session_id, "user", f"message {i}")

        last_two = await memory.get_last_n(agent_id, session_id, 2)
        assert len(last_two) == 2
        assert last_two[-1].content == "message 4"

    @pytest.mark.asyncio
    async def test_clear(self, fake_redis, test_settings) -> None:
        memory = ShortTermMemory(fake_redis, test_settings)
        agent_id = uuid.uuid4().hex
        session_id = "session_1"

        await memory.add(agent_id, session_id, "user", "test")
        assert await memory.count(agent_id, session_id) == 1

        await memory.clear(agent_id, session_id)
        assert await memory.count(agent_id, session_id) == 0

    @pytest.mark.asyncio
    async def test_to_messages_respects_token_budget(self, fake_redis, test_settings) -> None:
        memory = ShortTermMemory(fake_redis, test_settings)
        agent_id = uuid.uuid4().hex
        session_id = "session_1"

        for i in range(20):
            await memory.add(agent_id, session_id, "user", f"This is message number {i} with some content")

        messages = await memory.to_messages(agent_id, session_id, max_tokens=50)
        assert len(messages) < 20
        assert len(messages) > 0


class TestSessionMemory:
    @pytest.mark.asyncio
    async def test_set_and_get(self, fake_redis, test_settings) -> None:
        memory = SessionMemory(fake_redis, test_settings)
        agent_id = uuid.uuid4().hex
        session_id = "session_1"

        await memory.set(agent_id, session_id, "user_name", "Sambhav")
        value = await memory.get(agent_id, session_id, "user_name")
        assert value == "Sambhav"

    @pytest.mark.asyncio
    async def test_get_missing_key_returns_default(self, fake_redis, test_settings) -> None:
        memory = SessionMemory(fake_redis, test_settings)
        value = await memory.get(uuid.uuid4().hex, "s1", "missing_key", default="fallback")
        assert value == "fallback"

    @pytest.mark.asyncio
    async def test_delete_key(self, fake_redis, test_settings) -> None:
        memory = SessionMemory(fake_redis, test_settings)
        agent_id = uuid.uuid4().hex
        session_id = "session_1"

        await memory.set(agent_id, session_id, "key1", "value1")
        await memory.delete(agent_id, session_id, "key1")
        value = await memory.get(agent_id, session_id, "key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_get_all_excludes_internal_keys(self, fake_redis, test_settings) -> None:
        memory = SessionMemory(fake_redis, test_settings)
        agent_id = uuid.uuid4().hex
        session_id = "session_1"

        await memory.set(agent_id, session_id, "visible_key", "value")
        all_vars = await memory.get_all(agent_id, session_id)
        assert "visible_key" in all_vars
        assert "__updated_at__" not in all_vars


class TestMemoryContext:
    def test_default_construction(self) -> None:
        context = MemoryContext()
        assert context.short_term == []
        assert context.total_tokens_used == 0

    def test_with_data(self) -> None:
        context = MemoryContext(short_term=[{"role": "user", "content": "hi"}], total_tokens_used=5)
        assert len(context.short_term) == 1
        assert context.total_tokens_used == 5
