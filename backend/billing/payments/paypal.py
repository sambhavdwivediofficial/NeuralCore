# billing/payments/paypal.py
from __future__ import annotations

from typing import Any

import httpx

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.billing.payments.paypal")

_PAYPAL_SANDBOX_BASE = "https://api-m.sandbox.paypal.com"
_PAYPAL_LIVE_BASE = "https://api-m.paypal.com"


class PayPalProviderError(Exception):
    pass


class PayPalProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.config = settings.billing.providers.get("paypal")
        if self.config is None or not self.config.enabled:
            raise PayPalProviderError("PayPal provider is not enabled in settings")
        if self.config.api_key is None or self.config.api_secret is None:
            raise PayPalProviderError("PayPal client_id/client_secret not configured")
        self._base_url = _PAYPAL_SANDBOX_BASE if self.config.sandbox_mode else _PAYPAL_LIVE_BASE
        self._access_token: str | None = None

    async def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        client_id = self.config.api_key.get_secret_value()
        client_secret = self.config.api_secret.get_secret_value()

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self._base_url}/v1/oauth2/token",
                auth=(client_id, client_secret),
                data={"grant_type": "client_credentials"},
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def _authed_client(self) -> httpx.AsyncClient:
        token = await self._get_access_token()
        return httpx.AsyncClient(base_url=self._base_url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=15.0)

    async def create_subscription(
        self, customer_email: str, payment_method_token: str, amount: float, currency: str, interval: str,
    ) -> str:
        async with await self._authed_client() as client:
            plan_response = await client.post(
                "/v1/billing/plans",
                json={
                    "product_id": "neuralcore_subscription",
                    "name": "NeuralCore Subscription",
                    "billing_cycles": [
                        {
                            "frequency": {"interval_unit": "MONTH" if interval == "monthly" else "YEAR", "interval_count": 1},
                            "tenure_type": "REGULAR",
                            "sequence": 1,
                            "total_cycles": 0,
                            "pricing_scheme": {"fixed_price": {"value": str(amount), "currency_code": currency.upper()}},
                        }
                    ],
                    "payment_preferences": {"auto_bill_outstanding": True},
                },
            )
            plan_data = plan_response.json()

            subscription_response = await client.post(
                "/v1/billing/subscriptions",
                json={"plan_id": plan_data["id"], "subscriber": {"email_address": customer_email}},
            )
            return subscription_response.json()["id"]

    async def cancel_subscription(self, provider_subscription_id: str, immediate: bool = False) -> None:
        async with await self._authed_client() as client:
            await client.post(f"/v1/billing/subscriptions/{provider_subscription_id}/cancel", json={"reason": "Cancelled by user"})

    async def update_subscription(self, provider_subscription_id: str, new_amount: float) -> None:
        logger.warning("paypal_subscription_update_requires_revision", subscription_id=provider_subscription_id)

    async def create_order(self, amount: float, currency: str) -> dict[str, Any]:
        async with await self._authed_client() as client:
            response = await client.post(
                "/v2/checkout/orders",
                json={"intent": "CAPTURE", "purchase_units": [{"amount": {"currency_code": currency.upper(), "value": str(amount)}}]},
            )
            data = response.json()
            return {"id": data["id"], "status": data["status"]}

    def verify_webhook_signature(self, headers: dict[str, str], body: str, webhook_id: str) -> bool:
        return bool(headers.get("paypal-transmission-sig"))
