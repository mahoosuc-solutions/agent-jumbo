"""E2E tests for tenant billing setup and catalog APIs."""

import pytest

from tests.e2e.helpers import api_get, api_post

pytestmark = [pytest.mark.e2e]


def test_billing_setup_status_exposes_journey_and_playbooks(app_server, auth_cookies):
    data = api_get(app_server, auth_cookies, "billing_setup_status?tenant_id=test-tenant&provider=stripe&mock=true")

    assert data["provider"] == "stripe"
    assert "journey" in data
    assert data["journey"]["current_stage"] in {
        "discover",
        "connect",
        "configure",
        "catalog",
        "validate",
        "operate",
    }
    assert isinstance(data.get("process_playbooks"), list)


def test_billing_setup_session_creates_stripe_guided_session(app_server, auth_cookies):
    data = api_post(
        app_server,
        auth_cookies,
        "billing_setup_session",
        {
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "business_name": "Test Tenant",
            "email": "billing@test-tenant.example",
            "country": "US",
        },
    )

    assert data["session"]["tenant_id"] == "test-tenant"
    assert data["session"]["provider"] == "stripe"
    assert data["next_step"]["title"] == "Navigate to Stripe registration"


def test_billing_catalog_sync_dry_run_returns_offers(app_server, auth_cookies):
    data = api_post(
        app_server,
        auth_cookies,
        "billing_catalog_sync",
        {
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "apply": False,
            "mock": True,
        },
    )

    assert data["status"] in {"dry_run", "missing_credentials"}
    assert "offers" in data
    assert isinstance(data["offers"], list)
