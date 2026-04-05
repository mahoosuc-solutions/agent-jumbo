"""
Tests for DunningManager — automated failed-payment recovery logic.

Uses a real temp SQLite DB (via StripePaymentDatabase) so the business logic
runs against actual SQL rather than mocks. External calls (provider.retry_payment,
email send) are patched.

Note: _get_last_attempt_time() is currently a stub returning None, so the
time-window gating (e.g. "wait 3 days before retry attempt 1") is bypassed.
Every past-due item is acted on in each cycle. Tests reflect this behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

if TYPE_CHECKING:
    from pathlib import Path

from instruments.custom.stripe_payments.dunning_manager import (
    DunningAction,
    DunningManager,
    DunningReport,
)
from instruments.custom.stripe_payments.stripe_db import StripePaymentDatabase


def _make_db(tmp_path: Path) -> StripePaymentDatabase:
    return StripePaymentDatabase(str(tmp_path / "test_dunning.db"))


def _make_manager(db) -> DunningManager:
    return DunningManager(db)


def _seed_past_due_invoice(db, invoice_id="inv_001", customer_id="cus_001", amount=5000):
    db.add_invoice(
        stripe_invoice_id=invoice_id,
        stripe_customer_id=customer_id,
        status="past_due",
        amount_due=amount,
        currency="usd",
    )


# ---------------------------------------------------------------------------
# DunningReport
# ---------------------------------------------------------------------------


class TestDunningReport:
    def test_to_dict_has_expected_keys(self):
        report = DunningReport(total_past_due=3, retried=1, emailed=2, paused=0, canceled=0)
        d = report.to_dict()
        assert d["total_past_due"] == 3
        assert d["retried"] == 1
        assert d["emailed"] == 2
        assert "at_risk_mrr_dollars" in d

    def test_mrr_cents_converted_to_dollars(self):
        report = DunningReport(at_risk_mrr_cents=25000)
        assert report.to_dict()["at_risk_mrr_dollars"] == 250.0

    def test_defaults_are_all_zero(self):
        report = DunningReport()
        assert report.total_past_due == 0
        assert report.retried == 0
        assert report.errors == []

    def test_errors_list_independent_per_instance(self):
        r1 = DunningReport()
        r2 = DunningReport()
        r1.errors.append("err")
        assert r2.errors == []


# ---------------------------------------------------------------------------
# run_dunning_cycle — empty DB
# ---------------------------------------------------------------------------


class TestDunningCycleEmpty:
    def test_empty_db_returns_zero_totals(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        report = mgr.run_dunning_cycle()
        assert report.total_past_due == 0
        assert report.retried == 0
        assert report.errors == []

    def test_report_to_dict_serializes_cleanly(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        report = mgr.run_dunning_cycle()
        d = report.to_dict()
        import json

        json.dumps(d)  # must not raise


# ---------------------------------------------------------------------------
# run_dunning_cycle — with past-due items
# ---------------------------------------------------------------------------


class TestDunningCycleWithItems:
    def test_past_due_invoice_is_processed(self, tmp_path):
        db = _make_db(tmp_path)
        _seed_past_due_invoice(db)
        mgr = _make_manager(db)

        with patch("instruments.custom.stripe_payments.payment_router.PaymentRouter") as mock_router:
            mock_provider = MagicMock()
            mock_provider.retry_payment.return_value = {"status": "failed"}
            mock_router.get_provider.return_value = mock_provider
            report = mgr.run_dunning_cycle()

        assert report.total_past_due >= 1

    def test_successful_retry_marks_invoice_paid(self, tmp_path):
        db = _make_db(tmp_path)
        _seed_past_due_invoice(db, invoice_id="inv_success")
        mgr = _make_manager(db)

        with patch("instruments.custom.stripe_payments.payment_router.PaymentRouter") as mock_router:
            mock_provider = MagicMock()
            mock_provider.retry_payment.return_value = {"status": "paid"}
            mock_router.get_provider.return_value = mock_provider
            report = mgr.run_dunning_cycle()

        assert report.retried >= 1
        updated = db.get_invoice_by_id("inv_success")
        assert updated is not None
        assert updated.get("status") == "paid"

    def test_at_risk_mrr_accumulates_from_past_due(self, tmp_path):
        db = _make_db(tmp_path)
        # Two invoices: $50 + $30 = $80
        _seed_past_due_invoice(db, invoice_id="inv_a", amount=5000)
        _seed_past_due_invoice(db, invoice_id="inv_b", amount=3000)
        mgr = _make_manager(db)

        with patch("instruments.custom.stripe_payments.payment_router.PaymentRouter") as mock_router:
            mock_provider = MagicMock()
            mock_provider.retry_payment.return_value = {"status": "failed"}
            mock_router.get_provider.return_value = mock_provider
            report = mgr.run_dunning_cycle()

        assert report.at_risk_mrr_cents >= 8000

    def test_provider_error_is_captured_not_raised(self, tmp_path):
        db = _make_db(tmp_path)
        _seed_past_due_invoice(db, invoice_id="inv_err")
        mgr = _make_manager(db)

        with patch("instruments.custom.stripe_payments.payment_router.PaymentRouter") as mock_router:
            mock_router.get_provider.side_effect = RuntimeError("provider offline")
            report = mgr.run_dunning_cycle()

        # Should not raise; errors are captured
        assert isinstance(report.errors, list)


# ---------------------------------------------------------------------------
# _determine_action
# ---------------------------------------------------------------------------


class TestDetermineAction:
    def test_first_attempt_retries(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        action = mgr._determine_action(0)
        assert action in (DunningAction.RETRY_NOW, DunningAction.SEND_EMAIL)

    def test_max_attempts_cancels(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        action = mgr._determine_action(mgr.max_attempts)
        assert action == DunningAction.CANCEL_SUBSCRIPTION


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------


class TestDunningConfigure:
    def test_max_attempts_updated(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        result = mgr.configure(max_attempts=6)
        assert result["max_attempts"] == 6
        assert mgr.max_attempts == 6

    def test_retry_intervals_updated(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        result = mgr.configure(retry_intervals={1: 1, 2: 2, 3: 3})
        assert result["retry_intervals"][1] == 1
        assert mgr.retry_intervals[1] == 1

    def test_configure_with_none_args_is_noop(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        orig_max = mgr.max_attempts
        mgr.configure(max_attempts=None, retry_intervals=None)
        assert mgr.max_attempts == orig_max


# ---------------------------------------------------------------------------
# get_pending_retries
# ---------------------------------------------------------------------------


class TestGetPendingRetries:
    def test_empty_returns_empty_list(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        result = mgr.get_pending_retries()
        assert result == []

    def test_scheduled_attempt_appears_in_pending(self, tmp_path):
        db = _make_db(tmp_path)
        _seed_past_due_invoice(db)
        mgr = _make_manager(db)

        db.record_dunning_attempt(
            item_id="inv_001",
            customer_id="cus_001",
            attempt_number=1,
            result="scheduled",
        )
        pending = mgr.get_pending_retries()
        assert any(a.get("item_id") == "inv_001" for a in pending)


# ---------------------------------------------------------------------------
# retry_payment_manually
# ---------------------------------------------------------------------------


class TestRetryPaymentManually:
    def test_unknown_invoice_returns_error(self, tmp_path):
        db = _make_db(tmp_path)
        mgr = _make_manager(db)
        result = mgr.retry_payment_manually("inv_nonexistent")
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    def test_successful_manual_retry_marks_paid(self, tmp_path):
        db = _make_db(tmp_path)
        _seed_past_due_invoice(db, invoice_id="inv_manual")
        mgr = _make_manager(db)

        with patch("instruments.custom.stripe_payments.payment_router.PaymentRouter") as mock_router:
            mock_provider = MagicMock()
            mock_provider.retry_payment.return_value = {"status": "paid"}
            mock_router.get_provider.return_value = mock_provider
            result = mgr.retry_payment_manually("inv_manual")

        assert result["status"] == "ok"
        updated = db.get_invoice_by_id("inv_manual")
        assert updated is not None
        assert updated["status"] == "paid"
