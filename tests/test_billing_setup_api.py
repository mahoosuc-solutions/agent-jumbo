import asyncio
import threading

from flask import Flask

from python.api.billing_catalog import BillingCatalog
from python.api.billing_catalog_sync import BillingCatalogSync
from python.api.billing_setup_session import BillingSetupSession
from python.api.billing_setup_status import BillingSetupStatus


def test_billing_setup_status_returns_journey_and_playbooks():
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    handler = BillingSetupStatus(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_status?tenant_id=test-tenant&provider=stripe&mock=true", method="GET"
    ) as ctx:
        response = asyncio.run(handler.handle_request(ctx.request))

    assert response.status_code == 200
    body = response.get_json()
    assert body["provider"] == "stripe"
    assert body["journey"]["current_stage"] in {
        "discover",
        "connect",
        "configure",
        "catalog",
        "validate",
        "operate",
    }
    assert isinstance(body["process_playbooks"], list)


def test_billing_setup_session_creates_guided_session():
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    handler = BillingSetupSession(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_session",
        method="POST",
        json={
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "business_name": "Test Tenant",
            "email": "billing@test-tenant.example",
            "country": "US",
        },
    ) as ctx:
        response = asyncio.run(handler.handle_request(ctx.request))

    assert response.status_code == 200
    body = response.get_json()
    assert body["session"]["tenant_id"] == "test-tenant"
    assert body["session"]["provider"] == "stripe"
    assert body["next_step"]["title"] == "Navigate to Stripe registration"


def test_billing_catalog_sync_dry_run_returns_catalog_payload():
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    handler = BillingCatalogSync(app, threading.Lock())
    with app.test_request_context(
        "/billing_catalog_sync",
        method="POST",
        json={
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "apply": False,
            "mock": True,
        },
    ) as ctx:
        response = asyncio.run(handler.handle_request(ctx.request))

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] in {"dry_run", "missing_credentials"}
    assert "offers" in body
    assert isinstance(body["offers"], list)


def test_billing_catalog_post_updates_offer():
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    handler = BillingCatalog(app, threading.Lock())
    with app.test_request_context(
        "/billing_catalog",
        method="POST",
        json={
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "slug": "pro",
            "active": False,
            "monthly_price_usd": 129,
            "setup_price_usd": 49,
        },
    ) as ctx:
        response = asyncio.run(handler.handle_request(ctx.request))

    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "updated"
    assert body["offer"]["slug"] == "pro"
    assert body["offer"]["active"] is False
    assert body["offer"]["monthly_price_usd"] == 129.0
    assert body["offer"]["sync_status"] == "inactive"
