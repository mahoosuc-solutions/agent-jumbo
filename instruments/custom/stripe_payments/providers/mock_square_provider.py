"""Mock Square provider for testing. Returns deterministic fake data."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from instruments.custom.stripe_payments.providers.base import PaymentProvider


def _mock_id(prefix: str) -> str:
    return f"{prefix}_mock_{uuid.uuid4().hex[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _future_iso(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


class MockSquareProvider(PaymentProvider):
    """Deterministic mock Square provider. No network calls."""

    def get_provider_name(self) -> str:
        return "square"

    def create_customer(self, email: str, name: str, metadata: dict[str, Any] | None = None) -> dict:
        return {
            "id": _mock_id("sqr_cust"),
            "object": "customer",
            "email": email,
            "name": name,
            "metadata": metadata or {},
            "provider": "square",
        }

    def get_customer(self, customer_id: str) -> dict:
        return {
            "id": customer_id,
            "object": "customer",
            "email": "mock@example.com",
            "name": "Mock Square Customer",
            "provider": "square",
        }

    def create_product(self, name: str, description: str, metadata: dict[str, Any] | None = None) -> dict:
        return {
            "id": _mock_id("sqr_prod"),
            "object": "product",
            "name": name,
            "description": description,
            "variation_id": _mock_id("sqr_var"),
            "provider": "square",
        }

    def create_price(
        self,
        product_id: str,
        unit_amount_cents: int,
        currency: str = "usd",
        recurring_interval: str | None = None,
    ) -> dict:
        return {
            "id": _mock_id("sqr_price"),
            "object": "price",
            "product": product_id,
            "unit_amount": unit_amount_cents,
            "currency": currency,
            "type": "recurring" if recurring_interval else "one_time",
            "provider": "square",
        }

    def create_checkout_session(
        self,
        price_id: str,
        customer_id: str,
        mode: str = "payment",
        success_url: str = "",
        cancel_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        link_id = _mock_id("sqr_link")
        return {
            "id": link_id,
            "object": "checkout.session",
            "url": f"https://checkout.square.site/mock/{link_id}",
            "customer": customer_id,
            "mode": mode,
            "provider": "square",
        }

    def create_invoice(
        self,
        customer_id: str,
        items: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        total = sum(item.get("amount", 0) for item in items)
        return {
            "id": _mock_id("sqr_inv"),
            "object": "invoice",
            "customer": customer_id,
            "status": "draft",
            "amount_due": total,
            "currency": "usd",
            "provider": "square",
        }

    def finalize_invoice(self, invoice_id: str) -> dict:
        return {
            "id": invoice_id,
            "object": "invoice",
            "status": "unpaid",
            "provider": "square",
        }

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        return {
            "id": _mock_id("sqr_sub"),
            "object": "subscription",
            "customer": customer_id,
            "status": "active",
            "provider": "square",
        }

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict:
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": "canceled",
            "provider": "square",
        }

    def update_subscription(self, subscription_id: str, new_price_id: str) -> dict:
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": "active",
            "provider": "square",
        }

    def list_payment_methods(self, customer_id: str) -> list[dict]:
        return [
            {
                "id": _mock_id("sqr_card"),
                "type": "card",
                "card": {"brand": "visa", "last4": "4242"},
                "provider": "square",
            }
        ]

    def update_customer_payment_method(self, customer_id: str, payment_method_token: str) -> dict:
        return {"status": "updated", "customer_id": customer_id, "provider": "square"}

    def retry_payment(self, payment_id: str) -> dict:
        return {"id": payment_id, "status": "paid", "provider": "square"}

    def create_billing_portal_session(self, customer_id: str, return_url: str) -> dict:
        return {
            "url": f"https://squareup.com/dashboard/customers/{customer_id}",
            "provider": "square",
        }

    def construct_webhook_event(self, payload: str, sig_header: str, secret: str) -> dict:
        import json

        return json.loads(payload)
