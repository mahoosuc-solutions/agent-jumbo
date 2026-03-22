import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from instruments.custom.stripe_payments.providers.base import StripePaymentProvider


def _mock_id(prefix: str) -> str:
    return f"{prefix}_mock_{uuid.uuid4().hex[:8]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _future_iso(days: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


class MockStripeProvider(StripePaymentProvider):
    """Deterministic mock implementation of the Stripe payment provider.

    Returns realistic response shapes with fake data. No external dependencies.
    """

    def create_customer(self, email: str, name: str, metadata: dict[str, Any] | None = None) -> dict:
        return {
            "id": _mock_id("cus"),
            "object": "customer",
            "email": email,
            "name": name,
            "metadata": metadata or {},
            "created": _now_iso(),
            "livemode": False,
            "currency": "usd",
            "default_source": None,
            "description": None,
        }

    def get_customer(self, customer_id: str) -> dict:
        return {
            "id": customer_id,
            "object": "customer",
            "email": "retrieved@example.com",
            "name": "Retrieved Customer",
            "metadata": {},
            "created": _now_iso(),
            "livemode": False,
            "currency": "usd",
            "default_source": None,
            "description": None,
        }

    def create_product(self, name: str, description: str, metadata: dict[str, Any] | None = None) -> dict:
        return {
            "id": _mock_id("prod"),
            "object": "product",
            "name": name,
            "description": description,
            "active": True,
            "metadata": metadata or {},
            "created": _now_iso(),
            "livemode": False,
            "type": "service",
            "images": [],
        }

    def create_price(
        self,
        product_id: str,
        unit_amount_cents: int,
        currency: str = "usd",
        recurring_interval: str | None = None,
    ) -> dict:
        price: dict[str, Any] = {
            "id": _mock_id("price"),
            "object": "price",
            "product": product_id,
            "unit_amount": unit_amount_cents,
            "currency": currency,
            "active": True,
            "type": "recurring" if recurring_interval else "one_time",
            "created": _now_iso(),
            "livemode": False,
            "recurring": None,
        }
        if recurring_interval:
            price["recurring"] = {
                "interval": recurring_interval,
                "interval_count": 1,
                "usage_type": "licensed",
            }
        return price

    def create_checkout_session(
        self,
        price_id: str,
        customer_id: str,
        mode: str = "payment",
        success_url: str = "",
        cancel_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        session_id = _mock_id("cs")
        return {
            "id": session_id,
            "object": "checkout.session",
            "customer": customer_id,
            "mode": mode,
            "payment_status": "unpaid",
            "status": "open",
            "url": f"https://checkout.stripe.com/mock/{session_id}",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata or {},
            "line_items": [{"price": price_id, "quantity": 1}],
            "created": _now_iso(),
            "livemode": False,
            "amount_total": 0,
            "currency": "usd",
        }

    def create_invoice(
        self,
        customer_id: str,
        items: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        total = sum(item.get("amount", 0) for item in items)
        return {
            "id": _mock_id("in"),
            "object": "invoice",
            "customer": customer_id,
            "status": "draft",
            "amount_due": total,
            "amount_paid": 0,
            "currency": "usd",
            "lines": {"data": items},
            "metadata": metadata or {},
            "created": _now_iso(),
            "due_date": _future_iso(30),
            "hosted_invoice_url": None,
            "invoice_pdf": None,
            "livemode": False,
        }

    def finalize_invoice(self, invoice_id: str) -> dict:
        return {
            "id": invoice_id,
            "object": "invoice",
            "status": "open",
            "amount_due": 5000,
            "amount_paid": 0,
            "currency": "usd",
            "hosted_invoice_url": f"https://invoice.stripe.com/mock/{invoice_id}",
            "invoice_pdf": f"https://invoice.stripe.com/mock/{invoice_id}/pdf",
            "finalized_at": _now_iso(),
            "livemode": False,
        }

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        now = _now_iso()
        trial_end = _future_iso(trial_days) if trial_days else None
        return {
            "id": _mock_id("sub"),
            "object": "subscription",
            "customer": customer_id,
            "status": "trialing" if trial_days else "active",
            "items": {"data": [{"price": {"id": price_id}}]},
            "current_period_start": now,
            "current_period_end": _future_iso(30),
            "trial_start": now if trial_days else None,
            "trial_end": trial_end,
            "cancel_at_period_end": False,
            "metadata": metadata or {},
            "created": now,
            "livemode": False,
        }

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict:
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": "active" if at_period_end else "canceled",
            "cancel_at_period_end": at_period_end,
            "canceled_at": _now_iso(),
            "current_period_end": _future_iso(30),
            "livemode": False,
        }

    def update_subscription(self, subscription_id: str, new_price_id: str) -> dict:
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": "active",
            "items": {"data": [{"price": {"id": new_price_id}}]},
            "current_period_start": _now_iso(),
            "current_period_end": _future_iso(30),
            "cancel_at_period_end": False,
            "livemode": False,
        }

    def construct_webhook_event(self, payload: str, sig_header: str, secret: str) -> dict:
        sig = hashlib.hmac_digest(secret.encode(), payload.encode(), "sha256").hex()
        try:
            data = json.loads(payload)
        except (json.JSONDecodeError, TypeError):
            data = {}
        return {
            "id": _mock_id("evt"),
            "object": "event",
            "type": data.get("type", "unknown"),
            "data": {"object": data.get("data", {})},
            "created": _now_iso(),
            "livemode": False,
            "api_version": "2024-12-18",
            "request": {"id": _mock_id("req"), "idempotency_key": None},
            "pending_webhooks": 0,
            "computed_signature": sig,
        }
