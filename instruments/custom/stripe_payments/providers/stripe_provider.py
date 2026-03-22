import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from instruments.custom.stripe_payments.providers.base import StripePaymentProvider
from python.helpers import settings as settings_helper

logger = logging.getLogger(__name__)

BASE_URL = "https://api.stripe.com/v1"


def _flatten_params(data: dict[str, Any], prefix: str = "") -> list[tuple[str, str]]:
    """Flatten a nested dict into Stripe's bracket-notation form-encoded pairs.

    Example::

        {"metadata": {"key": "val"}, "name": "Foo"}
        -> [("metadata[key]", "val"), ("name", "Foo")]
    """
    pairs: list[tuple[str, str]] = []
    for key, value in data.items():
        full_key = f"{prefix}[{key}]" if prefix else key
        if isinstance(value, dict):
            pairs.extend(_flatten_params(value, full_key))
        elif isinstance(value, (list, tuple)):
            for idx, item in enumerate(value):
                if isinstance(item, dict):
                    pairs.extend(_flatten_params(item, f"{full_key}[{idx}]"))
                else:
                    pairs.append((f"{full_key}[{idx}]", str(item)))
        elif isinstance(value, bool):
            pairs.append((full_key, "true" if value else "false"))
        elif value is not None:
            pairs.append((full_key, str(value)))
    return pairs


class StripePaymentProvider(StripePaymentProvider):
    """Real Stripe API provider using httpx (no SDK dependency).

    Reads ``stripe_api_key`` and ``stripe_webhook_secret`` from the
    application settings loaded via ``python.helpers.settings``.
    """

    def __init__(self) -> None:
        try:
            config = settings_helper.get_settings()
        except Exception:
            config = {}
        self.api_key: str | None = config.get("stripe_api_key")
        self.webhook_secret: str | None = config.get("stripe_webhook_secret")

    # ------------------------------------------------------------------
    # Low-level request helper
    # ------------------------------------------------------------------

    def _stripe_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated HTTPS request to the Stripe API.

        Args:
            method: HTTP method (GET, POST, DELETE).
            endpoint: API path *without* the ``/v1/`` prefix,
                      e.g. ``"customers"`` or ``"invoices/in_xxx/finalize"``.
            data: Optional dict of parameters (will be form-encoded).

        Returns:
            Parsed JSON response dict.

        Raises:
            RuntimeError: If the API key is not configured.
            httpx.HTTPStatusError: On 4xx / 5xx responses (with Stripe error
                message attached).
        """
        if not self.api_key:
            raise RuntimeError("stripe_api_key is not configured in settings")

        url = f"{BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        pairs = _flatten_params(data) if data else None

        try:
            response = httpx.request(
                method,
                url,
                headers=headers,
                data=pairs,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            # Try to extract a friendlier Stripe error message.
            try:
                body = exc.response.json()
                stripe_msg = body.get("error", {}).get("message", exc.response.text)
            except Exception:
                stripe_msg = exc.response.text
            logger.error(
                "Stripe API error %s for %s %s: %s",
                exc.response.status_code,
                method,
                endpoint,
                stripe_msg,
            )
            raise httpx.HTTPStatusError(
                message=stripe_msg,
                request=exc.request,
                response=exc.response,
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Stripe request error for %s %s: %s", method, endpoint, exc)
            raise
        except Exception as exc:
            logger.error("Unexpected error calling Stripe %s %s: %s", method, endpoint, exc)
            raise

    # ------------------------------------------------------------------
    # Customer endpoints
    # ------------------------------------------------------------------

    def create_customer(
        self,
        email: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        params: dict[str, Any] = {"email": email, "name": name}
        if metadata:
            params["metadata"] = metadata
        return self._stripe_request("POST", "customers", params)

    def get_customer(self, customer_id: str) -> dict:
        return self._stripe_request("GET", f"customers/{customer_id}")

    # ------------------------------------------------------------------
    # Product / Price endpoints
    # ------------------------------------------------------------------

    def create_product(
        self,
        name: str,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        params: dict[str, Any] = {"name": name, "description": description}
        if metadata:
            params["metadata"] = metadata
        return self._stripe_request("POST", "products", params)

    def create_price(
        self,
        product_id: str,
        unit_amount_cents: int,
        currency: str = "usd",
        recurring_interval: str | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "product": product_id,
            "unit_amount": unit_amount_cents,
            "currency": currency,
        }
        if recurring_interval:
            params["recurring"] = {"interval": recurring_interval}
        return self._stripe_request("POST", "prices", params)

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    def create_checkout_session(
        self,
        price_id: str,
        customer_id: str,
        mode: str = "payment",
        success_url: str = "",
        cancel_url: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "customer": customer_id,
            "mode": mode,
            "line_items": [{"price": price_id, "quantity": 1}],
            "success_url": success_url or "https://example.com/success",
            "cancel_url": cancel_url or "https://example.com/cancel",
        }
        if metadata:
            params["metadata"] = metadata
        return self._stripe_request("POST", "checkout/sessions", params)

    # ------------------------------------------------------------------
    # Invoice endpoints
    # ------------------------------------------------------------------

    def create_invoice(
        self,
        customer_id: str,
        items: list[dict[str, Any]],
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        # Step 1: create the invoice shell
        inv_params: dict[str, Any] = {"customer": customer_id}
        if metadata:
            inv_params["metadata"] = metadata
        invoice = self._stripe_request("POST", "invoices", inv_params)
        invoice_id = invoice["id"]

        # Step 2: add each line item via InvoiceItems
        for item in items:
            item_params: dict[str, Any] = {
                "invoice": invoice_id,
                "customer": customer_id,
            }
            if "price" in item:
                item_params["price"] = item["price"]
            else:
                item_params["amount"] = item.get("amount", 0)
                item_params["currency"] = item.get("currency", "usd")
                item_params["description"] = item.get("description", "Line item")
            self._stripe_request("POST", "invoiceitems", item_params)

        # Re-fetch so the response includes all lines
        return self._stripe_request("GET", f"invoices/{invoice_id}")

    def finalize_invoice(self, invoice_id: str) -> dict:
        return self._stripe_request("POST", f"invoices/{invoice_id}/finalize")

    # ------------------------------------------------------------------
    # Subscription endpoints
    # ------------------------------------------------------------------

    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        params: dict[str, Any] = {
            "customer": customer_id,
            "items": [{"price": price_id}],
        }
        if trial_days:
            params["trial_period_days"] = trial_days
        if metadata:
            params["metadata"] = metadata
        return self._stripe_request("POST", "subscriptions", params)

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict:
        if at_period_end:
            return self._stripe_request(
                "POST",
                f"subscriptions/{subscription_id}",
                {"cancel_at_period_end": True},
            )
        return self._stripe_request("DELETE", f"subscriptions/{subscription_id}")

    def update_subscription(self, subscription_id: str, new_price_id: str) -> dict:
        # Retrieve current subscription to get the subscription item ID
        sub = self._stripe_request("GET", f"subscriptions/{subscription_id}")
        si_id = sub["items"]["data"][0]["id"]
        return self._stripe_request(
            "POST",
            f"subscriptions/{subscription_id}",
            {"items": [{"id": si_id, "price": new_price_id}]},
        )

    # ------------------------------------------------------------------
    # Webhook signature verification
    # ------------------------------------------------------------------

    def construct_webhook_event(self, payload: str, sig_header: str, secret: str) -> dict:
        """Verify Stripe webhook signature and return the parsed event.

        Stripe sends a ``Stripe-Signature`` header containing a timestamp
        (``t=…``) and one or more ``v1=…`` HMAC-SHA256 signatures.  We
        recompute the expected signature and compare.

        Raises:
            ValueError: If the signature is missing, malformed, or invalid.
        """
        if not sig_header:
            raise ValueError("Missing Stripe-Signature header")

        # Parse the header: "t=<ts>,v1=<sig1>,v1=<sig2>"
        parts: dict[str, list[str]] = {}
        for item in sig_header.split(","):
            key, _, value = item.strip().partition("=")
            parts.setdefault(key, []).append(value)

        timestamp_strs = parts.get("t", [])
        signatures = parts.get("v1", [])

        if not timestamp_strs or not signatures:
            raise ValueError("Invalid Stripe-Signature header format")

        timestamp = timestamp_strs[0]

        # Build the signed payload: "<timestamp>.<raw_body>"
        signed_payload = f"{timestamp}.{payload}"
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not any(hmac.compare_digest(expected_sig, sig) for sig in signatures):
            raise ValueError("Stripe webhook signature verification failed")

        # Reject timestamps older than 5 minutes to prevent replay attacks
        try:
            ts_int = int(timestamp)
            if abs(time.time() - ts_int) > 300:
                raise ValueError("Stripe webhook timestamp outside tolerance (>5 min)")
        except (ValueError, OverflowError):
            pass  # non-integer timestamp; skip tolerance check

        event = json.loads(payload)
        return event
