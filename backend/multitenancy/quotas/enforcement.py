# multitenancy/quotas/enforcement.py
from __future__ import annotations

from redis.asyncio import Redis

from multitenancy.quotas.limits import QuotaPeriod, QuotaType, find_quota_definition
from multitenancy.quotas.usage import UsageTracker
from multitenancy.tenant_context import TenantContext

_PERIODS: tuple[QuotaPeriod, ...] = (
    QuotaPeriod.MINUTE,
    QuotaPeriod.HOUR,
    QuotaPeriod.DAY,
    QuotaPeriod.MONTH,
    QuotaPeriod.LIFETIME,
)


class QuotaExceededError(Exception):
    def __init__(self, quota_type: QuotaType, period: QuotaPeriod, limit: int, current: int) -> None:
        self.quota_type = quota_type
        self.period = period
        self.limit = limit
        self.current = current
        super().__init__(f"Quota exceeded for {quota_type.value} ({period.value}): {current}/{limit}")


class QuotaEnforcer:
    def __init__(self, redis: Redis) -> None:
        self.usage = UsageTracker(redis)

    async def check(self, tenant: TenantContext, quota_type: QuotaType, amount: int = 1) -> None:
        for period in _PERIODS:
            definition = find_quota_definition(tenant.plan, quota_type, period)
            if definition is None:
                continue
            current = await self.usage.get_usage(tenant.organization_id, quota_type, period)
            if current + amount > definition.limit:
                raise QuotaExceededError(quota_type, period, definition.limit, current)

    async def consume(self, tenant: TenantContext, quota_type: QuotaType, amount: int = 1) -> None:
        await self.check(tenant, quota_type, amount)
        for period in _PERIODS:
            definition = find_quota_definition(tenant.plan, quota_type, period)
            if definition is None:
                continue
            await self.usage.increment(tenant.organization_id, quota_type, period, amount)

    async def usage_report(self, tenant: TenantContext) -> dict[str, int]:
        return await self.usage.snapshot(tenant.organization_id, list(QuotaType))