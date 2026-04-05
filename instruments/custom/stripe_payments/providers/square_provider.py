"""Square payment provider implementation.

Uses the Square REST API v2 via httpx (no SDK dependency).
All write operations include an idempotency_key to make retries safe.

Required environment variables:
    SQUARE_ACCESS_TOKEN     — OAuth access token or personal access token
    SQUARE_ENVIRONMENT      — 'sandbox' or 'production' (default: sandbox)
    SQUARE_WEBHOOK_SIGNATURE_KEY — webhook HMAC signing key
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from typing import Any

import httpx

from instruments.custom.stripe_payments.providers.base import PaymentProvider

logger = logging.getLogger(__name__)

_SQUARE_URLS = {
    "sandbox": "https://connect.squareupsandbox.com/v2",
    "production": "https://connect.squareup.com/v2",
}


class SquareProvider(PaymentProvider):
    """Real Square API provider using httpx.

    Reads credentials from environment variables or application settings.
    """

    def __init__(self) -> None:
        from python.helpers import settings as settings_helper

        try:
            config = settings_helper.get_settings()
        except Exception:
            config = {}

        self.access_token: str | None = os.environ.get("SQUARE_ACCESS_TOKEN") or config.get("square_access_token")
        self.webhook_signature_key: str | None = os.environ.get("SQUARE_WEBHOOK_SIGNATURE_KEY") or config.get(
            "square_webhook_signature_key"
        )
        env = os.environ.get("SQUARE_ENVIRONMENT", config.get("square_environment", "sandbox")).lower()
        self.base_url = _SQUARE_URLS.get(env, _SQUARE_URLS["sandbox"])

    # -- low-level -----------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not self.access_token:
            raise RuntimeError("SQUARE_ACCESS_TOKEN is not configured")

        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Square-Version": "2024-11-20",
        }

        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                content=json.dumps(body) if body else None,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            try:
                body_json = exc.response.json()
                msg = str(body_json.get("errors", exc.response.text))
            except Exception:
                msg = exc.response.text
            logger.error("Square API error %s for %s %s: %s", exc.response.status_code, method, path, msg)
            raise httpx.HTTPStatusError(message=msg, request=exc.request, response=exc.response) from exc

    @staticmethod
    def _idempotency_key() -> str:
        return uuid.uuid4().hex

    # -- PaymentProvider interface -------------------------------------------

    def get_provider_name(self) -> str:
        return "square"

    def create_customer(self, email: str, name: str, metadata: dict[str, Any] | None = None) -> dict:
        given_name, _, family_name = name.partition(" ")
        body: dict[str, Any] = {
            "idempotency_key": self._idempotency_key(),
            "email_address": email,
            "given_name": given_name,
            "family_name": family_name or "",
        }
        if metadata:
            body["note"] = json.dumps(metadata)
        result = self._request("POST", "customers", body)
        customer = result.get("customer", result)
        return {
            "id": customer.get("id", ""),
            "object": "customer",
            "email": email,
            "name": name,
            "metadata": metadata or {},
            "provider": "square",
            "raw": customer,
        }

    def get_customer(self, customer_id: str) -> dict:
        result = self._request("GET", f"customers/{customer_id}")
        customer = result.get("customer", result)
        return {
            "id": customer.get("id", customer_id),
            "object": "customer",
            "email": customer.get("email_address", ""),
            "name": f"{customer.get('given_name', '')} {customer.get('family_name', '')}".strip(),
            "provider": "square",
            "raw": customer,
        }

    def create_product(self, name: str, description: str, metadata: dict[str, Any] | None = None) -> dict:
        body = {
            "idempotency_key": self._idempotency_key(),
            "object": {
                "type": "ITEM",
                "id": "#item",
                "item_data": {
                    "name": name,
                    "description": description,
                    "variations": [
                        {
                            "type": "ITEM_VARIATION",
                            "id": "#variation",
                            "item_variation_data": {
                                "name": "Standard",
                                "pricing_type": "FIXED_PRICING",
                                "price_money": {"amount": 0, "currency": "USD"},
                            },
                        }
                    ],
                },
            },
        }
        result = self._request("POST", "catalog/object", body)
        obj = result.get("catalog_object", {})
        variation_id = ""
        variations = obj.get("item_data", {}).get("variations", [])
        if variations:
            variation_id = variations[0].get("id", "")
        return {
            "id": obj.get("id", ""),
            "object": "product",
            "name": name,
            "description": description,
            "variation_id": variation_id,
            "provider": "square",
            "raw": obj,
        }

    def create_price(
        self,
        product_id: str,
        unit_amount_cents: int,
        currency: str = "usd",
        recurring_interval: str | None = None,
    ) -> dict:
        # In Square, prices are ITEM_VARIATION objects on the catalog item.
        body = {
            "idempotency_key": self._idempotency_key(),
            "object": {
                "type": "ITEM_VARIATION",
                "id": "#price_variation",
                "item_variation_data": {
                    "item_id": product_id,
                    "name": "Monthly" if recurring_interval else "One-Time",
                    "pricing_type": "FIXED_PRICING",
                    "price_money": {"amount": unit_amount_cents, "currency": currency.upper()},
                },
            },
        }
        result = self._request("POST", "catalog/object", body)
        obj = result.get("catalog_object", {})
        return {
            "id": obj.get("id", ""),
            "object": "price",
            "product": product_id,
            "unit_amount": unit_amount_cents,
            "currency": currency,
            "type": "recurring" if recurring_interval else "one_time",
            "provider": "square",
            "raw": obj,
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
        body: dict[str, Any] = {
            "idempotency_key": self._idempotency_key(),
            "checkout_options": {
                "redirect_url": success_url or "https://example.com/success",
            },
            "pre_populated_data": {"buyer_email": ""},
            "line_items": [{"catalog_object_id": price_id, "quantity": "1"}],
        }
        result = self._request("POST", "online-checkout/payment-links", body)
        link = result.get("payment_link", {})
        return {
            "id": link.get("id", ""),
            "object": "checkout.session",
            "url": link.get("url", ""),
            "customer": customer_id,
            "mode": mode,
            "provider": "square",
            "raw": link,
        }

    def create_invoice(
        self,
        customer_id: str,
        items: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        line_items = []
        for item in items:
            line_items.append(
                {
                    "quantity": "1",
                    "base_price_money": {
                        "amount": item.get("amount", 0),
                        "currency": item.get("currency", "USD").upper(),
                    },
                    "note": item.get("description", ""),
                }
            )

        body: dict[str, Any] = {
            "idempotency_key": self._idempotency_key(),
            "invoice": {
                "primary_recipient": {"customer_id": customer_id},
                "delivery_method": "EMAIL",
                "line_items": line_items,
                "payment_requests": [{"request_type": "BALANCE", "due_date": self._due_date_str(30)}],
            },
        }
        result = self._request("POST", "invoices", body)
        invoice = result.get("invoice", {})
        total = sum(item.get("amount", 0) for item in items)
        return {
            "id": invoice.get("id", ""),
            "object": "invoice",
            "customer": customer_id,
            "status": invoice.get("status", "DRAFT").lower(),
            "amount_due": total,
            "currency": "usd",
            "provider": "square",
            "raw": invoice,
        }

    def finalize_invoice(self, invoice_id: str) -> dict:
        result = self._request(
            "POST", f"invoices/{invoice_id}/publish", {"version": 0, "idempotency_key": self._idempotency_key()}
        )
        invoice = result.get("invoice", {})
        return {
            "id": invoice_id,
            "object": "invoice",
            "status": invoice.get("status", "UNPAID").lower(),
            "provider": "square",
            "raw": invoice,
        }

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        body: dict[str, Any] = {
            "idempotency_key": self._idempotency_key(),
            "customer_id": customer_id,
            "plan_variation_id": price_id,
            "start_date": self._today_str(),
        }
        if trial_days:
            body["phases"] = [{"periods": trial_days, "cadence": "DAILY", "pricing": {"type": "STATIC"}}]
        result = self._request("POST", "subscriptions", body)
        sub = result.get("subscription", {})
        return {
            "id": sub.get("id", ""),
            "object": "subscription",
            "customer": customer_id,
            "status": sub.get("status", "ACTIVE").lower(),
            "provider": "square",
            "raw": sub,
        }

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict:
        result = self._request("POST", f"subscriptions/{subscription_id}/cancel")
        sub = result.get("subscription", {})
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": sub.get("status", "CANCELED").lower(),
            "provider": "square",
            "raw": sub,
        }

    def update_subscription(self, subscription_id: str, new_price_id: str) -> dict:
        body = {"subscription": {"plan_variation_id": new_price_id}}
        result = self._request("PUT", f"subscriptions/{subscription_id}", body)
        sub = result.get("subscription", {})
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": sub.get("status", "ACTIVE").lower(),
            "provider": "square",
            "raw": sub,
        }

    def list_payment_methods(self, customer_id: str) -> list[dict]:
        # Square stores payment methods as cards on a customer profile
        result = self._request("GET", f"customers/{customer_id}")
        customer = result.get("customer", {})
        return [
            {
                "id": card.get("id", ""),
                "type": "card",
                "card": {
                    "brand": card.get("card_brand", ""),
                    "last4": card.get("last_4", ""),
                    "exp_month": card.get("exp_month", 0),
                    "exp_year": card.get("exp_year", 0),
                },
                "provider": "square",
            }
            for card in customer.get("cards", [])
        ]

    def update_customer_payment_method(self, customer_id: str, payment_method_token: str) -> dict:
        # Square uses card nonces — the token must be from Square.js / In-App Payments SDK
        body = {
            "idempotency_key": self._idempotency_key(),
            "source_id": payment_method_token,
            "customer_id": customer_id,
            "billing_address": {},
        }
        result = self._request("POST", "cards", body)
        return {"status": "updated", "customer_id": customer_id, "provider": "square", "raw": result}

    def retry_payment(self, payment_id: str) -> dict:
        # Square invoices: POST /v2/invoices/{id}/pay
        result = self._request("POST", f"invoices/{payment_id}/pay", {"idempotency_key": self._idempotency_key()})
        invoice = result.get("invoice", {})
        return {"id": payment_id, "status": invoice.get("status", "").lower(), "provider": "square"}

    def create_billing_portal_session(self, customer_id: str, return_url: str) -> dict:
        # Square doesn't have a hosted billing portal; return the customer portal deep-link.
        return {
            "url": f"https://squareup.com/dashboard/customers/{customer_id}",
            "provider": "square",
            "note": "Square does not provide a hosted customer billing portal. "
            "This URL opens the Square merchant customer detail page.",
        }

    def construct_webhook_event(self, payload: str, sig_header: str, secret: str) -> dict:
        """Verify Square webhook signature (HMAC-SHA256).

        Square sends the signature in the ``X-Square-HMAC-SHA256-Signature`` header.
        The signed content is the notification URL concatenated with the raw body.
        """
        if not secret:
            raise ValueError("Missing Square webhook signature key")

        expected = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        import base64

        expected_b64 = base64.b64encode(expected).decode("utf-8")

        if not hmac.compare_digest(expected_b64, sig_header):
            raise ValueError("Square webhook signature verification failed")

        event = json.loads(payload)
        return event

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _today_str() -> str:
        return time.strftime("%Y-%m-%d", time.gmtime())

    @staticmethod
    def _due_date_str(days: int) -> str:
        future_ts = time.time() + days * 86400
        return time.strftime("%Y-%m-%d", time.gmtime(future_ts))
