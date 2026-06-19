# billing/payments/stripe.py
from __future__ import annotations

from typing import Any

from monitoring.logging import get_logger
from settings import Settings

logger = get_logger("neuralcore.billing.payments.stripe")


class StripeProviderError(Exception):
    pass


class StripeProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.config = settings.billing.providers.get("stripe")
        if self.config is None or not self.config.enabled:
            raise StripeProviderError("Stripe provider is not enabled in settings")
        self._client = self._build_client()

    def _build_client(self) -> Any:
        try:
            import stripe
        except ImportError as exc:
            raise ImportError("stripe SDK not installed; run: pip install stripe") from exc

        if self.config.api_key is None:
            raise StripeProviderError("Stripe API key is not configured")
        stripe.api_key = self.config.api_key.get_secret_value()
        return stripe

    async def create_customer(self, email: str, name: str | None = None) -> str:
        import asyncio
        customer = await asyncio.to_thread(self._client.Customer.create, email=email, name=name)
        return customer.id

    async def create_subscription(
        self, customer_email: str, payment_method_token: str, amount: float, currency: str, interval: str,
    ) -> str:
        import asyncio

        customer_id = await self.create_customer(customer_email)

        await asyncio.to_thread(
            self._client.PaymentMethod.attach, payment_method_token, customer=customer_id,
        )
        await asyncio.to_thread(
            self._client.Customer.modify, customer_id, invoice_settings={"default_payment_method": payment_method_token},
        )

        price = await asyncio.to_thread(
            self._client.Price.create,
            unit_amount=int(amount * 100),
            currency=currency.lower(),
            recurring={"interval": "month" if interval == "monthly" else "year"},
            product_data={"name": "NeuralCore Subscription"},
        )

        subscription = await asyncio.to_thread(
            self._client.Subscription.create, customer=customer_id, items=[{"price": price.id}],
        )
        return subscription.id

    async def cancel_subscription(self, provider_subscription_id: str, immediate: bool = False) -> None:
        import asyncio
        if immediate:
            await asyncio.to_thread(self._client.Subscription.delete, provider_subscription_id)
        else:
            await asyncio.to_thread(self._client.Subscription.modify, provider_subscription_id, cancel_at_period_end=True)

    async def update_subscription(self, provider_subscription_id: str, new_amount: float) -> None:
        import asyncio
        subscription = await asyncio.to_thread(self._client.Subscription.retrieve, provider_subscription_id)
        item_id = subscription["items"]["data"][0]["id"]

        price = await asyncio.to_thread(
            self._client.Price.create,
            unit_amount=int(new_amount * 100),
            currency=self.settings.billing.default_currency.lower(),
            recurring={"interval": "month"},
            product_data={"name": "NeuralCore Subscription (updated)"},
        )
        await asyncio.to_thread(
            self._client.Subscription.modify, provider_subscription_id, items=[{"id": item_id, "price": price.id}],
        )

    async def create_payment_intent(self, amount: float, currency: str, customer_id: str | None = None) -> dict[str, Any]:
        import asyncio
        intent = await asyncio.to_thread(
            self._client.PaymentIntent.create,
            amount=int(amount * 100), currency=currency.lower(), customer=customer_id,
        )
        return {"id": intent.id, "client_secret": intent.client_secret, "status": intent.status}

    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> Any:
        if self.config.webhook_secret is None:
            raise StripeProviderError("Stripe webhook secret is not configured")
        return self._client.Webhook.construct_event(payload, signature_header, self.config.webhook_secret.get_secret_value())
