# billing/webhooks/stripe_webhook.py
from __future__ import annotations

from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.billing.webhooks.stripe")


async def handle_stripe_webhook(payload: bytes, signature_header: str, settings: Settings) -> dict[str, Any]:
    from billing.payments.stripe import StripeProvider

    provider = StripeProvider(settings)
    event = provider.verify_webhook_signature(payload, signature_header)
    event_type = event["type"]

    logger.info("stripe_webhook_received", event_type=event_type, event_id=event["id"])

    handlers: dict[str, Any] = {
        "invoice.paid": _handle_invoice_paid,
        "invoice.payment_failed": _handle_payment_failed,
        "customer.subscription.deleted": _handle_subscription_deleted,
        "customer.subscription.updated": _handle_subscription_updated,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(event["data"]["object"])

    return {"received": True, "event_type": event_type}


async def _handle_invoice_paid(invoice_object: dict[str, Any]) -> None:
    logger.info("stripe_invoice_paid", invoice_id=invoice_object.get("id"), amount=invoice_object.get("amount_paid"))


async def _handle_payment_failed(invoice_object: dict[str, Any]) -> None:
    logger.warning("stripe_payment_failed", invoice_id=invoice_object.get("id"), customer=invoice_object.get("customer"))


async def _handle_subscription_deleted(subscription_object: dict[str, Any]) -> None:
    logger.info("stripe_subscription_deleted", subscription_id=subscription_object.get("id"))


async def _handle_subscription_updated(subscription_object: dict[str, Any]) -> None:
    logger.info("stripe_subscription_updated", subscription_id=subscription_object.get("id"), status=subscription_object.get("status"))
