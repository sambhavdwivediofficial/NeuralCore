# billing/pricing.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_LLM_TOKEN_OVERAGE_PRICE_PER_1K = 0.002
_EMBEDDING_TOKEN_OVERAGE_PRICE_PER_1K = 0.0001
_STORAGE_OVERAGE_PRICE_PER_GB = 0.10
_API_CALL_OVERAGE_PRICE_PER_1K = 0.50


@dataclass(slots=True, frozen=True)
class UsageLineItem:
    description: str
    quantity: float
    unit_price: float
    unit: str

    @property
    def total(self) -> float:
        return round(self.quantity * self.unit_price, 4)

    def to_dict(self) -> dict[str, Any]:
        return {"description": self.description, "quantity": self.quantity, "unit": self.unit, "unit_price": self.unit_price, "total": self.total}


def calculate_token_overage_cost(tokens_used: int, tokens_included: int, token_type: str = "llm") -> UsageLineItem:
    overage_tokens = max(0, tokens_used - tokens_included)
    price_per_1k = _LLM_TOKEN_OVERAGE_PRICE_PER_1K if token_type == "llm" else _EMBEDDING_TOKEN_OVERAGE_PRICE_PER_1K
    return UsageLineItem(
        description=f"{token_type.upper()} token overage",
        quantity=round(overage_tokens / 1000, 3),
        unit_price=price_per_1k,
        unit="1K tokens",
    )


def calculate_storage_overage_cost(storage_bytes_used: int, storage_gb_included: int) -> UsageLineItem:
    storage_gb_used = storage_bytes_used / (1024 ** 3)
    overage_gb = max(0.0, storage_gb_used - storage_gb_included)
    return UsageLineItem(description="Storage overage", quantity=round(overage_gb, 3), unit_price=_STORAGE_OVERAGE_PRICE_PER_GB, unit="GB")


def calculate_api_call_overage_cost(calls_used: int, calls_included: int) -> UsageLineItem:
    overage_calls = max(0, calls_used - calls_included)
    return UsageLineItem(description="API call overage", quantity=round(overage_calls / 1000, 3), unit_price=_API_CALL_OVERAGE_PRICE_PER_1K, unit="1K calls")


def calculate_total_overage_cost(usage_summary: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
    line_items: list[UsageLineItem] = []

    llm_tokens_used = usage_summary.get("total_prompt_tokens", 0) + usage_summary.get("total_completion_tokens", 0)
    llm_tokens_included = limits.get("max_monthly_tokens", 0)
    if llm_tokens_used > llm_tokens_included:
        line_items.append(calculate_token_overage_cost(llm_tokens_used, llm_tokens_included, "llm"))

    embedding_tokens_used = usage_summary.get("total_embedding_tokens", 0)
    if embedding_tokens_used > 0:
        line_items.append(calculate_token_overage_cost(embedding_tokens_used, 0, "embedding"))

    storage_used = usage_summary.get("total_storage_bytes", 0)
    storage_included_gb = limits.get("max_storage_gb", 0)
    storage_item = calculate_storage_overage_cost(storage_used, storage_included_gb)
    if storage_item.quantity > 0:
        line_items.append(storage_item)

    calls_used = usage_summary.get("total_api_calls", 0)
    calls_included = limits.get("max_monthly_requests", 0)
    if calls_used > calls_included:
        line_items.append(calculate_api_call_overage_cost(calls_used, calls_included))

    return {
        "line_items": [item.to_dict() for item in line_items],
        "total_overage_usd": round(sum(item.total for item in line_items), 2),
    }


def prorate_amount(full_amount: float, days_used: int, days_in_period: int) -> float:
    if days_in_period <= 0:
        return 0.0
    return round(full_amount * (days_used / days_in_period), 2)


def calculate_upgrade_proration(
    old_plan_monthly_price: float,
    new_plan_monthly_price: float,
    days_remaining_in_cycle: int,
    days_in_cycle: int = 30,
) -> float:
    unused_credit = prorate_amount(old_plan_monthly_price, days_remaining_in_cycle, days_in_cycle)
    new_charge = prorate_amount(new_plan_monthly_price, days_remaining_in_cycle, days_in_cycle)
    return round(new_charge - unused_credit, 2)
