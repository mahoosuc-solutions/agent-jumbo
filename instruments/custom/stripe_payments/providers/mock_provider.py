import hashlib
import json
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


class MockStripeProvider(PaymentProvider):
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

    def list_products(self, active: bool | None = None, limit: int = 100) -> list[dict]:
        products = [
            {
                "id": "mahoosuc_platform_tier_pro",
                "object": "product",
                "name": "Pro",
                "description": "Managed routing tier",
                "active": True,
                "metadata": {"slug": "pro", "catalog_family": "platform_tier"},
            }
        ]
        if active is None:
            return products[:limit]
        return [product for product in products[:limit] if bool(product.get("active")) is active]

    def list_prices(
        self,
        product_id: str | None = None,
        active: bool | None = None,
        limit: int = 100,
    ) -> list[dict]:
        prices = [
            {
                "id": "price_mock_pro_monthly",
                "object": "price",
                "product": "mahoosuc_platform_tier_pro",
                "unit_amount": 3900,
                "currency": "usd",
                "active": True,
                "recurring": {"interval": "month"},
                "lookup_key": "mahoosuc_platform_tier_pro_monthly",
            }
        ]
        filtered = prices
        if product_id:
            filtered = [price for price in filtered if price.get("product") == product_id]
        if active is not None:
            filtered = [price for price in filtered if bool(price.get("active")) is active]
        return filtered[:limit]

    def list_webhook_endpoints(self, limit: int = 100) -> list[dict]:
        return [
            {
                "id": "we_mock_123",
                "object": "webhook_endpoint",
                "url": "http://localhost:6274/api/stripe/webhook",
                "status": "enabled",
                "enabled_events": [
                    "checkout.session.completed",
                    "customer.subscription.updated",
                    "customer.subscription.deleted",
                    "invoice.paid",
                    "invoice.payment_failed",
                ],
            }
        ][:limit]

    def create_webhook_endpoint(
        self,
        url: str,
        enabled_events: list[str] | None = None,
        description: str = "",
    ) -> dict:
        return {
            "id": _mock_id("we"),
            "object": "webhook_endpoint",
            "url": url,
            "status": "enabled",
            "description": description,
            "enabled_events": enabled_events or [],
            "secret": "whsec_mock_secret",  # pragma: allowlist secret
        }

    def get_account(self) -> dict:
        return {
            "id": "acct_mock_123",
            "business_profile": {"name": "Mock Tenant"},
            "details_submitted": True,
            "charges_enabled": True,
            "payouts_enabled": True,
            "requirements": {"currently_due": []},
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

    def get_provider_name(self) -> str:
        return "stripe"

    def list_payment_methods(self, customer_id: str) -> list[dict]:
        return [
            {
                "id": _mock_id("pm"),
                "object": "payment_method",
                "type": "card",
                "card": {"brand": "visa", "last4": "4242", "exp_month": 12, "exp_year": 2030},
                "customer": customer_id,
            }
        ]

    def update_customer_payment_method(self, customer_id: str, payment_method_token: str) -> dict:
        return {
            "id": customer_id,
            "object": "customer",
            "invoice_settings": {"default_payment_method": payment_method_token},
        }

    def retry_payment(self, payment_id: str) -> dict:
        return {
            "id": payment_id,
            "object": "invoice",
            "status": "paid",
            "amount_paid": 5000,
            "paid": True,
        }

    def create_billing_portal_session(self, customer_id: str, return_url: str) -> dict:
        return {
            "url": f"https://billing.stripe.com/mock/p/{_mock_id('bps')}",
            "session_id": _mock_id("bps"),
            "provider": "stripe",
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
