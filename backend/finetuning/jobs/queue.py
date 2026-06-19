# finetuning/jobs/queue.py
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from redis.asyncio import Redis

_QUEUE_KEY = "finetune_jobs:queue"
_PROCESSING_KEY = "finetune_jobs:processing"


@dataclass(slots=True)
class FineTuneJobMessage:
    job_id: str
    config_dict: dict[str, Any]
    priority: int = 2
    enqueued_at: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps({"job_id": self.job_id, "config_dict": self.config_dict, "priority": self.priority, "enqueued_at": self.enqueued_at})

    @classmethod
    def from_json(cls, data: str) -> "FineTuneJobMessage":
        parsed = json.loads(data)
        return cls(**parsed)


class FineTuneJobQueue:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def enqueue(self, job_id: str, config_dict: dict[str, Any], priority: int = 2) -> None:
        message = FineTuneJobMessage(job_id=job_id, config_dict=config_dict, priority=priority)
        score = time.time() - priority * 0.001
        await self.redis.zadd(_QUEUE_KEY, {message.to_json(): score})

    async def dequeue(self) -> FineTuneJobMessage | None:
        items = await self.redis.zrange(_QUEUE_KEY, 0, 0)
        if not items:
            return None
        raw = items[0]
        await self.redis.zrem(_QUEUE_KEY, raw)
        message = FineTuneJobMessage.from_json(raw)
        await self.redis.setex(f"{_PROCESSING_KEY}:{message.job_id}", 7200, raw)
        return message

    async def complete(self, job_id: str) -> None:
        await self.redis.delete(f"{_PROCESSING_KEY}:{job_id}")

    async def queue_depth(self) -> int:
        return int(await self.redis.zcard(_QUEUE_KEY))
