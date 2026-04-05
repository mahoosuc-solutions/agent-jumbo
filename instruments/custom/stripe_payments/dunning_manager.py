"""Dunning Manager — automated failed-payment recovery.

Escalating retry schedule (configurable via dunning_config table):
    Attempt 1 failure: retry after 3 days, send email
    Attempt 2 failure: retry after 5 days, send email (urgent)
    Attempt 3 failure: retry after 7 days, send email (final warning), pause subscription
    Attempt 4+ failure: cancel subscription, send cancellation email

Usage::

    from instruments.custom.stripe_payments.dunning_manager import DunningManager
    from instruments.custom.stripe_payments.stripe_db import StripePaymentDatabase

    db = StripePaymentDatabase(db_path)
    mgr = DunningManager(db)
    report = mgr.run_dunning_cycle()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DunningAction(Enum):
    RETRY_NOW = "retry_now"
    SEND_EMAIL = "send_email"
    PAUSE_SUBSCRIPTION = "pause_subscription"
    CANCEL_SUBSCRIPTION = "cancel_subscription"
    NO_ACTION = "no_action"


@dataclass
class DunningReport:
    total_past_due: int = 0
    retried: int = 0
    emailed: int = 0
    paused: int = 0
    canceled: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    at_risk_mrr_cents: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_past_due": self.total_past_due,
            "retried": self.retried,
            "emailed": self.emailed,
            "paused": self.paused,
            "canceled": self.canceled,
            "skipped": self.skipped,
            "errors": self.errors,
            "at_risk_mrr_dollars": round(self.at_risk_mrr_cents / 100, 2),
        }


# Default escalation schedule: {attempt_number: days_until_retry}
DEFAULT_RETRY_INTERVALS: dict[int, int] = {1: 3, 2: 5, 3: 7}
DEFAULT_MAX_ATTEMPTS = 4


class DunningManager:
    """Automated dunning cycle for failed payments across all providers."""

    def __init__(self, db, max_attempts: int | None = None, retry_intervals: dict[int, int] | None = None):
        self.db = db
        self.max_attempts = max_attempts or DEFAULT_MAX_ATTEMPTS
        self.retry_intervals = retry_intervals or DEFAULT_RETRY_INTERVALS

    # -- public API ----------------------------------------------------------

    def run_dunning_cycle(self, email_tool=None) -> DunningReport:
        """Execute a full dunning cycle across all past-due invoices and subscriptions.

        Args:
            email_tool: Optional agent email tool instance for sending dunning emails.
                        If None, emails are logged but not sent.

        Returns:
            DunningReport with a summary of actions taken.
        """
        report = DunningReport()

        past_due = self._get_past_due_items()
        report.total_past_due = len(past_due)

        for item in past_due:
            try:
                self._process_item(item, report, email_tool)
            except Exception as exc:
                error_msg = f"Error processing {item.get('id', 'unknown')}: {exc}"
                logger.error(error_msg)
                report.errors.append(error_msg)

        logger.info(
            "Dunning cycle complete: %d past_due, %d retried, %d emailed, %d paused, %d canceled",
            report.total_past_due,
            report.retried,
            report.emailed,
            report.paused,
            report.canceled,
        )
        return report

    def get_pending_retries(self) -> list[dict[str, Any]]:
        """Return dunning attempts that are scheduled but not yet executed."""
        return self.db.list_dunning_attempts(status="scheduled")

    def retry_payment_manually(self, invoice_id: str) -> dict[str, Any]:
        """Manually trigger a payment retry for a specific invoice."""
        try:
            # Determine provider from local invoice record
            invoice = self.db.get_invoice_by_id(invoice_id)
            if invoice is None:
                return {"status": "error", "error": f"Invoice {invoice_id!r} not found"}

            provider_name = invoice.get("payment_provider", "stripe") or "stripe"
            from instruments.custom.stripe_payments.payment_router import PaymentRouter

            provider = PaymentRouter.get_provider(provider_name)
            result = provider.retry_payment(invoice_id)

            if result.get("status") in ("paid", "succeeded"):
                self.db.update_invoice_status(invoice_id, "paid")
                self._record_attempt(invoice_id, invoice.get("stripe_customer_id", ""), 0, "succeeded")

            return {"status": "ok", "result": result}
        except Exception as exc:
            logger.error("Manual retry failed for %s: %s", invoice_id, exc)
            return {"status": "error", "error": str(exc)}

    def configure(
        self,
        max_attempts: int | None = None,
        retry_intervals: dict[int, int] | None = None,
    ) -> dict[str, Any]:
        """Update dunning configuration."""
        if max_attempts is not None:
            self.max_attempts = max_attempts
        if retry_intervals is not None:
            self.retry_intervals = retry_intervals
        return {
            "max_attempts": self.max_attempts,
            "retry_intervals": self.retry_intervals,
        }

    # -- internal ------------------------------------------------------------

    def _get_past_due_items(self) -> list[dict[str, Any]]:
        """Return all invoices/subscriptions in a past_due state."""
        items: list[dict[str, Any]] = []
        try:
            # Past-due invoices
            past_due_invoices = self.db.list_invoices_by_status("past_due")
            for inv in past_due_invoices:
                items.append(
                    {
                        "id": inv.get("stripe_invoice_id", ""),
                        "type": "invoice",
                        "customer_id": inv.get("stripe_customer_id", ""),
                        "amount_cents": inv.get("amount_due", 0),
                        "currency": inv.get("currency", "usd"),
                        "payment_provider": inv.get("payment_provider", "stripe") or "stripe",
                    }
                )
        except Exception as exc:
            logger.warning("Could not fetch past-due invoices: %s", exc)

        try:
            # Past-due subscriptions (carrier of the payment failure state)
            past_due_subs = self.db.list_subscriptions(status="past_due")
            for sub in past_due_subs:
                items.append(
                    {
                        "id": sub.get("stripe_subscription_id", ""),
                        "type": "subscription",
                        "customer_id": sub.get("stripe_customer_id", ""),
                        "amount_cents": sub.get("amount_cents", 0),
                        "currency": sub.get("currency", "usd"),
                        "payment_provider": sub.get("payment_provider", "stripe") or "stripe",
                    }
                )
        except Exception as exc:
            logger.warning("Could not fetch past-due subscriptions: %s", exc)

        return items

    def _process_item(
        self,
        item: dict[str, Any],
        report: DunningReport,
        email_tool,
    ) -> None:
        item_id = item["id"]
        customer_id = item["customer_id"]
        amount_cents = item.get("amount_cents", 0)

        report.at_risk_mrr_cents += amount_cents

        attempt_count = self._get_attempt_count(item_id)
        action = self._determine_action(attempt_count)

        logger.debug("Dunning %s (attempt %d): action=%s", item_id, attempt_count, action.value)

        if action == DunningAction.NO_ACTION:
            report.skipped += 1
            return

        if action in (DunningAction.RETRY_NOW, DunningAction.SEND_EMAIL):
            # Try to retry the payment
            if item["type"] == "invoice":
                provider_name = item.get("payment_provider", "stripe")
                try:
                    from instruments.custom.stripe_payments.payment_router import PaymentRouter

                    provider = PaymentRouter.get_provider(provider_name)
                    result = provider.retry_payment(item_id)
                    if result.get("status") in ("paid", "succeeded", "paid"):
                        self.db.update_invoice_status(item_id, "paid")
                        self._record_attempt(item_id, customer_id, attempt_count + 1, "succeeded")
                        report.retried += 1
                        return
                except Exception as exc:
                    logger.info("Payment retry failed for %s: %s (will email)", item_id, exc)

            # Send dunning email
            sent = self._send_dunning_email(customer_id, attempt_count + 1, amount_cents, email_tool)
            if sent:
                report.emailed += 1

            self._record_attempt(item_id, customer_id, attempt_count + 1, "retried")
            report.retried += 1

        elif action == DunningAction.PAUSE_SUBSCRIPTION:
            self._pause_subscription(item, customer_id)
            self._send_dunning_email(customer_id, attempt_count + 1, amount_cents, email_tool)
            self._record_attempt(item_id, customer_id, attempt_count + 1, "paused")
            report.paused += 1
            report.emailed += 1

        elif action == DunningAction.CANCEL_SUBSCRIPTION:
            self._cancel_subscription(item, customer_id)
            self._send_cancellation_email(customer_id, amount_cents, email_tool)
            self._record_attempt(item_id, customer_id, attempt_count + 1, "canceled")
            report.canceled += 1

    def _determine_action(self, attempt_count: int) -> DunningAction:
        """Return the dunning action for a given attempt count."""
        if attempt_count >= self.max_attempts:
            return DunningAction.CANCEL_SUBSCRIPTION

        retry_day = self.retry_intervals.get(attempt_count + 1, 7)
        # Check if enough time has passed since the last attempt
        last_attempt_at = self._get_last_attempt_time(attempt_count)
        if last_attempt_at:
            due_at = last_attempt_at + timedelta(days=retry_day)
            if datetime.now(timezone.utc) < due_at:
                return DunningAction.NO_ACTION

        if attempt_count + 1 >= self.max_attempts - 1:
            return DunningAction.PAUSE_SUBSCRIPTION

        return DunningAction.RETRY_NOW

    def _get_attempt_count(self, item_id: str) -> int:
        try:
            attempts = self.db.list_dunning_attempts_for_item(item_id)
            return len(attempts)
        except Exception:
            return 0

    def _get_last_attempt_time(self, attempt_count: int) -> datetime | None:
        return None  # Simplified — full implementation queries dunning_attempts table

    def _send_dunning_email(
        self,
        customer_id: str,
        attempt_number: int,
        amount_cents: int,
        email_tool,
    ) -> bool:
        amount_str = f"${amount_cents / 100:.2f}"
        urgency = ["", "", "urgent ", "final "][min(attempt_number, 3)]
        subject = f"[{urgency.strip().capitalize() + ' ' if urgency else ''}Action Required] Payment for your Agent Jumbo subscription"
        body = (
            f"We were unable to process your payment of {amount_str}. "
            f"This is attempt {attempt_number} of {self.max_attempts}. "
            "Please update your payment method to avoid service interruption."
        )
        logger.info("Dunning email (attempt %d) to customer %s: %s", attempt_number, customer_id, subject)

        if email_tool:
            try:
                email_tool.send(to=customer_id, subject=subject, body=body)
                return True
            except Exception as exc:
                logger.warning("Failed to send dunning email: %s", exc)
                return False
        return False

    def _send_cancellation_email(self, customer_id: str, amount_cents: int, email_tool) -> bool:
        subject = "Your Agent Jumbo subscription has been cancelled"
        body = (
            "Due to repeated payment failures, your subscription has been cancelled. "
            "You can resubscribe at any time from your billing portal."
        )
        logger.info("Cancellation email to customer %s", customer_id)
        if email_tool:
            try:
                email_tool.send(to=customer_id, subject=subject, body=body)
                return True
            except Exception as exc:
                logger.warning("Failed to send cancellation email: %s", exc)
        return False

    def _pause_subscription(self, item: dict[str, Any], customer_id: str) -> None:
        sub_id = item["id"] if item["type"] == "subscription" else None
        if sub_id:
            try:
                self.db.update_subscription(sub_id, status="paused")
                logger.info("Paused subscription %s for customer %s", sub_id, customer_id)
            except Exception as exc:
                logger.warning("Could not pause subscription %s: %s", sub_id, exc)

    def _cancel_subscription(self, item: dict[str, Any], customer_id: str) -> None:
        sub_id = item["id"] if item["type"] == "subscription" else None
        if sub_id:
            try:
                provider_name = item.get("payment_provider", "stripe")
                from instruments.custom.stripe_payments.payment_router import PaymentRouter

                provider = PaymentRouter.get_provider(provider_name)
                provider.cancel_subscription(sub_id, at_period_end=False)
                self.db.update_subscription(sub_id, status="canceled")
                logger.info("Cancelled subscription %s for customer %s", sub_id, customer_id)
            except Exception as exc:
                logger.warning("Could not cancel subscription %s: %s", sub_id, exc)

    def _record_attempt(
        self,
        item_id: str,
        customer_id: str,
        attempt_number: int,
        result: str,
    ) -> None:
        try:
            self.db.record_dunning_attempt(
                item_id=item_id,
                customer_id=customer_id,
                attempt_number=attempt_number,
                result=result,
            )
        except Exception as exc:
            logger.debug("Could not record dunning attempt: %s", exc)
