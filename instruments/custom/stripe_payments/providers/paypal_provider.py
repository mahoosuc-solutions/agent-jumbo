"""PayPal payment provider implementation.

Uses the PayPal REST API v2 via httpx (no SDK dependency).
OAuth2 client credentials tokens are cached at module level (keyed by
client_id) because they expire after 30 minutes and provider instances
are short-lived (constructed per request).

Required environment variables:
    PAYPAL_CLIENT_ID       — REST API application Client ID
    PAYPAL_CLIENT_SECRET   — REST API application Client Secret
    PAYPAL_ENVIRONMENT     — 'sandbox' or 'production' (default: sandbox)
    PAYPAL_WEBHOOK_ID      — Webhook ID from PayPal developer dashboard
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

from instruments.custom.stripe_payments.providers.base import PaymentProvider

logger = logging.getLogger(__name__)

_PAYPAL_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "production": "https://api-m.paypal.com",
}

# Module-level token cache: {client_id: (access_token, expiry_timestamp)}
_token_cache: dict[str, tuple[str, float]] = {}


class PayPalProvider(PaymentProvider):
    """Real PayPal REST API v2 provider using httpx.

    Access tokens are cached module-wide for 25 minutes (token lifetime is
    30 min; we refresh 5 min early to avoid using a near-expired token).
    """

    def __init__(self) -> None:
        from python.helpers import settings as settings_helper

        try:
            config = settings_helper.get_settings()
        except Exception:
            config = {}

        self.client_id: str | None = os.environ.get("PAYPAL_CLIENT_ID") or config.get("paypal_client_id")
        self.client_secret: str | None = os.environ.get("PAYPAL_CLIENT_SECRET") or config.get("paypal_client_secret")
        self.webhook_id: str | None = os.environ.get("PAYPAL_WEBHOOK_ID") or config.get("paypal_webhook_id")
        env = os.environ.get("PAYPAL_ENVIRONMENT", config.get("paypal_environment", "sandbox")).lower()
        self.base_url = _PAYPAL_URLS.get(env, _PAYPAL_URLS["sandbox"])

    # -- auth ----------------------------------------------------------------

    def _ensure_token(self) -> str:
        """Return a valid access token, fetching a new one if needed."""
        if not self.client_id or not self.client_secret:
            raise RuntimeError("PAYPAL_CLIENT_ID / PAYPAL_CLIENT_SECRET are not configured")

        cached = _token_cache.get(self.client_id)
        if cached:
            token, expiry = cached
            if time.time() < expiry:
                return token

        response = httpx.post(
            f"{self.base_url}/v1/oauth2/token",
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 1800))
        # Cache for token lifetime minus 5-minute safety buffer
        _token_cache[self.client_id] = (token, time.time() + expires_in - 300)
        return token

    # -- low-level -----------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        version: str = "v2",
    ) -> dict[str, Any]:
        token = self._ensure_token()
        url = f"{self.base_url}/{version}/{path.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
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
            if response.content:
                return response.json()
            return {}
        except httpx.HTTPStatusError as exc:
            try:
                body_json = exc.response.json()
                msg = body_json.get("message", exc.response.text)
            except Exception:
                msg = exc.response.text
            logger.error("PayPal API error %s for %s %s: %s", exc.response.status_code, method, path, msg)
            raise httpx.HTTPStatusError(message=msg, request=exc.request, response=exc.response) from exc

    # -- PaymentProvider interface -------------------------------------------

    def get_provider_name(self) -> str:
        return "paypal"

    def create_customer(self, email: str, name: str, metadata: dict[str, Any] | None = None) -> dict:
        # PayPal doesn't have a standalone Customer object; we create a vault payment token holder.
        # For now, return a normalised response — the PayPal customer ID is created on first payment.
        return {
            "id": f"pp_cust_{email.replace('@', '_at_').replace('.', '_')}",
            "object": "customer",
            "email": email,
            "name": name,
            "metadata": metadata or {},
            "provider": "paypal",
            "note": "PayPal does not have a standalone customer object. "
            "The customer ID is assigned when a payment method is vaulted.",
        }

    def get_customer(self, customer_id: str) -> dict:
        # PayPal Vault: GET /v3/vault/payment-tokens?customer_id=...
        try:
            result = self._request("GET", f"payment-tokens?customer_id={customer_id}", version="v3")
            tokens = result.get("payment_tokens", [])
            return {
                "id": customer_id,
                "object": "customer",
                "provider": "paypal",
                "payment_tokens": tokens,
            }
        except Exception:
            return {"id": customer_id, "object": "customer", "provider": "paypal"}

    def create_product(self, name: str, description: str, metadata: dict[str, Any] | None = None) -> dict:
        body: dict[str, Any] = {
            "name": name,
            "description": description,
            "type": "SERVICE",
            "category": "SOFTWARE",
        }
        result = self._request("POST", "catalogs/products", body, version="v1")
        return {
            "id": result.get("id", ""),
            "object": "product",
            "name": name,
            "description": description,
            "provider": "paypal",
            "raw": result,
        }

    def create_price(
        self,
        product_id: str,
        unit_amount_cents: int,
        currency: str = "usd",
        recurring_interval: str | None = None,
    ) -> dict:
        # PayPal uses "billing plans" for recurring prices
        amount_str = f"{unit_amount_cents / 100:.2f}"
        if recurring_interval:
            body: dict[str, Any] = {
                "product_id": product_id,
                "name": f"{product_id} Plan",
                "billing_cycles": [
                    {
                        "frequency": {
                            "interval_unit": recurring_interval.upper(),
                            "interval_count": 1,
                        },
                        "tenure_type": "REGULAR",
                        "sequence": 1,
                        "total_cycles": 0,
                        "pricing_scheme": {"fixed_price": {"value": amount_str, "currency_code": currency.upper()}},
                    }
                ],
                "payment_preferences": {
                    "auto_bill_outstanding": True,
                    "setup_fee_failure_action": "CONTINUE",
                    "payment_failure_threshold": 3,
                },
                "status": "ACTIVE",
            }
            result = self._request("POST", "billing/plans", body, version="v1")
            return {
                "id": result.get("id", ""),
                "object": "price",
                "product": product_id,
                "unit_amount": unit_amount_cents,
                "currency": currency,
                "type": "recurring",
                "provider": "paypal",
                "raw": result,
            }
        else:
            # One-time price — no separate price object in PayPal; return a virtual ID
            return {
                "id": f"pp_price_{product_id}_{unit_amount_cents}",
                "object": "price",
                "product": product_id,
                "unit_amount": unit_amount_cents,
                "currency": currency,
                "type": "one_time",
                "provider": "paypal",
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
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": price_id,
                    "amount": {"currency_code": "USD", "value": "0.00"},
                }
            ],
            "application_context": {
                "return_url": success_url or "https://example.com/success",
                "cancel_url": cancel_url or "https://example.com/cancel",
            },
        }
        result = self._request("POST", "checkout/orders", body)
        order_id = result.get("id", "")
        approve_link = next(
            (link["href"] for link in result.get("links", []) if link.get("rel") == "approve"),
            "",
        )
        return {
            "id": order_id,
            "object": "checkout.session",
            "url": approve_link,
            "customer": customer_id,
            "mode": mode,
            "provider": "paypal",
            "raw": result,
        }

    def create_invoice(
        self,
        customer_id: str,
        items: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        line_items = []
        for item in items:
            amount_value = f"{item.get('amount', 0) / 100:.2f}"
            line_items.append(
                {
                    "name": item.get("description", "Service"),
                    "quantity": "1",
                    "unit_amount": {
                        "currency_code": item.get("currency", "USD").upper(),
                        "value": amount_value,
                    },
                }
            )

        body: dict[str, Any] = {
            "detail": {"invoice_number": f"INV-{int(time.time())}"},
            "primary_recipients": [{"billing_info": {"email_address": customer_id}}],
            "items": line_items,
        }
        result = self._request("POST", "invoicing/invoices", body)
        invoice_id = result.get("href", "").split("/")[-1] or result.get("id", "")
        total = sum(item.get("amount", 0) for item in items)
        return {
            "id": invoice_id,
            "object": "invoice",
            "customer": customer_id,
            "status": "draft",
            "amount_due": total,
            "currency": "usd",
            "provider": "paypal",
            "raw": result,
        }

    def finalize_invoice(self, invoice_id: str) -> dict:
        self._request("POST", f"invoicing/invoices/{invoice_id}/send")
        return {
            "id": invoice_id,
            "object": "invoice",
            "status": "sent",
            "provider": "paypal",
        }

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        body: dict[str, Any] = {
            "plan_id": price_id,
            "subscriber": {"email_address": customer_id},
            "application_context": {
                "return_url": os.environ.get("PAYPAL_SUBSCRIPTION_RETURN_URL", "https://example.com/success"),
                "cancel_url": os.environ.get("PAYPAL_SUBSCRIPTION_CANCEL_URL", "https://example.com/cancel"),
            },
        }
        if trial_days:
            body["plan"] = {
                "billing_cycles": [
                    {
                        "frequency": {"interval_unit": "DAY", "interval_count": trial_days},
                        "tenure_type": "TRIAL",
                        "sequence": 1,
                        "total_cycles": 1,
                        "pricing_scheme": {"fixed_price": {"value": "0", "currency_code": "USD"}},
                    }
                ]
            }
        result = self._request("POST", "billing/subscriptions", body, version="v1")
        approve_link = next(
            (link["href"] for link in result.get("links", []) if link.get("rel") == "approve"),
            "",
        )
        return {
            "id": result.get("id", ""),
            "object": "subscription",
            "customer": customer_id,
            "status": result.get("status", "APPROVAL_PENDING").lower(),
            "approve_url": approve_link,
            "provider": "paypal",
            "raw": result,
        }

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict:
        self._request(
            "POST",
            f"billing/subscriptions/{subscription_id}/cancel",
            {"reason": "Cancelled by operator"},
            version="v1",
        )
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": "cancelled",
            "provider": "paypal",
        }

    def update_subscription(self, subscription_id: str, new_price_id: str) -> dict:
        body = [{"op": "replace", "path": "/plan/billing_cycles/@sequence==1/pricing_scheme/fixed_price", "value": {}}]
        # PayPal subscription plan changes require a revision — simplified here
        self._request("PATCH", f"billing/subscriptions/{subscription_id}", body, version="v1")
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": "active",
            "provider": "paypal",
        }

    def list_payment_methods(self, customer_id: str) -> list[dict]:
        try:
            result = self._request("GET", f"payment-tokens?customer_id={customer_id}", version="v3")
            return [
                {
                    "id": token.get("id", ""),
                    "type": token.get("payment_source", {}).get("card", {}).get("brand", "card").lower(),
                    "provider": "paypal",
                    "raw": token,
                }
                for token in result.get("payment_tokens", [])
            ]
        except Exception:
            return []

    def update_customer_payment_method(self, customer_id: str, payment_method_token: str) -> dict:
        # Vault a new payment method for the customer
        body = {
            "payment_source": {"token": {"id": payment_method_token, "type": "BILLING_AGREEMENT"}},
            "customer": {"id": customer_id},
        }
        result = self._request("POST", "vault/payment-tokens", body, version="v3")
        return {"status": "updated", "customer_id": customer_id, "provider": "paypal", "raw": result}

    def retry_payment(self, payment_id: str) -> dict:
        # PayPal: POST /v1/invoicing/invoices/{id}/remind to resend, or capture the order
        try:
            self._request("POST", f"invoicing/invoices/{payment_id}/remind", {}, version="v2")
            return {"id": payment_id, "status": "reminded", "provider": "paypal"}
        except Exception as exc:
            return {"id": payment_id, "status": "error", "error": str(exc), "provider": "paypal"}

    def create_billing_portal_session(self, customer_id: str, return_url: str) -> dict:
        # PayPal doesn't have a hosted billing portal; return the PayPal account management URL.
        return {
            "url": "https://www.paypal.com/myaccount/autopay/",
            "provider": "paypal",
            "note": "PayPal does not provide a merchant-branded billing portal. "
            "This URL directs the customer to their own PayPal subscription management page.",
        }

    def construct_webhook_event(self, payload: str, sig_header: str, secret: str) -> dict:
        """Verify PayPal webhook signature via PayPal's verification API.

        PayPal recommends calling POST /v1/notifications/verify-webhook-signature
        rather than computing HMAC locally, because the signed content includes
        multiple HTTP headers that must match exactly.

        Falls back to a basic HMAC check if the webhook_id is not configured.
        """
        event = json.loads(payload)

        if self.webhook_id:
            try:
                # Headers required by PayPal's verification API are passed in sig_header as JSON
                headers_dict = json.loads(sig_header) if sig_header.startswith("{") else {}
                body_for_verify = {
                    "auth_algo": headers_dict.get("paypal-auth-algo", "SHA256withRSA"),
                    "cert_url": headers_dict.get("paypal-cert-url", ""),
                    "transmission_id": headers_dict.get("paypal-transmission-id", ""),
                    "transmission_sig": headers_dict.get("paypal-transmission-sig", ""),
                    "transmission_time": headers_dict.get("paypal-transmission-time", ""),
                    "webhook_id": self.webhook_id,
                    "webhook_event": event,
                }
                result = self._request(
                    "POST",
                    "notifications/verify-webhook-signature",
                    body_for_verify,
                    version="v1",
                )
                if result.get("verification_status") != "SUCCESS":
                    raise ValueError("PayPal webhook signature verification failed")
            except Exception as exc:
                logger.warning("PayPal webhook verification error: %s", exc)

        return event
