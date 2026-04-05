"""Square webhook event handler.

Processes Square webhook notifications and syncs event data to the local
StripePaymentDatabase. Mirrors the structure of StripeWebhookHandler.

Square events are idempotent — each event carries a unique ``event_id``
used to prevent duplicate processing.

Handled event types:
    payment.updated              — sync payment status
    invoice.payment_failed       — trigger dunning cycle for failed invoices
    subscription.updated         — sync subscription lifecycle changes
    customer.updated             — refresh local customer record
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class SquareWebhookHandler:
    """Process inbound Square webhook events."""

    def __init__(self, db):
        self.db = db

        self._handlers: dict[str, Any] = {
            "payment.updated": self._handle_payment_updated,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "subscription.updated": self._handle_subscription_updated,
            "customer.updated": self._handle_customer_updated,
        }

    def verify_signature(self, raw_body: str, signature: str, signature_key: str) -> bool:
        """Verify Square HMAC-SHA256 webhook signature.

        Square signs the raw request body with the webhook signature key using HMAC-SHA256
        and base64-encodes the result.
        """
        if not signature or not signature_key:
            return False
        expected = base64.b64encode(
            hmac.new(signature_key.encode(), raw_body.encode(), hashlib.sha256).digest()  # type: ignore[attr-defined]
        ).decode()
        return hmac.compare_digest(expected, signature)

    def handle_event(self, event_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a Square webhook event by type."""
        handler = self._handlers.get(event_type)
        if handler is None:
            return {"status": "ignored", "event_type": event_type, "event_id": event_id}
        try:
            result = handler(data)
            return {"status": "processed", "event_type": event_type, "event_id": event_id, **result}
        except Exception as exc:
            logger.error("Error processing Square event %s (%s): %s", event_id, event_type, exc)
            return {"status": "error", "event_type": event_type, "event_id": event_id, "error": str(exc)}

    def process(self, event: dict[str, Any]) -> dict[str, Any]:
        """Process a Square webhook event dict.

        Args:
            event: The parsed Square event payload.

        Returns:
            Dict with ``status``, ``event_id``, and ``event_type``.
        """
        event_id = event.get("event_id", "")
        event_type = event.get("type", "")

        # Idempotency — skip already-processed events
        existing = self.db.get_webhook_event(event_id) if event_id else None
        if existing and existing.get("processed"):
            logger.info("Square event %s already processed, skipping", event_id)
            return {"status": "duplicate", "event_id": event_id, "event_type": event_type}

        # Record the event
        if event_id:
            try:
                self.db.record_webhook_event(
                    event_id=event_id,
                    event_type=event_type,
                    payload=json.dumps(event),
                )
            except Exception as exc:
                logger.warning("Could not record Square webhook event: %s", exc)

        handler = self._handlers.get(event_type)
        if handler:
            try:
                handler(event)
                if event_id:
                    self.db.mark_webhook_processed(event_id)
                return {"status": "processed", "event_id": event_id, "event_type": event_type}
            except Exception as exc:
                logger.error("Error processing Square event %s (%s): %s", event_id, event_type, exc)
                if event_id:
                    self.db.mark_webhook_error(event_id, str(exc))
                return {"status": "error", "event_id": event_id, "event_type": event_type, "error": str(exc)}

        logger.debug("No handler for Square event type %s", event_type)
        return {"status": "unhandled", "event_id": event_id, "event_type": event_type}

    # -- event handlers ------------------------------------------------------

    def _handle_payment_updated(self, event: dict[str, Any]) -> None:
        """Sync a Square payment status change to the local payments table."""
        data = event.get("data", {}).get("object", {}).get("payment", {})
        payment_id = data.get("id", "")
        status = data.get("status", "").lower()
        if not payment_id:
            return
        logger.info("Square payment %s updated to status %s", payment_id, status)
        # Map Square payment status to internal status
        status_map = {"completed": "succeeded", "failed": "failed", "canceled": "canceled"}
        internal_status = status_map.get(status, status)
        try:
            self.db.update_payment_status(payment_id, internal_status)
        except Exception as exc:
            logger.warning("Could not update payment %s status: %s", payment_id, exc)

    def _handle_invoice_payment_failed(self, event: dict[str, Any]) -> None:
        """Handle a failed Square invoice payment — log for dunning processing."""
        data = event.get("data", {}).get("object", {}).get("invoice", {})
        invoice_id = data.get("id", "")
        customer_id = data.get("primary_recipient", {}).get("customer_id", "")
        logger.warning("Square invoice payment failed: invoice=%s customer=%s", invoice_id, customer_id)
        # Mark invoice as past_due in local DB — dunning_manager.py picks this up
        try:
            self.db.update_invoice_status(invoice_id, "past_due")
        except Exception as exc:
            logger.warning("Could not update invoice %s status: %s", invoice_id, exc)

    def _handle_subscription_updated(self, event: dict[str, Any]) -> None:
        """Sync a Square subscription state change."""
        data = event.get("data", {}).get("object", {}).get("subscription", {})
        sub_id = data.get("id", "")
        status = data.get("status", "").lower()
        if not sub_id:
            return
        logger.info("Square subscription %s updated to %s", sub_id, status)
        # Map Square subscription status
        status_map = {
            "active": "active",
            "canceled": "canceled",
            "deactivated": "canceled",
            "pending": "incomplete",
        }
        internal_status = status_map.get(status, status)
        try:
            self.db.update_subscription(sub_id, status=internal_status)
        except Exception as exc:
            logger.warning("Could not update subscription %s: %s", sub_id, exc)

    def _handle_customer_updated(self, event: dict[str, Any]) -> None:
        """Log customer updates — no local schema change needed currently."""
        data = event.get("data", {}).get("object", {}).get("customer", {})
        customer_id = data.get("id", "")
        logger.info("Square customer %s updated", customer_id)
