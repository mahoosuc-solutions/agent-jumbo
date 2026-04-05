"""PayPal webhook event handler.

Processes PayPal IPN / REST webhook notifications and syncs event data to
the local database. Mirrors the structure of StripeWebhookHandler.

Handled event types:
    BILLING.SUBSCRIPTION.ACTIVATED      — new subscription goes live
    BILLING.SUBSCRIPTION.CANCELLED      — subscription cancelled
    BILLING.SUBSCRIPTION.PAYMENT.FAILED — payment failed on a subscription
    PAYMENT.SALE.COMPLETED              — one-time payment captured successfully
    PAYMENT.SALE.DENIED                 — payment denied / failed
    INVOICING.INVOICE.PAID              — invoice paid
    INVOICING.INVOICE.PAYMENT_FAILED    — invoice payment failed
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PayPalWebhookHandler:
    """Process inbound PayPal webhook events."""

    def __init__(self, db):
        self.db = db

        self._handlers: dict[str, Any] = {
            "BILLING.SUBSCRIPTION.ACTIVATED": self._handle_subscription_activated,
            "BILLING.SUBSCRIPTION.CANCELLED": self._handle_subscription_cancelled,
            "BILLING.SUBSCRIPTION.PAYMENT.FAILED": self._handle_subscription_payment_failed,
            "PAYMENT.SALE.COMPLETED": self._handle_payment_completed,
            "PAYMENT.SALE.DENIED": self._handle_payment_denied,
            "INVOICING.INVOICE.PAID": self._handle_invoice_paid,
            "INVOICING.INVOICE.PAYMENT_FAILED": self._handle_invoice_payment_failed,
        }

    def verify_signature(
        self,
        raw_body: str,
        headers: dict[str, str],
        webhook_id: str,
        client_id: str,
        client_secret: str,
        environment: str = "sandbox",
    ) -> bool:
        """Verify PayPal webhook signature via the PayPal verify-webhook-signature API.

        Returns True if verification succeeds, False on any failure.
        Falls back to True in sandbox mode when credentials are not configured
        (to simplify local development without real PayPal keys).
        """
        if not client_id or not client_secret:
            if environment == "sandbox":
                logger.warning("PayPal credentials not configured — skipping verification in sandbox mode")
                return True
            return False

        try:
            import httpx

            base_url = "https://api-m.sandbox.paypal.com" if environment == "sandbox" else "https://api-m.paypal.com"
            # Get access token
            token_resp = httpx.post(
                f"{base_url}/v1/oauth2/token",
                auth=(client_id, client_secret),
                data={"grant_type": "client_credentials"},
                timeout=10,
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]

            # Verify signature
            verify_resp = httpx.post(
                f"{base_url}/v1/notifications/verify-webhook-signature",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={
                    "auth_algo": headers.get("PAYPAL-AUTH-ALGO", ""),
                    "cert_url": headers.get("PAYPAL-CERT-URL", ""),
                    "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID", ""),
                    "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG", ""),
                    "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME", ""),
                    "webhook_id": webhook_id,
                    "webhook_event": json.loads(raw_body),
                },
                timeout=10,
            )
            verify_resp.raise_for_status()
            return verify_resp.json().get("verification_status") == "SUCCESS"
        except Exception as exc:
            logger.error("PayPal webhook verification error: %s", exc)
            return False

    def handle_event(self, event_id: str, event_type: str, resource: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a PayPal webhook event by type."""
        handler = self._handlers.get(event_type)
        if handler is None:
            return {"status": "ignored", "event_type": event_type, "event_id": event_id}
        try:
            result = handler(resource)
            return {"status": "processed", "event_type": event_type, "event_id": event_id, **result}
        except Exception as exc:
            logger.error("Error processing PayPal event %s (%s): %s", event_id, event_type, exc)
            return {"status": "error", "event_type": event_type, "event_id": event_id, "error": str(exc)}

    def process(self, event: dict[str, Any]) -> dict[str, Any]:
        """Process a PayPal webhook event dict.

        Args:
            event: The parsed PayPal event payload.

        Returns:
            Dict with ``status``, ``event_id``, and ``event_type``.
        """
        event_id = event.get("id", "")
        event_type = event.get("event_type", "")

        # Idempotency check
        existing = self.db.get_webhook_event(event_id) if event_id else None
        if existing and existing.get("processed"):
            logger.info("PayPal event %s already processed, skipping", event_id)
            return {"status": "duplicate", "event_id": event_id, "event_type": event_type}

        if event_id:
            try:
                self.db.record_webhook_event(
                    event_id=event_id,
                    event_type=event_type,
                    payload=json.dumps(event),
                )
            except Exception as exc:
                logger.warning("Could not record PayPal webhook event: %s", exc)

        handler = self._handlers.get(event_type)
        if handler:
            try:
                handler(event)
                if event_id:
                    self.db.mark_webhook_processed(event_id)
                return {"status": "processed", "event_id": event_id, "event_type": event_type}
            except Exception as exc:
                logger.error("Error processing PayPal event %s (%s): %s", event_id, event_type, exc)
                if event_id:
                    self.db.mark_webhook_error(event_id, str(exc))
                return {"status": "error", "event_id": event_id, "event_type": event_type, "error": str(exc)}

        logger.debug("No handler for PayPal event type %s", event_type)
        return {"status": "unhandled", "event_id": event_id, "event_type": event_type}

    # -- event handlers ------------------------------------------------------

    def _handle_subscription_activated(self, event: dict[str, Any]) -> None:
        """Sync a newly activated PayPal subscription."""
        resource = event.get("resource", {})
        sub_id = resource.get("id", "")
        plan_id = resource.get("plan_id", "")
        subscriber = resource.get("subscriber", {})
        customer_email = subscriber.get("email_address", "")

        logger.info("PayPal subscription activated: %s plan=%s customer=%s", sub_id, plan_id, customer_email)
        try:
            self.db.update_subscription(sub_id, status="active")
        except Exception:
            # May not be tracked locally yet — create a stub record
            logger.debug("Subscription %s not in local DB, skipping update", sub_id)

    def _handle_subscription_cancelled(self, event: dict[str, Any]) -> None:
        """Sync a cancelled PayPal subscription."""
        resource = event.get("resource", {})
        sub_id = resource.get("id", "")
        logger.info("PayPal subscription cancelled: %s", sub_id)
        try:
            self.db.update_subscription(sub_id, status="canceled")
        except Exception:
            logger.debug("Subscription %s not in local DB", sub_id)

    def _handle_subscription_payment_failed(self, event: dict[str, Any]) -> None:
        """Log a failed subscription payment for dunning."""
        resource = event.get("resource", {})
        sub_id = resource.get("id", "")
        logger.warning("PayPal subscription payment failed for %s", sub_id)
        try:
            self.db.update_subscription(sub_id, status="past_due")
        except Exception:
            logger.debug("Subscription %s not in local DB", sub_id)

    def _handle_payment_completed(self, event: dict[str, Any]) -> None:
        """Record a completed PayPal payment."""
        resource = event.get("resource", {})
        payment_id = resource.get("id", "")
        amount = resource.get("amount", {})
        logger.info(
            "PayPal payment completed: %s amount=%s %s",
            payment_id,
            amount.get("total", "0"),
            amount.get("currency", "USD"),
        )
        try:
            self.db.update_payment_status(payment_id, "succeeded")
        except Exception:
            logger.debug("Payment %s not in local DB", payment_id)

    def _handle_payment_denied(self, event: dict[str, Any]) -> None:
        """Log a denied PayPal payment."""
        resource = event.get("resource", {})
        payment_id = resource.get("id", "")
        logger.warning("PayPal payment denied: %s", payment_id)
        try:
            self.db.update_payment_status(payment_id, "failed")
        except Exception:
            logger.debug("Payment %s not in local DB", payment_id)

    def _handle_invoice_paid(self, event: dict[str, Any]) -> None:
        """Record a paid PayPal invoice."""
        resource = event.get("resource", {})
        invoice_id = resource.get("id", "")
        logger.info("PayPal invoice paid: %s", invoice_id)
        try:
            self.db.update_invoice_status(invoice_id, "paid")
        except Exception:
            logger.debug("Invoice %s not in local DB", invoice_id)

    def _handle_invoice_payment_failed(self, event: dict[str, Any]) -> None:
        """Handle a failed PayPal invoice payment — flag for dunning."""
        resource = event.get("resource", {})
        invoice_id = resource.get("id", "")
        logger.warning("PayPal invoice payment failed: %s", invoice_id)
        try:
            self.db.update_invoice_status(invoice_id, "past_due")
        except Exception:
            logger.debug("Invoice %s not in local DB", invoice_id)
