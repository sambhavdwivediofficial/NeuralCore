# multitenancy/quotas/usage.py
from __future__ import annotations

import time
import uuid

from redis.asyncio import Redis

from multitenancy.quotas.limits import QUOTA_PERIOD_SECONDS, QuotaPeriod, QuotaType


class UsageTracker:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    def _bucket_key(self, organization_id: uuid.UUID, quota_type: QuotaType, period: QuotaPeriod) -> str:
        if period == QuotaPeriod.LIFETIME:
            window = "lifetime"
        else:
            seconds = QUOTA_PERIOD_SECONDS[period]
            window = str(int(time.time()) // seconds)
        return f"usage:{organization_id}:{quota_type.value}:{period.value}:{window}"

    async def increment(
        self, organization_id: uuid.UUID, quota_type: QuotaType, period: QuotaPeriod, amount: int = 1
    ) -> int:
        key = self._bucket_key(organization_id, quota_type, period)
        new_value = await self.redis.incrby(key, amount)
        if new_value == amount:
            ttl = QUOTA_PERIOD_SECONDS.get(period, 0)
            if ttl > 0:
                await self.redis.expire(key, ttl * 2)
        return int(new_value)

    async def get_usage(self, organization_id: uuid.UUID, quota_type: QuotaType, period: QuotaPeriod) -> int:
        key = self._bucket_key(organization_id, quota_type, period)
        value = await self.redis.get(key)
        return int(value) if value is not None else 0

    async def reset(self, organization_id: uuid.UUID, quota_type: QuotaType, period: QuotaPeriod) -> None:
        key = self._bucket_key(organization_id, quota_type, period)
        await self.redis.delete(key)

    async def snapshot(self, organization_id: uuid.UUID, quota_types: list[QuotaType]) -> dict[str, int]:
        result: dict[str, int] = {}
        for quota_type in quota_types:
            for period in (QuotaPeriod.MINUTE, QuotaPeriod.DAY, QuotaPeriod.MONTH, QuotaPeriod.LIFETIME):
                usage = await self.get_usage(organization_id, quota_type, period)
                if usage:
                    result[f"{quota_type.value}:{period.value}"] = usage
        return result