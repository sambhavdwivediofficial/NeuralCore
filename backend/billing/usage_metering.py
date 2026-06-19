# billing/usage_metering.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from monitoring.logging import get_logger
from multitenancy.quotas.usage import UsageTracker
from multitenancy.quotas.limits import QuotaPeriod, QuotaType

logger = get_logger("neuralcore.billing.usage_metering")


class UsageMeter:
    def __init__(self, usage_tracker: UsageTracker) -> None:
        self.usage_tracker = usage_tracker

    async def meter_llm_usage(self, organization_id: uuid.UUID, prompt_tokens: int, completion_tokens: int) -> None:
        await self.usage_tracker.increment(organization_id, QuotaType.LLM_TOKENS, QuotaPeriod.MONTH, prompt_tokens + completion_tokens)
        await self.usage_tracker.increment(organization_id, QuotaType.LLM_TOKENS, QuotaPeriod.DAY, prompt_tokens + completion_tokens)

    async def meter_embedding_usage(self, organization_id: uuid.UUID, token_count: int) -> None:
        await self.usage_tracker.increment(organization_id, QuotaType.EMBEDDING_TOKENS, QuotaPeriod.MONTH, token_count)

    async def meter_api_call(self, organization_id: uuid.UUID) -> None:
        await self.usage_tracker.increment(organization_id, QuotaType.API_REQUESTS, QuotaPeriod.MONTH, 1)
        await self.usage_tracker.increment(organization_id, QuotaType.API_REQUESTS, QuotaPeriod.MINUTE, 1)

    async def meter_agent_run(self, organization_id: uuid.UUID) -> None:
        await self.usage_tracker.increment(organization_id, QuotaType.AGENT_RUNS, QuotaPeriod.DAY, 1)

    async def meter_document_ingestion(self, organization_id: uuid.UUID, document_count: int = 1) -> None:
        await self.usage_tracker.increment(organization_id, QuotaType.INGESTION_DOCUMENTS, QuotaPeriod.MONTH, document_count)

    async def meter_storage_delta(self, organization_id: uuid.UUID, bytes_delta: int) -> None:
        await self.usage_tracker.increment(organization_id, QuotaType.STORAGE_BYTES, QuotaPeriod.LIFETIME, bytes_delta)

    async def get_billing_period_usage(self, organization_id: uuid.UUID) -> dict[str, Any]:
        snapshot = await self.usage_tracker.snapshot(organization_id, list(QuotaType))
        return {
            "organization_id": str(organization_id),
            "period": "month",
            "total_prompt_tokens": 0,
            "total_completion_tokens": snapshot.get(f"{QuotaType.LLM_TOKENS.value}:month", 0),
            "total_embedding_tokens": snapshot.get(f"{QuotaType.EMBEDDING_TOKENS.value}:month", 0),
            "total_api_calls": snapshot.get(f"{QuotaType.API_REQUESTS.value}:month", 0),
            "total_agent_runs": snapshot.get(f"{QuotaType.AGENT_RUNS.value}:day", 0),
            "total_documents_ingested": snapshot.get(f"{QuotaType.INGESTION_DOCUMENTS.value}:month", 0),
            "total_storage_bytes": snapshot.get(f"{QuotaType.STORAGE_BYTES.value}:lifetime", 0),
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
        }
