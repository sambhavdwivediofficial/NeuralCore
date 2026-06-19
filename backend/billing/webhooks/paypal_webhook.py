# billing/webhooks/paypal_webhook.py
from __future__ import annotations

import json
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.billing.webhooks.paypal")


async def handle_paypal_webhook(payload: bytes, headers: dict[str, str], settings: Settings) -> dict[str, Any]:
    from billing.payments.paypal import PayPalProvider

    provider = PayPalProvider(settings)
    body_str = payload.decode("utf-8")

    is_valid = provider.verify_webhook_signature(headers, body_str, webhook_id="")
    if not is_valid:
        raise ValueError("Invalid PayPal webhook signature")

    event = json.loads(body_str)
    event_type = event.get("event_type", "")

    logger.info("paypal_webhook_received", event_type=event_type)

    handlers: dict[str, Any] = {
        "BILLING.SUBSCRIPTION.ACTIVATED": _handle_subscription_activated,
        "BILLING.SUBSCRIPTION.CANCELLED": _handle_subscription_cancelled,
        "PAYMENT.SALE.DENIED": _handle_payment_denied,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(event.get("resource", {}))

    return {"received": True, "event_type": event_type}


async def _handle_subscription_activated(resource: dict[str, Any]) -> None:
    logger.info("paypal_subscription_activated", subscription_id=resource.get("id"))


async def _handle_subscription_cancelled(resource: dict[str, Any]) -> None:
    logger.info("paypal_subscription_cancelled", subscription_id=resource.get("id"))


async def _handle_payment_denied(resource: dict[str, Any]) -> None:
    logger.warning("paypal_payment_denied", sale_id=resource.get("id"))
