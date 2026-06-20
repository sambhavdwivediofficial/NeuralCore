# multitenancy/tenant_limits.py
from __future__ import annotations

from pydantic import BaseModel

from multitenancy.organizations.organization import OrganizationPlan


class TenantLimits(BaseModel):
    max_projects: int
    max_agents: int
    max_knowledge_bases: int
    max_datasets: int
    max_workflows: int
    max_members: int
    max_api_keys: int
    max_storage_gb: int
    max_monthly_tokens: int
    max_monthly_requests: int
    max_concurrent_agent_runs: int


PLAN_LIMITS: dict[OrganizationPlan, TenantLimits] = {
    OrganizationPlan.FREE: TenantLimits(
        max_projects=1, max_agents=3, max_knowledge_bases=2, max_datasets=1, max_workflows=2,
        max_members=2, max_api_keys=1, max_storage_gb=1, max_monthly_tokens=500_000,
        max_monthly_requests=1_000, max_concurrent_agent_runs=1,
    ),
    OrganizationPlan.STARTER: TenantLimits(
        max_projects=5, max_agents=15, max_knowledge_bases=10, max_datasets=5, max_workflows=10,
        max_members=10, max_api_keys=5, max_storage_gb=25, max_monthly_tokens=5_000_000,
        max_monthly_requests=50_000, max_concurrent_agent_runs=3,
    ),
    OrganizationPlan.PROFESSIONAL: TenantLimits(
        max_projects=25, max_agents=50, max_knowledge_bases=50, max_datasets=25, max_workflows=50,
        max_members=50, max_api_keys=25, max_storage_gb=250, max_monthly_tokens=50_000_000,
        max_monthly_requests=1_000_000, max_concurrent_agent_runs=10,
    ),
    OrganizationPlan.ENTERPRISE: TenantLimits(
        max_projects=1000, max_agents=500, max_knowledge_bases=1000, max_datasets=500, max_workflows=500,
        max_members=500, max_api_keys=100, max_storage_gb=5000, max_monthly_tokens=1_000_000_000,
        max_monthly_requests=50_000_000, max_concurrent_agent_runs=50,
    ),
}

OWNER_UNLIMITED_LIMITS = TenantLimits(
    max_projects=999999, max_agents=999999, max_knowledge_bases=999999, max_datasets=999999,
    max_workflows=999999, max_members=999999, max_api_keys=999999, max_storage_gb=999999,
    max_monthly_tokens=999999999999, max_monthly_requests=999999999999, max_concurrent_agent_runs=999999,
)


def get_limits_for_plan(plan: OrganizationPlan, is_owner_account: bool = False) -> TenantLimits:
    if is_owner_account:
        return OWNER_UNLIMITED_LIMITS
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[OrganizationPlan.FREE])


def merge_overrides(base: TenantLimits, overrides: dict[str, int]) -> TenantLimits:
    data = base.model_dump()
    data.update({key: value for key, value in overrides.items() if key in data and value is not None})
    return TenantLimits.model_validate(data)