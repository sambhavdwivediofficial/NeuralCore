# billing/payments/razorpay.py
from __future__ import annotations

import hashlib
import hmac
from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.billing.payments.razorpay")


class RazorpayProviderError(Exception):
    pass


class RazorpayProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.config = settings.billing.providers.get("razorpay")
        if self.config is None or not self.config.enabled:
            raise RazorpayProviderError("Razorpay provider is not enabled in settings")
        self._client = self._build_client()

    def _build_client(self) -> Any:
        try:
            import razorpay
        except ImportError as exc:
            raise ImportError("razorpay SDK not installed; run: pip install razorpay") from exc

        if self.config.api_key is None or self.config.api_secret is None:
            raise RazorpayProviderError("Razorpay API key/secret not configured")

        return razorpay.Client(auth=(self.config.api_key.get_secret_value(), self.config.api_secret.get_secret_value()))

    async def create_customer(self, email: str, name: str | None = None) -> str:
        import asyncio
        customer = await asyncio.to_thread(self._client.customer.create, {"email": email, "name": name or email})
        return customer["id"]

    async def create_subscription(
        self, customer_email: str, payment_method_token: str, amount: float, currency: str, interval: str,
    ) -> str:
        import asyncio

        plan = await asyncio.to_thread(
            self._client.plan.create,
            {
                "period": "monthly" if interval == "monthly" else "yearly",
                "interval": 1,
                "item": {"name": "NeuralCore Subscription", "amount": int(amount * 100), "currency": currency.upper()},
            },
        )

        subscription = await asyncio.to_thread(
            self._client.subscription.create,
            {"plan_id": plan["id"], "customer_notify": 1, "total_count": 12 if interval == "monthly" else 1},
        )
        return subscription["id"]

    async def cancel_subscription(self, provider_subscription_id: str, immediate: bool = False) -> None:
        import asyncio
        await asyncio.to_thread(
            self._client.subscription.cancel, provider_subscription_id, {"cancel_at_cycle_end": 0 if immediate else 1},
        )

    async def update_subscription(self, provider_subscription_id: str, new_amount: float) -> None:
        logger.warning("razorpay_subscription_update_requires_new_plan", subscription_id=provider_subscription_id)

    async def create_payment_order(self, amount: float, currency: str, receipt: str) -> dict[str, Any]:
        import asyncio
        order = await asyncio.to_thread(
            self._client.order.create, {"amount": int(amount * 100), "currency": currency.upper(), "receipt": receipt},
        )
        return {"id": order["id"], "amount": order["amount"], "currency": order["currency"], "status": order["status"]}

    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> bool:
        if self.config.webhook_secret is None:
            raise RazorpayProviderError("Razorpay webhook secret is not configured")
        expected = hmac.new(
            self.config.webhook_secret.get_secret_value().encode("utf-8"), payload, hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)
