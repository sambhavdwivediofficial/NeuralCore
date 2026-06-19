# billing/webhooks/razorpay_webhook.py
from __future__ import annotations

import json
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.billing.webhooks.razorpay")


async def handle_razorpay_webhook(payload: bytes, signature_header: str, settings: Settings) -> dict[str, Any]:
    from billing.payments.razorpay import RazorpayProvider

    provider = RazorpayProvider(settings)
    is_valid = provider.verify_webhook_signature(payload, signature_header)
    if not is_valid:
        raise ValueError("Invalid Razorpay webhook signature")

    event = json.loads(payload)
    event_type = event.get("event", "")

    logger.info("razorpay_webhook_received", event_type=event_type)

    handlers: dict[str, Any] = {
        "subscription.charged": _handle_subscription_charged,
        "subscription.cancelled": _handle_subscription_cancelled,
        "payment.failed": _handle_payment_failed,
    }

    handler = handlers.get(event_type)
    if handler:
        await handler(event.get("payload", {}))

    return {"received": True, "event_type": event_type}


async def _handle_subscription_charged(payload: dict[str, Any]) -> None:
    subscription_entity = payload.get("subscription", {}).get("entity", {})
    logger.info("razorpay_subscription_charged", subscription_id=subscription_entity.get("id"))


async def _handle_subscription_cancelled(payload: dict[str, Any]) -> None:
    subscription_entity = payload.get("subscription", {}).get("entity", {})
    logger.info("razorpay_subscription_cancelled", subscription_id=subscription_entity.get("id"))


async def _handle_payment_failed(payload: dict[str, Any]) -> None:
    payment_entity = payload.get("payment", {}).get("entity", {})
    logger.warning("razorpay_payment_failed", payment_id=payment_entity.get("id"))
