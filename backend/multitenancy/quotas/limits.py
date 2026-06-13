# multitenancy/quotas/limits.py
from __future__ import annotations

import enum

from multitenancy.organizations.organization import OrganizationPlan


class QuotaType(str, enum.Enum):
    API_REQUESTS = "api_requests"
    LLM_TOKENS = "llm_tokens"
    EMBEDDING_TOKENS = "embedding_tokens"
    STORAGE_BYTES = "storage_bytes"
    AGENT_RUNS = "agent_runs"
    INGESTION_DOCUMENTS = "ingestion_documents"


class QuotaPeriod(str, enum.Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    LIFETIME = "lifetime"


QUOTA_PERIOD_SECONDS: dict[QuotaPeriod, int] = {
    QuotaPeriod.MINUTE: 60,
    QuotaPeriod.HOUR: 3600,
    QuotaPeriod.DAY: 86400,
    QuotaPeriod.MONTH: 2592000,
    QuotaPeriod.LIFETIME: 0,
}


class QuotaDefinition:
    __slots__ = ("quota_type", "period", "limit")

    def __init__(self, quota_type: QuotaType, period: QuotaPeriod, limit: int) -> None:
        self.quota_type = quota_type
        self.period = period
        self.limit = limit


PLAN_QUOTAS: dict[OrganizationPlan, list[QuotaDefinition]] = {
    OrganizationPlan.FREE: [
        QuotaDefinition(QuotaType.API_REQUESTS, QuotaPeriod.MINUTE, 30),
        QuotaDefinition(QuotaType.API_REQUESTS, QuotaPeriod.MONTH, 1_000),
        QuotaDefinition(QuotaType.LLM_TOKENS, QuotaPeriod.MONTH, 500_000),
        QuotaDefinition(QuotaType.EMBEDDING_TOKENS, QuotaPeriod.MONTH, 1_000_000),
        QuotaDefinition(QuotaType.STORAGE_BYTES, QuotaPeriod.LIFETIME, 1 * 1024 ** 3),
        QuotaDefinition(QuotaType.AGENT_RUNS, QuotaPeriod.DAY, 20),
        QuotaDefinition(QuotaType.INGESTION_DOCUMENTS, QuotaPeriod.MONTH, 100),
    ],
    OrganizationPlan.STARTER: [
        QuotaDefinition(QuotaType.API_REQUESTS, QuotaPeriod.MINUTE, 120),
        QuotaDefinition(QuotaType.API_REQUESTS, QuotaPeriod.MONTH, 50_000),
        QuotaDefinition(QuotaType.LLM_TOKENS, QuotaPeriod.MONTH, 5_000_000),
        QuotaDefinition(QuotaType.EMBEDDING_TOKENS, QuotaPeriod.MONTH, 10_000_000),
        QuotaDefinition(QuotaType.STORAGE_BYTES, QuotaPeriod.LIFETIME, 25 * 1024 ** 3),
        QuotaDefinition(QuotaType.AGENT_RUNS, QuotaPeriod.DAY, 200),
        QuotaDefinition(QuotaType.INGESTION_DOCUMENTS, QuotaPeriod.MONTH, 2_000),
    ],
    OrganizationPlan.PROFESSIONAL: [
        QuotaDefinition(QuotaType.API_REQUESTS, QuotaPeriod.MINUTE, 600),
        QuotaDefinition(QuotaType.API_REQUESTS, QuotaPeriod.MONTH, 1_000_000),
        QuotaDefinition(QuotaType.LLM_TOKENS, QuotaPeriod.MONTH, 50_000_000),
        QuotaDefinition(QuotaType.EMBEDDING_TOKENS, QuotaPeriod.MONTH, 100_000_000),
        QuotaDefinition(QuotaType.STORAGE_BYTES, QuotaPeriod.LIFETIME, 250 * 1024 ** 3),
        QuotaDefinition(QuotaType.AGENT_RUNS, QuotaPeriod.DAY, 2_000),
        QuotaDefinition(QuotaType.INGESTION_DOCUMENTS, QuotaPeriod.MONTH, 50_000),
    ],
    OrganizationPlan.ENTERPRISE: [
        QuotaDefinition(QuotaType.API_REQUESTS, QuotaPeriod.MINUTE, 6_000),
        QuotaDefinition(QuotaType.API_REQUESTS, QuotaPeriod.MONTH, 50_000_000),
        QuotaDefinition(QuotaType.LLM_TOKENS, QuotaPeriod.MONTH, 1_000_000_000),
        QuotaDefinition(QuotaType.EMBEDDING_TOKENS, QuotaPeriod.MONTH, 2_000_000_000),
        QuotaDefinition(QuotaType.STORAGE_BYTES, QuotaPeriod.LIFETIME, 5000 * 1024 ** 3),
        QuotaDefinition(QuotaType.AGENT_RUNS, QuotaPeriod.DAY, 50_000),
        QuotaDefinition(QuotaType.INGESTION_DOCUMENTS, QuotaPeriod.MONTH, 1_000_000),
    ],
}


def get_quota_definitions(plan: OrganizationPlan) -> list[QuotaDefinition]:
    return PLAN_QUOTAS.get(plan, PLAN_QUOTAS[OrganizationPlan.FREE])


def find_quota_definition(plan: OrganizationPlan, quota_type: QuotaType, period: QuotaPeriod) -> QuotaDefinition | None:
    for definition in get_quota_definitions(plan):
        if definition.quota_type == quota_type and definition.period == period:
            return definition
    return None