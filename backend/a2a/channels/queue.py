# a2a/channels/queue.py
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

from redis.asyncio import Redis

from a2a.message import A2AMessage
from a2a.serializer import A2ASerializer
from monitoring.logging import get_logger

logger = get_logger("neuralcore.a2a.channels.queue")

_QUEUE_PREFIX = "a2a_queue"
_QUEUE_TTL = 3600
MessageCallback = Callable[[A2AMessage], Coroutine[Any, Any, None]]


class PersistentMessageQueue:
    def __init__(self, queue_id: str, redis: Redis) -> None:
        self.queue_id = queue_id
        self.redis = redis
        self._key = f"{_QUEUE_PREFIX}:{queue_id}"
        self._processing_key = f"{_QUEUE_PREFIX}:{queue_id}:processing"
        self._consumer_tasks: list[asyncio.Task[Any]] = []

    async def enqueue(self, message: A2AMessage, priority: int | None = None) -> None:
        score = time.time() - (priority or message.priority.value) * 0.001
        await self.redis.zadd(self._key, {A2ASerializer.to_json(message): score})
        await self.redis.expire(self._key, _QUEUE_TTL)

    async def dequeue(self, max_items: int = 1) -> list[A2AMessage]:
        now = time.time() + 10
        raw_items = await self.redis.zrangebyscore(self._key, "-inf", str(now), start=0, num=max_items)
        if not raw_items:
            return []
        await self.redis.zrem(self._key, *raw_items)
        messages: list[A2AMessage] = []
        for raw in raw_items:
            try:
                msg = A2ASerializer.from_json(raw)
                if not msg.is_expired():
                    await self.redis.setex(f"{self._processing_key}:{msg.message_id}", 300, raw)
                    messages.append(msg)
            except Exception:
                continue
        return messages

    async def ack(self, message_id: str) -> None:
        await self.redis.delete(f"{self._processing_key}:{message_id}")

    async def nack(self, message: A2AMessage, delay: float = 5.0) -> None:
        await self.redis.delete(f"{self._processing_key}:{message.message_id}")
        if message.can_retry():
            message.retry_count += 1
            score = time.time() + delay
            await self.redis.zadd(self._key, {A2ASerializer.to_json(message): score})

    async def depth(self) -> int:
        return int(await self.redis.zcard(self._key))

    async def start_consumer(
        self,
        callback: MessageCallback,
        concurrency: int = 4,
        poll_interval: float = 0.5,
    ) -> None:
        semaphore = asyncio.Semaphore(concurrency)

        async def _worker() -> None:
            while True:
                messages = await self.dequeue(max_items=concurrency)
                if not messages:
                    await asyncio.sleep(poll_interval)
                    continue
                async def _process(msg: A2AMessage) -> None:
                    async with semaphore:
                        try:
                            await callback(msg)
                            await self.ack(msg.message_id)
                        except Exception as exc:
                            logger.warning("queue_consumer_error", message_id=msg.message_id, error=str(exc))
                            await self.nack(msg)

                await asyncio.gather(*[_process(msg) for msg in messages])

        task = asyncio.create_task(_worker())
        self._consumer_tasks.append(task)

    async def stop_consumers(self) -> None:
        for task in self._consumer_tasks:
            task.cancel()
        self._consumer_tasks.clear()
        