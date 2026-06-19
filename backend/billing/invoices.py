# billing/invoices.py
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from billing.plans import get_plan_pricing
from billing.pricing import UsageLineItem, calculate_total_overage_cost
from billing.subscriptions import BillingInterval, Subscription
from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.billing.invoices")


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"


@dataclass(slots=True)
class InvoiceLineItem:
    description: str
    quantity: float
    unit_price: float
    amount: float

    def to_dict(self) -> dict[str, Any]:
        return {"description": self.description, "quantity": self.quantity, "unit_price": self.unit_price, "amount": self.amount}


@dataclass(slots=True)
class Invoice:
    id: str
    organization_id: str
    subscription_id: str
    invoice_number: str
    status: InvoiceStatus
    line_items: list[InvoiceLineItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax_amount: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    issued_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    due_at: str | None = None
    paid_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "organization_id": self.organization_id, "subscription_id": self.subscription_id,
            "invoice_number": self.invoice_number, "status": self.status.value,
            "line_items": [item.to_dict() for item in self.line_items],
            "subtotal": self.subtotal, "tax_amount": self.tax_amount, "total": self.total, "currency": self.currency,
            "issued_at": self.issued_at, "due_at": self.due_at, "paid_at": self.paid_at, "metadata": self.metadata,
        }


def _generate_invoice_number(organization_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m")
    short_id = organization_id.replace("-", "")[:6].upper()
    return f"INV-{timestamp}-{short_id}-{uuid.uuid4().hex[:6].upper()}"


class InvoiceGenerator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_subscription_invoice(
        self,
        subscription: Subscription,
        tax_rate: float = 0.0,
    ) -> Invoice:
        pricing = get_plan_pricing(subscription.plan)
        amount = pricing.monthly_price_usd if subscription.billing_interval == BillingInterval.MONTHLY else pricing.annual_price_usd

        line_items = [
            InvoiceLineItem(
                description=f"{subscription.plan.value.title()} Plan ({subscription.billing_interval.value})",
                quantity=1,
                unit_price=amount,
                amount=amount,
            )
        ]

        return self._build_invoice(subscription, line_items, tax_rate)

    def generate_usage_invoice(
        self,
        subscription: Subscription,
        usage_summary: dict[str, Any],
        plan_limits: dict[str, Any],
        tax_rate: float = 0.0,
    ) -> Invoice:
        pricing = get_plan_pricing(subscription.plan)
        base_amount = pricing.monthly_price_usd if subscription.billing_interval == BillingInterval.MONTHLY else pricing.annual_price_usd

        line_items = [
            InvoiceLineItem(description=f"{subscription.plan.value.title()} Plan (base)", quantity=1, unit_price=base_amount, amount=base_amount)
        ]

        overage = calculate_total_overage_cost(usage_summary, plan_limits)
        for item in overage["line_items"]:
            line_items.append(InvoiceLineItem(description=item["description"], quantity=item["quantity"], unit_price=item["unit_price"], amount=item["total"]))

        return self._build_invoice(subscription, line_items, tax_rate)

    def _build_invoice(self, subscription: Subscription, line_items: list[InvoiceLineItem], tax_rate: float) -> Invoice:
        subtotal = round(sum(item.amount for item in line_items), 2)
        tax_amount = round(subtotal * tax_rate, 2) if not self.settings.billing.tax_inclusive_pricing else 0.0
        total = round(subtotal + tax_amount, 2)

        now = datetime.now(timezone.utc)
        due_at = now + timedelta(days=self.settings.billing.invoice_due_days)

        invoice = Invoice(
            id=uuid.uuid4().hex,
            organization_id=subscription.organization_id,
            subscription_id=subscription.id,
            invoice_number=_generate_invoice_number(subscription.organization_id),
            status=InvoiceStatus.OPEN,
            line_items=line_items,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total=total,
            currency=self.settings.billing.default_currency,
            due_at=due_at.isoformat(),
        )
        logger.info("invoice_generated", invoice_id=invoice.id, total=total, organization_id=subscription.organization_id)
        return invoice

    def mark_paid(self, invoice: Invoice) -> Invoice:
        invoice.status = InvoiceStatus.PAID
        invoice.paid_at = datetime.now(timezone.utc).isoformat()
        return invoice

    def void_invoice(self, invoice: Invoice) -> Invoice:
        invoice.status = InvoiceStatus.VOID
        return invoice
