"""
Tests for stripe_catalog_sync.py — catalog sync business logic.

StripeCliClient wraps subprocess calls, so all tests mock _run() and focus
on the decision logic: when to create vs skip products and prices, how
lookup-key deduplication works, and the dry-run summary path.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers — load modules from scripts/ which is not on sys.path by default
# ---------------------------------------------------------------------------
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "stripe_catalog_sync.py"
_spec = importlib.util.spec_from_file_location("stripe_catalog_sync", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["stripe_catalog_sync"] = _mod
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

StripeCliClient = _mod.StripeCliClient
OfferSyncResult = _mod.OfferSyncResult
sync_offer = _mod.sync_offer
build_dry_run_summary = _mod.build_dry_run_summary
_active_matching_price = _mod._active_matching_price
_sync_price = _mod._sync_price


def _make_client(tmp_path: Path) -> StripeCliClient:
    return StripeCliClient(api_key="sk_test_fake", config_home=tmp_path / "stripe_config")  # pragma: allowlist secret


def _make_offer(slug: str = "pro", monthly: float = 29.0, setup: float = 0.0) -> _mod.StripeCatalogOffer:
    from python.helpers.stripe_catalog import StripeCatalogOffer

    return StripeCatalogOffer(
        catalog_family="platform_tier",
        slug=slug,
        name=slug.title(),
        tagline="Test plan",
        description="Test",
        monthly_price_usd=monthly,
        setup_price_usd=setup,
        billing_mode="subscription",
        active=True,
        source_path="docs/product-page/pricing-model.json",
        metadata={"slug": slug},
    )


# ---------------------------------------------------------------------------
# _active_matching_price
# ---------------------------------------------------------------------------


class TestActiveMatchingPrice:
    def test_returns_none_for_empty_list(self):
        assert _active_matching_price([], unit_amount=1000, recurring_interval="month") is None

    def test_returns_matching_active_price(self):
        prices = [
            {"id": "price_1", "active": True, "unit_amount": 1000, "recurring": {"interval": "month"}},
        ]
        result = _active_matching_price(prices, unit_amount=1000, recurring_interval="month")
        assert result is not None
        assert result["id"] == "price_1"

    def test_ignores_inactive_price(self):
        prices = [
            {"id": "price_1", "active": False, "unit_amount": 1000, "recurring": {"interval": "month"}},
        ]
        result = _active_matching_price(prices, unit_amount=1000, recurring_interval="month")
        assert result is None

    def test_ignores_wrong_amount(self):
        prices = [
            {"id": "price_1", "active": True, "unit_amount": 2000, "recurring": {"interval": "month"}},
        ]
        result = _active_matching_price(prices, unit_amount=1000, recurring_interval="month")
        assert result is None

    def test_ignores_wrong_interval(self):
        prices = [
            {"id": "price_1", "active": True, "unit_amount": 1000, "recurring": {"interval": "year"}},
        ]
        result = _active_matching_price(prices, unit_amount=1000, recurring_interval="month")
        assert result is None

    def test_matches_one_time_price_no_recurring(self):
        # One-time price: recurring is None/missing
        prices = [
            {"id": "price_setup", "active": True, "unit_amount": 350000, "recurring": None},
        ]
        result = _active_matching_price(prices, unit_amount=350000, recurring_interval=None)
        assert result is not None
        assert result["id"] == "price_setup"


# ---------------------------------------------------------------------------
# _sync_price
# ---------------------------------------------------------------------------


class TestSyncPrice:
    def test_skips_when_no_lookup_key(self, tmp_path):
        client = _make_client(tmp_path)
        offer = _make_offer(monthly=0.0)
        price_id, created = _sync_price(
            client, offer, lookup_key=None, unit_amount=0, recurring_interval="month", nickname="Monthly"
        )
        assert price_id is None
        assert created is False

    def test_skips_when_amount_is_zero(self, tmp_path):
        client = _make_client(tmp_path)
        offer = _make_offer(monthly=0.0)
        price_id, created = _sync_price(
            client, offer, lookup_key="some_key", unit_amount=0, recurring_interval="month", nickname="Monthly"
        )
        assert price_id is None
        assert created is False

    def test_returns_existing_price_without_creating(self, tmp_path):
        client = _make_client(tmp_path)
        offer = _make_offer(monthly=29.0)

        existing = {"id": "price_existing", "active": True, "unit_amount": 2900, "recurring": {"interval": "month"}}
        with patch.object(client, "list_prices_by_lookup_key", return_value=[existing]):
            with patch.object(client, "create_price") as mock_create:
                price_id, created = _sync_price(
                    client,
                    offer,
                    lookup_key="key_monthly",
                    unit_amount=2900,
                    recurring_interval="month",
                    nickname="Monthly",
                )

        assert price_id == "price_existing"
        assert created is False
        mock_create.assert_not_called()

    def test_creates_new_price_when_none_match(self, tmp_path):
        client = _make_client(tmp_path)
        offer = _make_offer(monthly=29.0)

        new_price = {"id": "price_new"}
        with patch.object(client, "list_prices_by_lookup_key", return_value=[]):
            with patch.object(client, "create_price", return_value=new_price):
                price_id, created = _sync_price(
                    client,
                    offer,
                    lookup_key="key_monthly",
                    unit_amount=2900,
                    recurring_interval="month",
                    nickname="Monthly",
                )

        assert price_id == "price_new"
        assert created is True

    def test_deactivates_stale_price_after_creating_new(self, tmp_path):
        client = _make_client(tmp_path)
        offer = _make_offer(monthly=29.0)

        stale = {"id": "price_stale", "active": True, "unit_amount": 1000, "recurring": {"interval": "month"}}
        new_price = {"id": "price_new"}

        with patch.object(client, "list_prices_by_lookup_key", return_value=[stale]):
            with patch.object(client, "create_price", return_value=new_price):
                with patch.object(client, "deactivate_price") as mock_deactivate:
                    _sync_price(
                        client,
                        offer,
                        lookup_key="key_monthly",
                        unit_amount=2900,
                        recurring_interval="month",
                        nickname="Monthly",
                    )

        mock_deactivate.assert_called_once_with("price_stale")


# ---------------------------------------------------------------------------
# sync_offer
# ---------------------------------------------------------------------------


class TestSyncOffer:
    def test_creates_product_when_missing(self, tmp_path):
        client = _make_client(tmp_path)
        offer = _make_offer(monthly=29.0)

        with patch.object(client, "get_product", return_value=None):
            with patch.object(client, "create_product", return_value={"id": offer.product_id}) as mock_create:
                with patch.object(client, "list_prices_by_lookup_key", return_value=[]):
                    with patch.object(client, "create_price", return_value={"id": "price_new"}):
                        result = sync_offer(client, offer)

        assert result.created_product is True
        mock_create.assert_called_once()

    def test_updates_product_when_exists(self, tmp_path):
        client = _make_client(tmp_path)
        offer = _make_offer(monthly=29.0)

        existing_product = {"id": offer.product_id, "name": offer.name}
        with patch.object(client, "get_product", return_value=existing_product):
            with patch.object(client, "update_product") as mock_update:
                with patch.object(client, "list_prices_by_lookup_key", return_value=[]):
                    with patch.object(client, "create_price", return_value={"id": "price_new"}):
                        result = sync_offer(client, offer)

        assert result.created_product is False
        mock_update.assert_called_once()

    def test_result_has_offer_and_price_ids(self, tmp_path):
        client = _make_client(tmp_path)
        offer = _make_offer(monthly=99.0)

        existing_product = {"id": offer.product_id}
        monthly_price = {"id": "price_monthly", "active": True, "unit_amount": 9900, "recurring": {"interval": "month"}}

        with patch.object(client, "get_product", return_value=existing_product):
            with patch.object(client, "update_product"):
                with patch.object(client, "list_prices_by_lookup_key", return_value=[monthly_price]):
                    result = sync_offer(client, offer)

        assert result.monthly_price_id == "price_monthly"
        assert result.product_id == offer.product_id

    def test_solution_package_with_setup_and_monthly(self, tmp_path):
        from python.helpers.stripe_catalog import StripeCatalogOffer

        client = _make_client(tmp_path)
        offer = StripeCatalogOffer(
            catalog_family="solution_package",
            slug="ai-customer-support",
            name="AI Customer Support",
            tagline="Customer support automation",
            description="Full AI customer support solution",
            monthly_price_usd=750.0,
            setup_price_usd=3500.0,
            billing_mode="setup_and_subscription",
            active=True,
            source_path="solutions/ai-customer-support/solution.json",
            metadata={"slug": "ai-customer-support"},
        )

        existing_product = {"id": offer.product_id}
        monthly_price = {
            "id": "price_monthly_support",
            "active": True,
            "unit_amount": 75000,
            "recurring": {"interval": "month"},
        }
        setup_price = {"id": "price_setup_support", "active": True, "unit_amount": 350000, "recurring": None}

        def lookup_side_effect(lookup_key):
            if "monthly" in lookup_key:
                return [monthly_price]
            if "setup" in lookup_key:
                return [setup_price]
            return []

        with patch.object(client, "get_product", return_value=existing_product):
            with patch.object(client, "update_product"):
                with patch.object(client, "list_prices_by_lookup_key", side_effect=lookup_side_effect):
                    result = sync_offer(client, offer)

        assert result.monthly_price_id == "price_monthly_support"
        assert result.setup_price_id == "price_setup_support"
        assert result.created_monthly_price is False
        assert result.created_setup_price is False


# ---------------------------------------------------------------------------
# build_dry_run_summary
# ---------------------------------------------------------------------------


class TestBuildDryRunSummary:
    def test_summary_has_count_and_offers(self):
        from python.helpers.stripe_catalog import load_commercial_catalog

        offers = load_commercial_catalog()
        summary = build_dry_run_summary(offers)

        assert summary["offer_count"] == len(offers)
        assert len(summary["offers"]) == len(offers)

    def test_each_offer_dict_has_product_id(self):
        from python.helpers.stripe_catalog import load_commercial_catalog

        offers = load_commercial_catalog()
        summary = build_dry_run_summary(offers)

        for offer_dict in summary["offers"]:
            assert "product_id" in offer_dict
            assert offer_dict["product_id"].startswith("mahoosuc_")

    def test_empty_catalog_returns_zero_count(self):
        summary = build_dry_run_summary([])
        assert summary["offer_count"] == 0
        assert summary["offers"] == []
