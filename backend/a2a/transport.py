# a2a/transport.py
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Callable, Coroutine

from redis.asyncio import Redis

from a2a.message import A2AMessage, A2AMessageStatus
from a2a.serializer import A2ASerializer
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.transport")

MessageCallback = Callable[[A2AMessage], Coroutine[Any, Any, None]]

_TRANSPORT_PREFIX = "a2a_transport"
_INBOX_TTL = 3600
_DEAD_LETTER_PREFIX = "a2a_dlq"
_DEAD_LETTER_TTL = 86400


class A2ATransport:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self._subscriptions: dict[str, list[MessageCallback]] = {}
        self._pubsub_tasks: dict[str, asyncio.Task[Any]] = {}
        self._polling_tasks: dict[str, asyncio.Task[Any]] = {}

    def _inbox_key(self, agent_id: str) -> str:
        return f"{_TRANSPORT_PREFIX}:inbox:{agent_id}"

    def _dlq_key(self, agent_id: str) -> str:
        return f"{_DEAD_LETTER_PREFIX}:{agent_id}"

    def _pubsub_channel(self, agent_id: str) -> str:
        return f"{_TRANSPORT_PREFIX}:channel:{agent_id}"

    def _broadcast_channel(self) -> str:
        return f"{_TRANSPORT_PREFIX}:broadcast"

    async def send(self, message: A2AMessage) -> bool:
        if message.is_expired():
            logger.warning("message_send_expired", message_id=message.message_id)
            return False
        if message.recipient_id is None:
            return await self.broadcast(message)
        serialized = A2ASerializer.to_json(message)
        inbox = self._inbox_key(message.recipient_id)
        score = time.time() - message.priority.value * 0.001
        await self.redis.zadd(inbox, {serialized: score})
        await self.redis.expire(inbox, _INBOX_TTL)
        await self.redis.publish(self._pubsub_channel(message.recipient_id), serialized)
        logger.debug("a2a_message_sent", from_id=message.sender_id, to_id=message.recipient_id, type=message.message_type.value)
        return True

    async def broadcast(self, message: A2AMessage) -> bool:
        serialized = A2ASerializer.to_json(message)
        count = await self.redis.publish(self._broadcast_channel(), serialized)
        logger.debug("a2a_broadcast_sent", sender_id=message.sender_id, subscribers=count)
        return True

    async def receive(self, agent_id: str, max_messages: int = 20) -> list[A2AMessage]:
        inbox = self._inbox_key(agent_id)
        now = time.time() + 10
        raw_items = await self.redis.zrangebyscore(inbox, "-inf", str(now), start=0, num=max_messages)
        if raw_items:
            await self.redis.zrem(inbox, *raw_items)
        messages: list[A2AMessage] = []
        for raw in raw_items:
            try:
                msg = A2ASerializer.from_json(raw)
                if not msg.is_expired():
                    messages.append(msg)
                else:
                    await self._send_to_dlq(agent_id, msg, reason="expired")
            except Exception:
                continue
        return messages

    async def subscribe(self, agent_id: str, callback: MessageCallback) -> None:
        if agent_id not in self._subscriptions:
            self._subscriptions[agent_id] = []
        self._subscriptions[agent_id].append(callback)
        if agent_id not in self._pubsub_tasks:
            self._pubsub_tasks[agent_id] = asyncio.create_task(
                self._pubsub_listener(agent_id)
            )

    async def subscribe_broadcast(self, callback: MessageCallback) -> None:
        channel = self._broadcast_channel()
        if channel not in self._subscriptions:
            self._subscriptions[channel] = []
        self._subscriptions[channel].append(callback)
        if channel not in self._pubsub_tasks:
            self._pubsub_tasks[channel] = asyncio.create_task(
                self._broadcast_listener()
            )

    async def start_polling(self, agent_id: str, interval: float = 0.5) -> None:
        if agent_id not in self._polling_tasks:
            self._polling_tasks[agent_id] = asyncio.create_task(
                self._poll_loop(agent_id, interval)
            )

    async def stop(self, agent_id: str) -> None:
        for task_dict in (self._pubsub_tasks, self._polling_tasks):
            task = task_dict.pop(agent_id, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._subscriptions.pop(agent_id, None)

    async def _poll_loop(self, agent_id: str, interval: float) -> None:
        while True:
            messages = await self.receive(agent_id)
            for msg in messages:
                await self._dispatch(agent_id, msg)
            await asyncio.sleep(interval)

    async def _pubsub_listener(self, agent_id: str) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._pubsub_channel(agent_id))
        try:
            async for raw_message in pubsub.listen():
                if raw_message.get("type") != "message":
                    continue
                data = raw_message.get("data", b"")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    msg = A2ASerializer.from_json(data)
                    await self._dispatch(agent_id, msg)
                except Exception as exc:
                    logger.warning("pubsub_dispatch_error", agent_id=agent_id, error=str(exc))
        except asyncio.CancelledError:
            await pubsub.unsubscribe(self._pubsub_channel(agent_id))
            await pubsub.close()

    async def _broadcast_listener(self) -> None:
        channel = self._broadcast_channel()
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw_message in pubsub.listen():
                if raw_message.get("type") != "message":
                    continue
                data = raw_message.get("data", b"")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                try:
                    msg = A2ASerializer.from_json(data)
                    await self._dispatch(channel, msg)
                except Exception:
                    continue
        except asyncio.CancelledError:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    async def _dispatch(self, target_key: str, message: A2AMessage) -> None:
        callbacks = self._subscriptions.get(target_key, [])
        if not callbacks:
            return
        results = await asyncio.gather(
            *[cb(message) for cb in callbacks], return_exceptions=True
        )
        for result in results:
            if isinstance(result, Exception):
                logger.warning("a2a_callback_error", target=target_key, error=str(result))

    async def _send_to_dlq(self, agent_id: str, message: A2AMessage, reason: str) -> None:
        dlq_key = self._dlq_key(agent_id)
        entry = json.dumps({"message": message.to_dict(), "reason": reason, "timestamp": time.time()})
        await self.redis.rpush(dlq_key, entry)
        await self.redis.ltrim(dlq_key, -1000, -1)
        await self.redis.expire(dlq_key, _DEAD_LETTER_TTL)

    async def get_dlq(self, agent_id: str, limit: int = 50) -> list[dict[str, Any]]:
        raw_items = await self.redis.lrange(self._dlq_key(agent_id), -limit, -1)
        return [json.loads(item) for item in raw_items]
    