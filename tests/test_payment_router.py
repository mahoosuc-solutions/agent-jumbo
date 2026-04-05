"""
Tests for PaymentRouter and the mock Square/PayPal providers.

PaymentRouter is the factory that resolves a PaymentProvider by name string.
These tests verify:
  - correct mock provider returned per name
  - ValueError for unknown providers
  - get_customer_provider falls back to Stripe for missing provider field
  - Each mock provider satisfies the full PaymentProvider interface
  - Provider-specific ID prefixes are consistent
"""

from __future__ import annotations

import pytest

from instruments.custom.stripe_payments.payment_router import PaymentRouter
from instruments.custom.stripe_payments.providers.mock_paypal_provider import MockPayPalProvider
from instruments.custom.stripe_payments.providers.mock_provider import MockStripeProvider
from instruments.custom.stripe_payments.providers.mock_square_provider import MockSquareProvider

# ---------------------------------------------------------------------------
# PaymentRouter.get_provider — factory resolution
# ---------------------------------------------------------------------------


class TestGetProvider:
    def test_stripe_mock_returns_mock_stripe_provider(self):
        p = PaymentRouter.get_provider("stripe", mock=True)
        assert isinstance(p, MockStripeProvider)
        assert p.get_provider_name() == "stripe"

    def test_square_mock_returns_mock_square_provider(self):
        p = PaymentRouter.get_provider("square", mock=True)
        assert isinstance(p, MockSquareProvider)
        assert p.get_provider_name() == "square"

    def test_paypal_mock_returns_mock_paypal_provider(self):
        p = PaymentRouter.get_provider("paypal", mock=True)
        assert isinstance(p, MockPayPalProvider)
        assert p.get_provider_name() == "paypal"

    def test_case_insensitive(self):
        p = PaymentRouter.get_provider("SQUARE", mock=True)
        assert isinstance(p, MockSquareProvider)

    def test_whitespace_stripped(self):
        p = PaymentRouter.get_provider("  paypal  ", mock=True)
        assert isinstance(p, MockPayPalProvider)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown payment provider"):
            PaymentRouter.get_provider("venmo", mock=True)

    def test_error_message_lists_supported_providers(self):
        with pytest.raises(ValueError, match=r"stripe.*square.*paypal"):
            PaymentRouter.get_provider("bitcoin")


# ---------------------------------------------------------------------------
# PaymentRouter.get_customer_provider — DB-driven provider lookup
# ---------------------------------------------------------------------------


class _FakeDB:
    """Minimal stand-in for StripePaymentsDatabase.get_customer()."""

    def __init__(self, provider_field=None):
        self._provider_field = provider_field

    def get_customer(self, customer_id):
        return {"id": customer_id, "payment_provider": self._provider_field}


class TestGetCustomerProvider:
    def test_returns_square_provider_for_square_customer(self):
        db = _FakeDB(provider_field="square")
        p = PaymentRouter.get_customer_provider("cus_001", db)
        assert p.get_provider_name() == "square"

    def test_falls_back_to_stripe_when_provider_none(self):
        db = _FakeDB(provider_field=None)
        p = PaymentRouter.get_customer_provider("cus_001", db)
        assert p.get_provider_name() == "stripe"

    def test_falls_back_to_stripe_when_provider_empty_string(self):
        db = _FakeDB(provider_field="")
        p = PaymentRouter.get_customer_provider("cus_001", db)
        assert p.get_provider_name() == "stripe"

    def test_raises_when_customer_not_found(self):
        class _NotFoundDB:
            def get_customer(self, customer_id):
                return None

        with pytest.raises(ValueError, match="not found"):
            PaymentRouter.get_customer_provider("cus_missing", _NotFoundDB())


# ---------------------------------------------------------------------------
# MockSquareProvider — interface completeness + ID prefix checks
# ---------------------------------------------------------------------------


class TestMockSquareProvider:
    def setup_method(self):
        self.p = MockSquareProvider()

    def test_create_customer_returns_square_id(self):
        result = self.p.create_customer("user@example.com", "Alice")
        assert result["id"].startswith("sqr_cust_mock_")
        assert result["email"] == "user@example.com"
        assert result["provider"] == "square"

    def test_get_customer_echoes_id(self):
        result = self.p.get_customer("sqr_cust_abc")
        assert result["id"] == "sqr_cust_abc"
        assert result["provider"] == "square"

    def test_create_product_has_variation_id(self):
        result = self.p.create_product("Widget", "A widget")
        assert result["id"].startswith("sqr_prod_mock_")
        assert "variation_id" in result  # Square-specific concept
        assert result["provider"] == "square"

    def test_create_price_recurring(self):
        result = self.p.create_price("sqr_prod_001", 2900, recurring_interval="month")
        assert result["type"] == "recurring"
        assert result["unit_amount"] == 2900
        assert result["provider"] == "square"

    def test_create_price_one_time(self):
        result = self.p.create_price("sqr_prod_001", 50000, recurring_interval=None)
        assert result["type"] == "one_time"

    def test_create_checkout_session_has_url(self):
        result = self.p.create_checkout_session("sqr_price_001", "sqr_cust_001")
        assert "url" in result
        assert "square.site" in result["url"]
        assert result["provider"] == "square"

    def test_create_invoice_sums_items(self):
        items = [{"amount": 1000}, {"amount": 2500}]
        result = self.p.create_invoice("sqr_cust_001", items)
        assert result["amount_due"] == 3500
        assert result["status"] == "draft"

    def test_finalize_invoice_returns_unpaid(self):
        result = self.p.finalize_invoice("sqr_inv_001")
        assert result["status"] == "unpaid"
        assert result["id"] == "sqr_inv_001"

    def test_create_subscription_is_active(self):
        result = self.p.create_subscription("sqr_cust_001", "sqr_price_001")
        assert result["status"] == "active"
        assert result["id"].startswith("sqr_sub_mock_")

    def test_cancel_subscription(self):
        result = self.p.cancel_subscription("sqr_sub_001")
        assert result["status"] == "canceled"

    def test_list_payment_methods_returns_card(self):
        methods = self.p.list_payment_methods("sqr_cust_001")
        assert len(methods) >= 1
        assert methods[0]["type"] == "card"

    def test_update_payment_method(self):
        result = self.p.update_customer_payment_method("sqr_cust_001", "tok_abc")
        assert result["status"] == "updated"

    def test_retry_payment(self):
        result = self.p.retry_payment("sqr_pay_001")
        assert result["status"] == "paid"

    def test_billing_portal_has_dashboard_url(self):
        result = self.p.create_billing_portal_session("sqr_cust_001", "https://example.com")
        assert "squareup.com" in result["url"]

    def test_construct_webhook_event_parses_json(self):
        import json

        payload = json.dumps({"type": "payment.completed", "data": {}})
        event = self.p.construct_webhook_event(payload, "sig_header", "secret")
        assert event["type"] == "payment.completed"


# ---------------------------------------------------------------------------
# MockPayPalProvider — interface completeness + ID prefix checks
# ---------------------------------------------------------------------------


class TestMockPayPalProvider:
    def setup_method(self):
        self.p = MockPayPalProvider()

    def test_create_customer_returns_paypal_id(self):
        result = self.p.create_customer("user@example.com", "Bob")
        assert result["id"].startswith("pp_cust_mock_")
        assert result["email"] == "user@example.com"
        assert result["provider"] == "paypal"

    def test_get_customer_echoes_id(self):
        result = self.p.get_customer("pp_cust_xyz")
        assert result["id"] == "pp_cust_xyz"
        assert result["provider"] == "paypal"

    def test_create_product_has_provider(self):
        result = self.p.create_product("Service Plan", "Monthly service")
        assert result["id"].startswith("pp_prod_mock_")
        assert result["provider"] == "paypal"

    def test_create_price_recurring(self):
        result = self.p.create_price("pp_prod_001", 4900, recurring_interval="month")
        assert result["type"] == "recurring"
        assert result["id"].startswith("pp_plan_mock_")  # PayPal uses "plan" concept

    def test_create_price_one_time(self):
        result = self.p.create_price("pp_prod_001", 9900, recurring_interval=None)
        assert result["type"] == "one_time"

    def test_create_checkout_session_has_sandbox_url(self):
        result = self.p.create_checkout_session("pp_plan_001", "pp_cust_001")
        assert "paypal.com" in result["url"]
        assert result["provider"] == "paypal"

    def test_create_invoice_sums_items(self):
        items = [{"amount": 5000}, {"amount": 1500}]
        result = self.p.create_invoice("pp_cust_001", items)
        assert result["amount_due"] == 6500

    def test_finalize_invoice_status_sent(self):
        result = self.p.finalize_invoice("pp_inv_001")
        assert result["status"] == "sent"  # PayPal "sends" invoices, Square marks "unpaid"

    def test_create_subscription_has_approve_url(self):
        result = self.p.create_subscription("pp_cust_001", "pp_plan_001")
        assert result["status"] == "active"
        assert "approve_url" in result  # PayPal requires buyer approval

    def test_cancel_subscription_spelling(self):
        result = self.p.cancel_subscription("pp_sub_001")
        # PayPal uses British spelling "cancelled"
        assert result["status"] == "cancelled"

    def test_list_payment_methods_returns_paypal_type(self):
        methods = self.p.list_payment_methods("pp_cust_001")
        assert len(methods) >= 1
        assert methods[0]["type"] == "paypal"

    def test_update_payment_method(self):
        result = self.p.update_customer_payment_method("pp_cust_001", "tok_abc")
        assert result["status"] == "updated"

    def test_retry_payment(self):
        result = self.p.retry_payment("pp_pay_001")
        assert result["status"] == "paid"

    def test_billing_portal_points_to_autopay(self):
        result = self.p.create_billing_portal_session("pp_cust_001", "https://example.com")
        assert "paypal.com" in result["url"]
        assert "autopay" in result["url"]

    def test_construct_webhook_event_parses_json(self):
        import json

        payload = json.dumps({"event_type": "PAYMENT.CAPTURE.COMPLETED"})
        event = self.p.construct_webhook_event(payload, "paypal-sig", "webhook_secret")
        assert event["event_type"] == "PAYMENT.CAPTURE.COMPLETED"


# ---------------------------------------------------------------------------
# Cross-provider consistency — same interface, different field values
# ---------------------------------------------------------------------------


class TestProviderConsistency:
    """Verify all three mock providers satisfy the same behavioral contract."""

    @pytest.mark.parametrize(
        "provider_name,cls",
        [
            ("stripe", MockStripeProvider),
            ("square", MockSquareProvider),
            ("paypal", MockPayPalProvider),
        ],
    )
    def test_get_provider_name_matches_class(self, provider_name, cls):
        p = cls()
        assert p.get_provider_name() == provider_name

    @pytest.mark.parametrize(
        "cls",
        [MockStripeProvider, MockSquareProvider, MockPayPalProvider],
    )
    def test_create_customer_has_id_email_name(self, cls):
        p = cls()
        result = p.create_customer("test@example.com", "Test User")
        assert "id" in result
        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"

    @pytest.mark.parametrize(
        "cls",
        [MockStripeProvider, MockSquareProvider, MockPayPalProvider],
    )
    def test_create_subscription_has_id_and_status(self, cls):
        p = cls()
        result = p.create_subscription("cust_001", "price_001")
        assert "id" in result
        assert "status" in result

    @pytest.mark.parametrize(
        "cls",
        [MockStripeProvider, MockSquareProvider, MockPayPalProvider],
    )
    def test_billing_portal_has_url(self, cls):
        p = cls()
        result = p.create_billing_portal_session("cust_001", "https://example.com/return")
        assert "url" in result
        assert result["url"].startswith("https://")

    @pytest.mark.parametrize(
        "cls",
        [MockStripeProvider, MockSquareProvider, MockPayPalProvider],
    )
    def test_ids_are_unique_across_calls(self, cls):
        """Mock providers should not return identical IDs on consecutive calls."""
        p = cls()
        r1 = p.create_customer("a@example.com", "A")
        r2 = p.create_customer("b@example.com", "B")
        assert r1["id"] != r2["id"]
