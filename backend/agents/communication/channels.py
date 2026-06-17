# agents/communication/channels.py
from __future__ import annotations

import asyncio
import json
from enum import Enum
from typing import Any

from redis.asyncio import Redis

from agents.communication.messages import AgentMessage
from monitoring.logging import get_logger

logger = get_logger("neuralcore.agents.channels")

_CHANNEL_PREFIX = "a2a_channel"


class ChannelType(str, Enum):
    DIRECT = "direct"
    GROUP = "group"
    BROADCAST = "broadcast"


class AgentChannel:
    def __init__(self, channel_id: str, channel_type: ChannelType, redis: Redis) -> None:
        self.channel_id = channel_id
        self.channel_type = channel_type
        self.redis = redis
        self._member_key = f"{_CHANNEL_PREFIX}:{channel_id}:members"
        self._stream_key = f"{_CHANNEL_PREFIX}:{channel_id}:stream"

    async def add_member(self, agent_id: str) -> None:
        await self.redis.sadd(self._member_key, agent_id)
        await self.redis.expire(self._member_key, 86400)

    async def remove_member(self, agent_id: str) -> None:
        await self.redis.srem(self._member_key, agent_id)

    async def get_members(self) -> list[str]:
        return list(await self.redis.smembers(self._member_key))

    async def publish(self, message: AgentMessage) -> int:
        count = await self.redis.publish(
            self._stream_key, json.dumps(message.to_dict())
        )
        return count

    async def listen(
        self, agent_id: str, on_message: Any, timeout: float = 30.0
    ) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._stream_key)
        deadline = asyncio.get_event_loop().time() + timeout
        try:
            while asyncio.get_event_loop().time() < deadline:
                raw = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=1.0)
                if raw and raw.get("data"):
                    try:
                        msg = AgentMessage.from_dict(json.loads(raw["data"]))
                        if msg.sender_id != agent_id:
                            await on_message(msg)
                    except (json.JSONDecodeError, KeyError):
                        continue
        except asyncio.TimeoutError:
            pass
        finally:
            await pubsub.unsubscribe(self._stream_key)
            await pubsub.close()


class ChannelRegistry:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self._channels: dict[str, AgentChannel] = {}

    def get_or_create(
        self, channel_id: str, channel_type: ChannelType = ChannelType.GROUP
    ) -> AgentChannel:
        if channel_id not in self._channels:
            self._channels[channel_id] = AgentChannel(channel_id, channel_type, self.redis)
        return self._channels[channel_id]

    def get(self, channel_id: str) -> AgentChannel | None:
        return self._channels.get(channel_id)
