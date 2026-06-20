# billing/billing_manager.py
from __future__ import annotations

import uuid
from typing import Any

from billing.invoices import Invoice, InvoiceGenerator
from billing.plans import can_downgrade, can_upgrade, get_plan_limits, get_plan_pricing
from billing.subscriptions import BillingInterval, Subscription, SubscriptionManager, SubscriptionStatus
from billing.usage_metering import UsageMeter
from monitoring.logging import get_logger
from multitenancy.organizations.organization import OrganizationPlan
from settings import Settings
from settings import Role

logger = get_logger("neuralcore.billing.manager")


class BillingError(Exception):
    pass


class BillingManager:
    def __init__(self, settings: Settings, usage_meter: UsageMeter) -> None:
        self.settings = settings
        self.subscription_manager = SubscriptionManager(settings)
        self.invoice_generator = InvoiceGenerator(settings)
        self.usage_meter = usage_meter

    def is_billing_exempt(self, user_role: Role) -> bool:
        return user_role == Role.SUPER_ADMIN

    async def start_subscription(
        self,
        organization_id: uuid.UUID,
        plan: OrganizationPlan,
        billing_interval: BillingInterval = BillingInterval.MONTHLY,
        provider: str | None = None,
        payment_method_token: str | None = None,
        customer_email: str | None = None,
        user_role: Any = None,
    ) -> Subscription:
        if user_role is not None and self.is_billing_exempt(user_role):
            logger.info("billing_exempt_owner_subscription", organization_id=str(organization_id))
            return self.subscription_manager.create_trial_subscription(organization_id, OrganizationPlan.ENTERPRISE)

        if plan == OrganizationPlan.FREE:
            return self.subscription_manager.create_trial_subscription(organization_id, plan)

        if not payment_method_token or not customer_email:
            raise BillingError("Payment method and customer email required for paid plans")

        target_provider = provider or self.settings.billing.default_provider
        provider_config = self.settings.billing.providers.get(target_provider)
        if provider_config is None or not provider_config.enabled:
            raise BillingError(f"Payment provider '{target_provider}' is not enabled")

        return await self.subscription_manager.create_paid_subscription(
            organization_id, plan, billing_interval, target_provider, payment_method_token, customer_email,
        )

    async def upgrade_plan(self, subscription: Subscription, new_plan: OrganizationPlan) -> Subscription:
        if not can_upgrade(subscription.plan, new_plan):
            raise BillingError(f"Cannot upgrade from {subscription.plan.value} to {new_plan.value}")
        return await self.subscription_manager.change_plan(subscription, new_plan)

    async def downgrade_plan(self, subscription: Subscription, new_plan: OrganizationPlan) -> Subscription:
        if not can_downgrade(subscription.plan, new_plan):
            raise BillingError(f"Cannot downgrade from {subscription.plan.value} to {new_plan.value}")
        return await self.subscription_manager.change_plan(subscription, new_plan)

    async def cancel_subscription(self, subscription: Subscription, immediate: bool = False) -> Subscription:
        return await self.subscription_manager.cancel_subscription(subscription, immediate)

    async def generate_monthly_invoice(self, organization_id: uuid.UUID, subscription: Subscription, user_role: Any = None) -> Invoice | None:
        if user_role is not None and self.is_billing_exempt(user_role):
            logger.info("billing_exempt_invoice_skipped", organization_id=str(organization_id))
            return None
        usage_summary = await self.usage_meter.get_billing_period_usage(organization_id)
        plan_limits = get_plan_limits(subscription.plan).model_dump()
        return self.invoice_generator.generate_usage_invoice(subscription, usage_summary, plan_limits)

    async def check_quota_and_suggest_upgrade(self, organization_id: uuid.UUID, current_plan: OrganizationPlan) -> dict[str, Any]:
        usage_summary = await self.usage_meter.get_billing_period_usage(organization_id)
        limits = get_plan_limits(current_plan)

        approaching_limit: list[str] = []
        if limits.max_monthly_tokens > 0:
            token_usage_pct = usage_summary.get("total_completion_tokens", 0) / limits.max_monthly_tokens
            if token_usage_pct >= 0.8:
                approaching_limit.append("llm_tokens")

        suggested_plan = None
        if approaching_limit:
            order = list(OrganizationPlan)
            current_index = order.index(current_plan)
            if current_index < len(order) - 1:
                suggested_plan = order[current_index + 1].value

        return {
            "organization_id": str(organization_id),
            "current_plan": current_plan.value,
            "approaching_limits": approaching_limit,
            "suggested_upgrade": suggested_plan,
            "usage_summary": usage_summary,
        }
