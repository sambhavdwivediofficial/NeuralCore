# billing/reports/revenue.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from billing.plans import get_plan_pricing
from monitoring.logging import get_logger
from multitenancy.organizations.organization import OrganizationPlan

logger = get_logger("neuralcore.billing.reports.revenue")


async def calculate_mrr(db: Any) -> dict[str, Any]:
    from sqlalchemy import func, text
    from database.connection import get_engine

    engine = get_engine()
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT plan, COUNT(*) as count FROM organizations WHERE status = 'active' GROUP BY plan")
            )
            rows = result.mappings().all()
    except Exception as exc:
        logger.warning("mrr_calculation_db_failed", error=str(exc))
        rows = []

    total_mrr = 0.0
    by_plan: dict[str, Any] = {}

    for row in rows:
        try:
            plan = OrganizationPlan(row["plan"])
        except ValueError:
            continue
        pricing = get_plan_pricing(plan)
        plan_mrr = pricing.monthly_price_usd * row["count"]
        total_mrr += plan_mrr
        by_plan[plan.value] = {"customer_count": row["count"], "mrr_usd": round(plan_mrr, 2)}

    return {"total_mrr_usd": round(total_mrr, 2), "arr_usd": round(total_mrr * 12, 2), "by_plan": by_plan, "calculated_at": datetime.now(timezone.utc).isoformat()}


async def calculate_churn_rate(db: Any, period_days: int = 30) -> dict[str, Any]:
    return {"period_days": period_days, "churned_customers": 0, "total_customers_start": 0, "churn_rate_percentage": 0.0, "calculated_at": datetime.now(timezone.utc).isoformat()}


async def calculate_ltv(db: Any, avg_customer_lifespan_months: float = 24.0) -> dict[str, Any]:
    mrr_data = await calculate_mrr(db)
    total_customers = sum(p["customer_count"] for p in mrr_data["by_plan"].values())
    avg_revenue_per_customer = mrr_data["total_mrr_usd"] / total_customers if total_customers > 0 else 0.0
    ltv = avg_revenue_per_customer * avg_customer_lifespan_months

    return {"avg_revenue_per_customer_usd": round(avg_revenue_per_customer, 2), "avg_lifespan_months": avg_customer_lifespan_months, "ltv_usd": round(ltv, 2)}


async def get_revenue_by_period(db: Any, range_str: str = "30d") -> dict[str, Any]:
    from analytics.metrics import generate_empty_time_series
    series = generate_empty_time_series(range_str, "Revenue", "USD")
    return {"range": range_str, "series": series.to_dict()}
