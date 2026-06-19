# billing/plans.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from multitenancy.organizations.organization import OrganizationPlan
from multitenancy.tenant_limits import TenantLimits, get_limits_for_plan


@dataclass(slots=True, frozen=True)
class PlanPricing:
    plan: OrganizationPlan
    monthly_price_usd: float
    annual_price_usd: float
    currency: str = "USD"

    @property
    def annual_discount_percentage(self) -> float:
        full_year_at_monthly = self.monthly_price_usd * 12
        if full_year_at_monthly == 0:
            return 0.0
        return round((1 - self.annual_price_usd / full_year_at_monthly) * 100, 1)

    @property
    def annual_monthly_equivalent(self) -> float:
        return round(self.annual_price_usd / 12, 2)


PLAN_PRICING: dict[OrganizationPlan, PlanPricing] = {
    OrganizationPlan.FREE: PlanPricing(plan=OrganizationPlan.FREE, monthly_price_usd=0.0, annual_price_usd=0.0),
    OrganizationPlan.STARTER: PlanPricing(plan=OrganizationPlan.STARTER, monthly_price_usd=49.0, annual_price_usd=490.0),
    OrganizationPlan.PROFESSIONAL: PlanPricing(plan=OrganizationPlan.PROFESSIONAL, monthly_price_usd=199.0, annual_price_usd=1990.0),
    OrganizationPlan.ENTERPRISE: PlanPricing(plan=OrganizationPlan.ENTERPRISE, monthly_price_usd=999.0, annual_price_usd=9990.0),
}

PLAN_FEATURES: dict[OrganizationPlan, list[str]] = {
    OrganizationPlan.FREE: ["1 project", "3 agents", "2 knowledge bases", "500K tokens/month", "Community support"],
    OrganizationPlan.STARTER: ["5 projects", "15 agents", "10 knowledge bases", "5M tokens/month", "Email support", "GraphRAG"],
    OrganizationPlan.PROFESSIONAL: ["25 projects", "50 agents", "50 knowledge bases", "50M tokens/month", "Priority support", "Fine-tuning", "SSO"],
    OrganizationPlan.ENTERPRISE: ["Unlimited projects", "500 agents", "1000 knowledge bases", "1B tokens/month", "Dedicated support", "Custom SLA", "On-premise option"],
}


def get_plan_pricing(plan: OrganizationPlan) -> PlanPricing:
    return PLAN_PRICING.get(plan, PLAN_PRICING[OrganizationPlan.FREE])


def get_plan_features(plan: OrganizationPlan) -> list[str]:
    return PLAN_FEATURES.get(plan, [])


def get_plan_limits(plan: OrganizationPlan) -> TenantLimits:
    return get_limits_for_plan(plan)


def list_all_plans() -> list[dict[str, Any]]:
    return [
        {
            "plan": plan.value,
            "pricing": {
                "monthly_usd": get_plan_pricing(plan).monthly_price_usd,
                "annual_usd": get_plan_pricing(plan).annual_price_usd,
                "annual_discount_pct": get_plan_pricing(plan).annual_discount_percentage,
            },
            "features": get_plan_features(plan),
            "limits": get_plan_limits(plan).model_dump(),
        }
        for plan in OrganizationPlan
    ]


def can_upgrade(current_plan: OrganizationPlan, target_plan: OrganizationPlan) -> bool:
    order = list(OrganizationPlan)
    return order.index(target_plan) > order.index(current_plan)


def can_downgrade(current_plan: OrganizationPlan, target_plan: OrganizationPlan) -> bool:
    order = list(OrganizationPlan)
    return order.index(target_plan) < order.index(current_plan)
