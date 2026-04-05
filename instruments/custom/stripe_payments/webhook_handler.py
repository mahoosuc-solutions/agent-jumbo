"""
Stripe Webhook Handler
Processes incoming Stripe webhook events and updates local database state.
Supports idempotent processing via the webhook_events table.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class StripeWebhookHandler:
    """Dispatches Stripe webhook events to typed handlers that update local DB state."""

    def __init__(self, manager):
        self.manager = manager
        self._handlers = {
            "checkout.session.completed": self._handle_checkout_completed,
            "payment_intent.succeeded": self._handle_payment_succeeded,
            "payment_intent.payment_failed": self._handle_payment_failed,
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.paid": self._handle_invoice_paid,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            # Dunning triggers
            "invoice.payment_action_required": self._handle_payment_action_required,
            # Lifecycle notifications
            "customer.subscription.trial_will_end": self._handle_trial_will_end,
            "invoice.upcoming": self._handle_upcoming_invoice,
        }

    def handle_event(self, event_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
        """Process a single webhook event with idempotency.

        Args:
            event_id: Stripe event ID (evt_...).
            event_type: Stripe event type string (e.g. "payment_intent.succeeded").
            data: The ``data.object`` payload from the event.

        Returns:
            Dict with processing result including status and any details.
        """
        # Idempotency: check if already processed
        # Use the webhook_events table if available (stripe_db pattern)
        try:
            existing_event = self._get_webhook_event(event_id)
            if existing_event and existing_event.get("processed"):
                logger.info("Event %s already processed, skipping", event_id)
                return {"status": "already_processed", "event_id": event_id}
        except Exception:
            pass  # webhook_events table may not exist in embedded DB

        # Record the event
        self._record_event(event_id, event_type, data)

        # Dispatch to typed handler
        handler = self._handlers.get(event_type)
        if handler is None:
            logger.info("No handler for event type %s, recording only", event_type)
            self._mark_processed(event_id)
            return {"status": "ignored", "event_type": event_type, "event_id": event_id}

        try:
            result = handler(data)
            self._mark_processed(event_id)
            return {"status": "processed", "event_type": event_type, "event_id": event_id, **result}
        except Exception as exc:
            error_msg = str(exc)
            logger.error("Error processing event %s (%s): %s", event_id, event_type, error_msg)
            self._mark_processed(event_id, error=error_msg)
            return {"status": "error", "event_type": event_type, "event_id": event_id, "error": error_msg}

    # ------------------------------------------------------------------
    # Event persistence helpers (work with embedded StripePaymentDatabase)
    # ------------------------------------------------------------------

    def _get_webhook_event(self, event_id: str) -> dict[str, Any] | None:
        """Check if an event has already been recorded."""

        try:
            conn = self.manager.db._connect()
            # Ensure webhook_events table exists
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stripe_event_id TEXT UNIQUE,
                    event_type TEXT,
                    processed INTEGER DEFAULT 0,
                    payload TEXT,
                    error TEXT,
                    created_at TEXT,
                    processed_at TEXT
                )
                """
            )
            conn.commit()
            cur = conn.execute("SELECT * FROM webhook_events WHERE stripe_event_id = ?", (event_id,))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            conn.close()
            return dict(zip(cols, row)) if row else None
        except Exception:
            return None

    def _record_event(self, event_id: str, event_type: str, data: dict[str, Any]) -> None:
        """Record a webhook event for idempotency tracking."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn = self.manager.db._connect()
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stripe_event_id TEXT UNIQUE,
                    event_type TEXT,
                    processed INTEGER DEFAULT 0,
                    payload TEXT,
                    error TEXT,
                    created_at TEXT,
                    processed_at TEXT
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO webhook_events
                    (stripe_event_id, event_type, payload, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, event_type, json.dumps(data), now),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("Failed to record webhook event %s: %s", event_id, exc)

    def _mark_processed(self, event_id: str, error: str | None = None) -> None:
        """Mark a webhook event as processed."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            conn = self.manager.db._connect()
            conn.execute(
                "UPDATE webhook_events SET processed = 1, processed_at = ?, error = ? WHERE stripe_event_id = ?",
                (now, error, event_id),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            logger.warning("Failed to mark event %s processed: %s", event_id, exc)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _handle_checkout_completed(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle checkout.session.completed — record payment, update pipeline."""
        session_id = data.get("id", "")
        customer_id = data.get("customer", "")
        amount_total = data.get("amount_total", 0)
        metadata = data.get("metadata") or {}

        # Record/update customer if present
        customer_email = data.get("customer_details", {}).get("email") or data.get("customer_email", "")
        customer_name = data.get("customer_details", {}).get("name") or customer_email
        if customer_id and customer_email:
            try:
                self.manager.db.add_customer(
                    stripe_customer_id=customer_id,
                    email=customer_email,
                    name=customer_name,
                )
            except Exception:
                # Customer may already exist
                pass

        result: dict[str, Any] = {
            "session_id": session_id,
            "customer_id": customer_id,
            "amount_total": amount_total,
        }

        # Update sales pipeline stage to closed-won if pipeline_id in metadata
        pipeline_id = metadata.get("pipeline_id")
        if pipeline_id:
            try:
                self._update_pipeline_stage(int(pipeline_id), "closed-won")
                result["pipeline_updated"] = True
                result["pipeline_id"] = pipeline_id
            except Exception as exc:
                logger.warning("Failed to update pipeline %s: %s", pipeline_id, exc)
                result["pipeline_updated"] = False

        return result

    def _handle_payment_succeeded(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle payment_intent.succeeded — update local payment status."""
        payment_intent_id = data.get("id", "")
        amount = data.get("amount", 0)
        customer_id = data.get("customer")
        currency = data.get("currency", "usd")
        payment_method = data.get("payment_method_types", [None])[0] if data.get("payment_method_types") else None

        # Upsert payment record as succeeded
        try:
            conn = self.manager.db._connect()
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO payments (stripe_payment_intent_id, amount, currency, status,
                    stripe_customer_id, payment_method, created_at, updated_at)
                VALUES (?, ?, ?, 'succeeded', ?, ?, ?, ?)
                ON CONFLICT(stripe_payment_intent_id) DO UPDATE SET
                    status = 'succeeded', updated_at = ?
                """,
                (payment_intent_id, amount, currency, customer_id, payment_method, now, now, now),
            )
            conn.commit()
            conn.close()
        except Exception:
            # payments table may use the embedded schema without UNIQUE constraint
            pass

        return {
            "payment_intent_id": payment_intent_id,
            "amount": amount,
            "currency": currency,
        }

    def _handle_payment_failed(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle payment_intent.payment_failed — record failure."""
        payment_intent_id = data.get("id", "")
        amount = data.get("amount", 0)
        error = data.get("last_payment_error", {})
        error_message = error.get("message", "Unknown payment failure") if error else "Unknown payment failure"

        try:
            conn = self.manager.db._connect()
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO payments (stripe_payment_intent_id, amount, currency, status,
                    metadata, created_at, updated_at)
                VALUES (?, ?, 'usd', 'failed', ?, ?, ?)
                ON CONFLICT(stripe_payment_intent_id) DO UPDATE SET
                    status = 'failed', metadata = ?, updated_at = ?
                """,
                (
                    payment_intent_id,
                    amount,
                    json.dumps({"error": error_message}),
                    now,
                    now,
                    json.dumps({"error": error_message}),
                    now,
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        return {
            "payment_intent_id": payment_intent_id,
            "amount": amount,
            "error": error_message,
        }

    def _handle_subscription_created(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle customer.subscription.created — store new subscription."""
        sub_id = data.get("id", "")
        customer_id = data.get("customer", "")
        status = data.get("status", "active")
        current_period_start = data.get("current_period_start")
        current_period_end = data.get("current_period_end")

        # Extract price from items
        items = data.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else None
        amount_cents = items[0]["price"].get("unit_amount", 0) if items else 0
        interval = items[0]["price"].get("recurring", {}).get("interval", "month") if items else "month"

        # Convert epoch timestamps to ISO strings
        period_start = (
            datetime.fromtimestamp(current_period_start, tz=timezone.utc).isoformat() if current_period_start else None
        )
        period_end = (
            datetime.fromtimestamp(current_period_end, tz=timezone.utc).isoformat() if current_period_end else None
        )

        self.manager.db.add_subscription(
            stripe_subscription_id=sub_id,
            stripe_customer_id=customer_id,
            stripe_price_id=price_id or "",
            status=status,
            current_period_start=period_start,
            current_period_end=period_end,
            amount_cents=amount_cents,
            recurring_interval=interval,
        )

        return {
            "subscription_id": sub_id,
            "customer_id": customer_id,
            "status": status,
        }

    def _handle_subscription_updated(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle customer.subscription.updated — update local state."""
        sub_id = data.get("id", "")
        status = data.get("status", "active")
        cancel_at_period_end = data.get("cancel_at_period_end", False)

        items = data.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else None
        amount_cents = items[0]["price"].get("unit_amount", 0) if items else None

        update_kwargs: dict[str, Any] = {"status": status}
        if cancel_at_period_end:
            update_kwargs["cancel_at_period_end"] = 1
        if price_id:
            update_kwargs["stripe_price_id"] = price_id
        if amount_cents is not None:
            update_kwargs["amount_cents"] = amount_cents

        self.manager.db.update_subscription(sub_id, **update_kwargs)

        return {
            "subscription_id": sub_id,
            "status": status,
            "cancel_at_period_end": cancel_at_period_end,
        }

    def _handle_subscription_deleted(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle customer.subscription.deleted — mark as canceled."""
        sub_id = data.get("id", "")
        canceled_at = data.get("canceled_at")

        canceled_iso = (
            datetime.fromtimestamp(canceled_at, tz=timezone.utc).isoformat()
            if canceled_at
            else datetime.now(timezone.utc).isoformat()
        )

        self.manager.db.update_subscription(
            sub_id,
            status="canceled",
            canceled_at=canceled_iso,
        )

        return {"subscription_id": sub_id, "status": "canceled"}

    def _handle_invoice_paid(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle invoice.paid — update invoice status."""
        invoice_id = data.get("id", "")
        customer_id = data.get("customer", "")
        amount_paid = data.get("amount_paid", 0)

        self.manager.db.update_invoice(
            invoice_id,
            status="paid",
            amount_due=0,
            finalized_at=datetime.now(timezone.utc).isoformat(),
        )

        return {
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "amount_paid": amount_paid,
        }

    def _handle_invoice_payment_failed(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle invoice.payment_failed — mark invoice as past_due."""
        invoice_id = data.get("id", "")
        customer_id = data.get("customer", "")
        amount_due = data.get("amount_due", 0)
        attempt_count = data.get("attempt_count", 0)

        self.manager.db.update_invoice(
            invoice_id,
            status="past_due",
        )

        return {
            "invoice_id": invoice_id,
            "customer_id": customer_id,
            "amount_due": amount_due,
            "attempt_count": attempt_count,
        }

    def _handle_payment_action_required(self, data: dict[str, Any]) -> dict[str, Any]:
        """Invoice requires additional customer action (3DS). Treat as payment failure for dunning."""
        invoice_id = data.get("id", "")
        customer_id = data.get("customer", "")
        logger.warning("Payment action required for invoice %s customer %s — marking past_due", invoice_id, customer_id)
        try:
            self.manager.db.update_invoice_status(invoice_id, "past_due")
        except Exception as exc:
            logger.debug("update_invoice_status: %s", exc)
        return {"invoice_id": invoice_id, "customer_id": customer_id, "status": "past_due"}

    def _handle_trial_will_end(self, data: dict[str, Any]) -> dict[str, Any]:
        """Subscription trial ending in 3 days. Log for notification pipeline."""
        sub_id = data.get("id", "")
        customer_id = data.get("customer", "")
        trial_end = data.get("trial_end", "")
        logger.info("Trial ending soon: subscription=%s customer=%s trial_end=%s", sub_id, customer_id, trial_end)
        # Future: hook into email notification system
        return {"subscription_id": sub_id, "customer_id": customer_id, "trial_end": trial_end}

    def _handle_upcoming_invoice(self, data: dict[str, Any]) -> dict[str, Any]:
        """Upcoming invoice notification. Log for advance billing notification."""
        customer_id = data.get("customer", "")
        amount_due = data.get("amount_due", 0)
        next_payment_attempt = data.get("next_payment_attempt", "")
        logger.info(
            "Upcoming invoice: customer=%s amount=%d due=%s",
            customer_id,
            amount_due,
            next_payment_attempt,
        )
        return {"customer_id": customer_id, "amount_due": amount_due}

    # ------------------------------------------------------------------
    # Cross-system helpers
    # ------------------------------------------------------------------

    def _update_pipeline_stage(self, pipeline_id: int, stage: str) -> None:
        """Update a sales pipeline entry stage in the lifecycle database."""
        import sqlite3

        from python.helpers.files import get_abs_path

        db_path = get_abs_path("instruments", "custom", "customer_lifecycle", "data", "customer_lifecycle.db")
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                "UPDATE pipeline SET stage = ? WHERE pipeline_id = ?",
                (stage, pipeline_id),
            )
            conn.commit()
            conn.close()
            logger.info("Updated pipeline %d to stage '%s'", pipeline_id, stage)
        except Exception as exc:
            logger.error("Failed to update pipeline %d: %s", pipeline_id, exc)
            raise
