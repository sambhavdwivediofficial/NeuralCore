# billing/subscriptions.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from billing.plans import get_plan_pricing
from monitoring.logging import get_logger
from multitenancy.organizations.organization import Organization, OrganizationPlan
from settings import Settings

logger = get_logger("neuralcore.billing.subscriptions")


class SubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


@dataclass(slots=True)
class Subscription:
    id: str
    organization_id: str
    plan: OrganizationPlan
    status: SubscriptionStatus
    billing_interval: BillingInterval
    provider: str
    provider_subscription_id: str | None
    current_period_start: str
    current_period_end: str
    cancel_at_period_end: bool = False
    trial_end: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "organization_id": self.organization_id, "plan": self.plan.value,
            "status": self.status.value, "billing_interval": self.billing_interval.value,
            "provider": self.provider, "provider_subscription_id": self.provider_subscription_id,
            "current_period_start": self.current_period_start, "current_period_end": self.current_period_end,
            "cancel_at_period_end": self.cancel_at_period_end, "trial_end": self.trial_end, "metadata": self.metadata,
        }


class SubscriptionManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_trial_subscription(self, organization_id: uuid.UUID, plan: OrganizationPlan = OrganizationPlan.FREE) -> Subscription:
        now = datetime.now(timezone.utc)
        trial_end = now + timedelta(days=self.settings.billing.trial_days)

        return Subscription(
            id=uuid.uuid4().hex,
            organization_id=str(organization_id),
            plan=plan,
            status=SubscriptionStatus.TRIALING,
            billing_interval=BillingInterval.MONTHLY,
            provider="none",
            provider_subscription_id=None,
            current_period_start=now.isoformat(),
            current_period_end=trial_end.isoformat(),
            trial_end=trial_end.isoformat(),
        )

    async def create_paid_subscription(
        self,
        organization_id: uuid.UUID,
        plan: OrganizationPlan,
        billing_interval: BillingInterval,
        provider: str,
        payment_method_token: str,
        customer_email: str,
    ) -> Subscription:
        from billing.payments.paypal import PayPalProvider
        from billing.payments.razorpay import RazorpayProvider
        from billing.payments.stripe import StripeProvider

        provider_map = {"stripe": StripeProvider, "razorpay": RazorpayProvider, "paypal": PayPalProvider}
        provider_cls = provider_map.get(provider)
        if provider_cls is None:
            raise ValueError(f"Unknown payment provider: {provider}")

        provider_instance = provider_cls(self.settings)
        pricing = get_plan_pricing(plan)
        amount = pricing.monthly_price_usd if billing_interval == BillingInterval.MONTHLY else pricing.annual_price_usd

        provider_subscription_id = await provider_instance.create_subscription(
            customer_email=customer_email,
            payment_method_token=payment_method_token,
            amount=amount,
            currency=self.settings.billing.default_currency,
            interval=billing_interval.value,
        )

        now = datetime.now(timezone.utc)
        period_delta = timedelta(days=30) if billing_interval == BillingInterval.MONTHLY else timedelta(days=365)

        subscription = Subscription(
            id=uuid.uuid4().hex,
            organization_id=str(organization_id),
            plan=plan,
            status=SubscriptionStatus.ACTIVE,
            billing_interval=billing_interval,
            provider=provider,
            provider_subscription_id=provider_subscription_id,
            current_period_start=now.isoformat(),
            current_period_end=(now + period_delta).isoformat(),
        )
        logger.info("subscription_created", subscription_id=subscription.id, plan=plan.value, provider=provider)
        return subscription

    async def cancel_subscription(self, subscription: Subscription, immediate: bool = False) -> Subscription:
        if subscription.provider != "none" and subscription.provider_subscription_id:
            provider_instance = self._get_provider_instance(subscription.provider)
            await provider_instance.cancel_subscription(subscription.provider_subscription_id, immediate=immediate)

        if immediate:
            subscription.status = SubscriptionStatus.CANCELLED
        else:
            subscription.cancel_at_period_end = True

        logger.info("subscription_cancelled", subscription_id=subscription.id, immediate=immediate)
        return subscription

    async def change_plan(self, subscription: Subscription, new_plan: OrganizationPlan) -> Subscription:
        if subscription.provider != "none" and subscription.provider_subscription_id:
            provider_instance = self._get_provider_instance(subscription.provider)
            new_pricing = get_plan_pricing(new_plan)
            amount = new_pricing.monthly_price_usd if subscription.billing_interval == BillingInterval.MONTHLY else new_pricing.annual_price_usd
            await provider_instance.update_subscription(subscription.provider_subscription_id, new_amount=amount)

        subscription.plan = new_plan
        logger.info("subscription_plan_changed", subscription_id=subscription.id, new_plan=new_plan.value)
        return subscription

    def _get_provider_instance(self, provider: str) -> Any:
        from billing.payments.paypal import PayPalProvider
        from billing.payments.razorpay import RazorpayProvider
        from billing.payments.stripe import StripeProvider

        provider_map = {"stripe": StripeProvider, "razorpay": RazorpayProvider, "paypal": PayPalProvider}
        provider_cls = provider_map.get(provider)
        if provider_cls is None:
            raise ValueError(f"Unknown payment provider: {provider}")
        return provider_cls(self.settings)

    def is_trial_expired(self, subscription: Subscription) -> bool:
        if subscription.trial_end is None:
            return False
        trial_end_dt = datetime.fromisoformat(subscription.trial_end)
        return datetime.now(timezone.utc) >= trial_end_dt
