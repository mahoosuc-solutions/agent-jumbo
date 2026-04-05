import asyncio
import threading

from flask import Flask

from python.api.billing_catalog import BillingCatalog
from python.api.billing_catalog_sync import BillingCatalogSync
from python.api.billing_setup_session import BillingSetupSession
from python.api.billing_setup_status import BillingSetupStatus
from python.api.billing_setup_workflow_advance import BillingSetupWorkflowAdvance
from python.api.billing_setup_workflow_checkpoints import BillingSetupWorkflowCheckpoints
from python.api.billing_setup_workflow_recover import BillingSetupWorkflowRecover
from python.api.billing_setup_workflow_restart import BillingSetupWorkflowRestart
from python.api.billing_setup_workflow_start import BillingSetupWorkflowStart
from python.api.billing_setup_workflow_status import BillingSetupWorkflowStatus
from python.api.billing_setup_workflow_validate import BillingSetupWorkflowValidate


def configure_test_db(monkeypatch, tmp_path):
    monkeypatch.setenv("PAYMENT_ACCOUNT_SETUP_DB_PATH", str(tmp_path / "payment_setup_api.db"))


def test_billing_setup_status_returns_journey_and_playbooks(monkeypatch, tmp_path):
    configure_test_db(monkeypatch, tmp_path)
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


def test_billing_setup_session_creates_guided_session(monkeypatch, tmp_path):
    configure_test_db(monkeypatch, tmp_path)
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


def test_billing_catalog_sync_dry_run_returns_catalog_payload(monkeypatch, tmp_path):
    configure_test_db(monkeypatch, tmp_path)
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


def test_billing_catalog_post_updates_offer(monkeypatch, tmp_path):
    configure_test_db(monkeypatch, tmp_path)
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


def test_billing_setup_workflow_start_returns_run_and_evidence(monkeypatch, tmp_path):
    configure_test_db(monkeypatch, tmp_path)
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    handler = BillingSetupWorkflowStart(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_start",
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
    assert body["workflow"]["workflow_type"] == "stripe_onboarding"
    assert body["workflow"]["run_id"].startswith("stripe_workflow_")
    assert isinstance(body["evidence"], list)


def test_billing_setup_workflow_status_returns_latest_run(monkeypatch, tmp_path):
    configure_test_db(monkeypatch, tmp_path)
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    starter = BillingSetupWorkflowStart(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_start",
        method="POST",
        json={
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "business_name": "Test Tenant",
            "email": "billing@test-tenant.example",
            "country": "US",
        },
    ) as ctx:
        asyncio.run(starter.handle_request(ctx.request))

    handler = BillingSetupWorkflowStatus(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_status?tenant_id=test-tenant&provider=stripe&mock=true",
        method="GET",
    ) as ctx:
        response = asyncio.run(handler.handle_request(ctx.request))

    assert response.status_code == 200
    body = response.get_json()
    assert body["workflow"]["run_id"].startswith("stripe_workflow_")
    assert body["status"]["provider"] == "stripe"


def test_billing_setup_workflow_validate_prepares_checkout(monkeypatch, tmp_path):
    configure_test_db(monkeypatch, tmp_path)
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    start_handler = BillingSetupWorkflowStart(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_start",
        method="POST",
        json={
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "business_name": "Test Tenant",
            "email": "billing@test-tenant.example",
            "country": "US",
        },
    ) as ctx:
        started = asyncio.run(start_handler.handle_request(ctx.request)).get_json()

    run_id = started["workflow"]["run_id"]
    advance_handler = BillingSetupWorkflowAdvance(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_advance",
        method="POST",
        json={"run_id": run_id, "human_confirmed": False, "step_result": {}},
    ) as ctx:
        response = asyncio.run(advance_handler.handle_request(ctx.request))
    assert response.status_code == 200

    store_handler = BillingCatalogSync(app, threading.Lock())
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
        dry_run = asyncio.run(store_handler.handle_request(ctx.request))
    assert dry_run.status_code == 200

    from python.api.billing_setup_store_credentials import BillingSetupStoreCredentials

    credentials_handler = BillingSetupStoreCredentials(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_store_credentials",
        method="POST",
        json={
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "credentials": {
                "stripe_secret_key": "sk_test_workflow",  # pragma: allowlist secret
                "stripe_webhook_secret": "whsec_workflow",  # pragma: allowlist secret
            },
        },
    ) as ctx:
        stored = asyncio.run(credentials_handler.handle_request(ctx.request))
    assert stored.status_code == 200

    validate_handler = BillingSetupWorkflowValidate(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_validate",
        method="POST",
        json={
            "run_id": run_id,
            "apply_catalog_sync": True,
            "target_offer_slug": "pro",
            "mock": True,
        },
    ) as ctx:
        response = asyncio.run(validate_handler.handle_request(ctx.request))

    assert response.status_code == 200
    body = response.get_json()
    assert body["workflow"]["checkout_state"]["status"] == "awaiting_human_completion"
    assert body["workflow"]["validation_report"]["checkout"]["checkout_url"].startswith("https://")


def test_billing_setup_workflow_recovery_endpoints(monkeypatch, tmp_path):
    configure_test_db(monkeypatch, tmp_path)
    app = Flask(__name__)
    app.secret_key = "test-secret"  # pragma: allowlist secret
    start_handler = BillingSetupWorkflowStart(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_start",
        method="POST",
        json={
            "tenant_id": "test-tenant",
            "provider": "stripe",
            "business_name": "Test Tenant",
            "email": "billing@test-tenant.example",
            "country": "US",
        },
    ) as ctx:
        started = asyncio.run(start_handler.handle_request(ctx.request)).get_json()

    run_id = started["workflow"]["run_id"]
    status_handler = BillingSetupWorkflowStatus(app, threading.Lock())
    with app.test_request_context(
        f"/billing_setup_workflow_status?run_id={run_id}",
        method="GET",
    ) as ctx:
        status_response = asyncio.run(status_handler.handle_request(ctx.request))
    assert status_response.status_code == 200
    status_body = status_response.get_json()
    checkpoint_id = status_body["checkpoints"][0]["checkpoint_id"]

    recover_handler = BillingSetupWorkflowRecover(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_recover",
        method="POST",
        json={"run_id": run_id},
    ) as ctx:
        recover_response = asyncio.run(recover_handler.handle_request(ctx.request))
    assert recover_response.status_code == 200

    checkpoints_handler = BillingSetupWorkflowCheckpoints(app, threading.Lock())
    with app.test_request_context(
        f"/billing_setup_workflow_checkpoints?run_id={run_id}",
        method="GET",
    ) as ctx:
        checkpoints_response = asyncio.run(checkpoints_handler.handle_request(ctx.request))
    assert checkpoints_response.status_code == 200
    assert checkpoints_response.get_json()["checkpoints"]

    restart_handler = BillingSetupWorkflowRestart(app, threading.Lock())
    with app.test_request_context(
        "/billing_setup_workflow_restart",
        method="POST",
        json={"run_id": run_id, "checkpoint_id": checkpoint_id},
    ) as ctx:
        restart_response = asyncio.run(restart_handler.handle_request(ctx.request))
    assert restart_response.status_code == 200
