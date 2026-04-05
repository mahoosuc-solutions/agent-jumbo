"""
Tests for StripePaymentManager — core payment business logic.

Uses a real temp SQLite DB (StripePaymentsDatabase) so the ORM/SQL layer
is fully exercised. External provider calls (Stripe API) are patched via
the mock provider flag or direct mocking.
"""

from pathlib import Path
from unittest.mock import patch


def _make_manager(tmp_path: Path):
    from instruments.custom.stripe_payments.stripe_manager import StripePaymentManager

    return StripePaymentManager(str(tmp_path / "test_stripe_manager.db"))


# ---------------------------------------------------------------------------
# create_customer
# ---------------------------------------------------------------------------


class TestCreateCustomer:
    def test_creates_customer_with_mock(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.create_customer(email="alice@example.com", name="Alice", mock=True)
        assert result.get("id", "").startswith("cus_mock_")
        assert "local_id" in result

    def test_customer_stored_locally_after_create(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_customer(email="bob@example.com", name="Bob", mock=True)
        customer = mgr.get_customer(email="bob@example.com")
        assert customer is not None
        assert customer["email"] == "bob@example.com"

    def test_duplicate_email_still_stores(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_customer(email="dup@example.com", name="First", mock=True)
        result2 = mgr.create_customer(email="dup@example.com", name="Second", mock=True)
        # A second call creates a second local record (may differ from Stripe dedup)
        assert "local_id" in result2


# ---------------------------------------------------------------------------
# list_customers
# ---------------------------------------------------------------------------


class TestListCustomers:
    def test_empty_db_returns_empty_list(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.list_customers() == []

    def test_returns_all_customers(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.create_customer(email="a@example.com", name="A", mock=True)
        mgr.create_customer(email="b@example.com", name="B", mock=True)
        assert len(mgr.list_customers()) == 2


# ---------------------------------------------------------------------------
# list_products / create_product
# ---------------------------------------------------------------------------


class TestProducts:
    def test_empty_db_returns_no_products(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.list_products() == []

    def test_create_product_stored_locally(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.create_product(name="Widget", description="A widget", mock=True)
        assert "local_id" in result
        products = mgr.list_products()
        assert len(products) == 1
        assert products[0]["name"] == "Widget"

    def test_get_product_by_stripe_id(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.create_product(name="Gadget", description="", mock=True)
        stripe_id = result["id"]
        fetched = mgr.get_product(stripe_product_id=stripe_id)
        assert fetched is not None
        assert fetched["name"] == "Gadget"


# ---------------------------------------------------------------------------
# sync_product_from_portfolio — idempotency
# ---------------------------------------------------------------------------


class TestSyncProductFromPortfolio:
    def _mock_portfolio_product(self):
        return {
            "id": 42,
            "name": "Pro Plan",
            "description": "The pro plan",
            "tagline": "Pro",
            "price": 99.0,
            "price_model": "subscription",
            "project_name": "Platform",
        }

    def test_already_synced_returns_early(self, tmp_path):
        mgr = _make_manager(tmp_path)
        portfolio = self._mock_portfolio_product()

        with patch.object(mgr, "_read_portfolio_product", return_value=portfolio):
            mgr.sync_product_from_portfolio(42, mock=True)
            result2 = mgr.sync_product_from_portfolio(42, mock=True)

        assert result2["status"] == "already_synced"

    def test_missing_portfolio_product_returns_error(self, tmp_path):
        mgr = _make_manager(tmp_path)
        with patch.object(mgr, "_read_portfolio_product", return_value=None):
            result = mgr.sync_product_from_portfolio(999, mock=True)
        assert result["status"] == "error"

    def test_sync_creates_local_product(self, tmp_path):
        mgr = _make_manager(tmp_path)
        portfolio = self._mock_portfolio_product()

        with patch.object(mgr, "_read_portfolio_product", return_value=portfolio):
            result = mgr.sync_product_from_portfolio(42, mock=True)

        assert result["status"] == "synced"
        assert "stripe_product_id" in result

    def test_sync_all_listed_uses_portfolio(self, tmp_path):
        mgr = _make_manager(tmp_path)
        portfolio = self._mock_portfolio_product()

        with patch.object(mgr, "_list_portfolio_listed_products", return_value=[portfolio]):
            with patch.object(mgr, "_read_portfolio_product", return_value=portfolio):
                results = mgr.sync_all_listed_products(mock=True)

        assert len(results) == 1
        assert results[0]["status"] == "synced"


# ---------------------------------------------------------------------------
# sync_customer_from_lifecycle
# ---------------------------------------------------------------------------


class TestSyncCustomerFromLifecycle:
    def _mock_lifecycle_customer(self):
        return {
            "customer_id": 7,
            "email": "lc_user@example.com",
            "name": "Lifecycle User",
            "company": "ACME",
        }

    def test_already_synced_returns_early(self, tmp_path):
        mgr = _make_manager(tmp_path)
        lc = self._mock_lifecycle_customer()

        with patch.object(mgr, "_read_lifecycle_customer", return_value=lc):
            mgr.sync_customer_from_lifecycle(7, mock=True)
            result2 = mgr.sync_customer_from_lifecycle(7, mock=True)

        assert result2["status"] == "already_synced"

    def test_missing_lifecycle_customer_returns_error(self, tmp_path):
        mgr = _make_manager(tmp_path)
        with patch.object(mgr, "_read_lifecycle_customer", return_value=None):
            result = mgr.sync_customer_from_lifecycle(999, mock=True)
        assert result["status"] == "error"

    def test_sync_creates_local_customer(self, tmp_path):
        mgr = _make_manager(tmp_path)
        lc = self._mock_lifecycle_customer()

        with patch.object(mgr, "_read_lifecycle_customer", return_value=lc):
            result = mgr.sync_customer_from_lifecycle(7, mock=True)

        assert result["status"] == "synced"
        assert "stripe_customer_id" in result


# ---------------------------------------------------------------------------
# create_subscription + cancel_subscription
# ---------------------------------------------------------------------------


class TestSubscriptions:
    def test_create_subscription_stored_locally(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.create_subscription(
            stripe_customer_id="cus_mock_abc",
            stripe_price_id="price_mock_xyz",
            mock=True,
        )
        assert result.get("id", "").startswith("sub_mock_")
        subs = mgr.db.list_subscriptions()
        assert len(subs) == 1

    def test_cancel_subscription_updates_status(self, tmp_path):
        mgr = _make_manager(tmp_path)
        create_result = mgr.create_subscription(
            stripe_customer_id="cus_mock_abc",
            stripe_price_id="price_mock_xyz",
            mock=True,
        )
        sub_id = create_result["id"]
        cancel_result = mgr.cancel_subscription(sub_id, at_period_end=False)
        assert cancel_result.get("status") in ("canceled", "cancel_at_period_end")

    def test_create_subscription_with_trial(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.create_subscription(
            stripe_customer_id="cus_mock_trial",
            stripe_price_id="price_mock_xyz",
            trial_days=14,
            mock=True,
        )
        assert result.get("id", "").startswith("sub_mock_")


# ---------------------------------------------------------------------------
# MRR calculation
# ---------------------------------------------------------------------------


class TestMRR:
    def test_empty_db_has_zero_mrr(self, tmp_path):
        mgr = _make_manager(tmp_path)
        assert mgr.get_mrr() == 0.0

    def test_active_subscription_contributes_to_mrr(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.db.add_subscription(
            stripe_subscription_id="sub_mrr_001",
            stripe_customer_id="cus_001",
            stripe_price_id="price_001",
            status="active",
            amount_cents=5000,
            currency="usd",
        )
        assert mgr.get_mrr() == 50.0

    def test_yearly_subscription_normalised_to_monthly(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.db.add_subscription(
            stripe_subscription_id="sub_year_001",
            stripe_customer_id="cus_001",
            stripe_price_id="price_001",
            status="active",
            amount_cents=12000,
            currency="usd",
            recurring_interval="year",
        )
        # 12000 cents annual / 12 = 1000 cents = $10/mo
        assert mgr.get_mrr() == 10.0

    def test_trialing_subscription_included_in_mrr(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.db.add_subscription(
            stripe_subscription_id="sub_trial_001",
            stripe_customer_id="cus_001",
            stripe_price_id="price_001",
            status="trialing",
            amount_cents=2000,
            currency="usd",
        )
        assert mgr.get_mrr() == 20.0

    def test_canceled_subscription_excluded_from_mrr(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.db.add_subscription(
            stripe_subscription_id="sub_canceled_001",
            stripe_customer_id="cus_001",
            stripe_price_id="price_001",
            status="canceled",
            amount_cents=9900,
            currency="usd",
        )
        assert mgr.get_mrr() == 0.0


# ---------------------------------------------------------------------------
# Revenue report
# ---------------------------------------------------------------------------


class TestRevenueReport:
    def test_report_has_expected_keys(self, tmp_path):
        mgr = _make_manager(tmp_path)
        report = mgr.get_revenue_report()
        for key in ("period_days", "total_revenue", "mrr", "arr", "customer_count", "generated_at"):
            assert key in report

    def test_arr_is_twelve_times_mrr(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.db.add_subscription(
            stripe_subscription_id="sub_arr_001",
            stripe_customer_id="cus_001",
            stripe_price_id="price_001",
            status="active",
            amount_cents=10000,
            currency="usd",
        )
        report = mgr.get_revenue_report()
        assert abs(report["arr"] - report["mrr"] * 12) < 0.01


# ---------------------------------------------------------------------------
# Churn report
# ---------------------------------------------------------------------------


class TestChurnReport:
    def test_empty_db_has_zero_churn(self, tmp_path):
        mgr = _make_manager(tmp_path)
        report = mgr.get_churn_report()
        assert report["canceled_subscriptions"] == 0
        assert report["churn_rate"] == 0.0

    def test_canceled_subscription_appears_in_churn(self, tmp_path):
        from datetime import datetime, timezone

        mgr = _make_manager(tmp_path)
        mgr.db.add_subscription(
            stripe_subscription_id="sub_churn_001",
            stripe_customer_id="cus_001",
            stripe_price_id="price_001",
            status="canceled",
            amount_cents=3000,
            currency="usd",
        )
        mgr.db.update_subscription(
            "sub_churn_001",
            canceled_at=datetime.now(timezone.utc).isoformat(),
        )
        report = mgr.get_churn_report(days=30)
        assert report["canceled_subscriptions"] >= 1
        assert report["lost_mrr"] > 0


# ---------------------------------------------------------------------------
# at_risk_revenue
# ---------------------------------------------------------------------------


class TestAtRiskRevenue:
    def test_no_past_due_means_zero_risk(self, tmp_path):
        mgr = _make_manager(tmp_path)
        result = mgr.get_at_risk_revenue()
        assert result["past_due_count"] == 0
        assert result["at_risk_mrr"] == 0.0

    def test_past_due_subscription_counted(self, tmp_path):
        mgr = _make_manager(tmp_path)
        mgr.db.add_subscription(
            stripe_subscription_id="sub_pd_001",
            stripe_customer_id="cus_001",
            stripe_price_id="price_001",
            status="past_due",
            amount_cents=7500,
            currency="usd",
        )
        result = mgr.get_at_risk_revenue()
        assert result["past_due_count"] == 1
        assert result["at_risk_mrr"] == 75.0
