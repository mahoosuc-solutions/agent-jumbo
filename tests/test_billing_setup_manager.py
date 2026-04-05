from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager


def build_manager(tmp_path):
    return PaymentAccountSetupManager(str(tmp_path / "payment_setup.db"))


def test_get_catalog_bootstraps_template_offers(tmp_path):
    manager = build_manager(tmp_path)

    catalog = manager.get_catalog(tenant_id="tenant-alpha", provider="stripe")

    assert catalog["offer_count"] == 9
    assert any(offer["slug"] == "pro" for offer in catalog["offers"])
    assert any(offer["slug"] == "ai-customer-support" for offer in catalog["offers"])


def test_start_setup_tracks_tenant_session_and_first_step(tmp_path):
    manager = build_manager(tmp_path)

    result = manager.start_setup(
        provider="stripe",
        business_name="Tenant Alpha",
        email="billing@tenant.test",
        tenant_id="tenant-alpha",
    )

    assert result["session"]["tenant_id"] == "tenant-alpha"
    assert result["next_step"]["title"] == "Navigate to Stripe registration"
    sessions = manager.list_sessions(tenant_id="tenant-alpha", provider="stripe")
    assert len(sessions) == 1


def test_verify_setup_reports_ready_after_mock_sync(tmp_path):
    manager = build_manager(tmp_path)

    manager.store_credentials(
        provider="stripe",
        tenant_id="tenant-alpha",
        credentials={
            "stripe_secret_key": "sk_test_mock_ready",  # pragma: allowlist secret
            "stripe_webhook_secret": "whsec_mock_ready",  # pragma: allowlist secret
        },
    )

    sync = manager.sync_catalog(tenant_id="tenant-alpha", provider="stripe", apply=True, mock=True)
    assert sync["status"] == "synced"

    verification = manager.verify_setup(provider="stripe", tenant_id="tenant-alpha", mock=True)

    assert verification["summary"]["ready"] is True
    assert verification["summary"]["failed"] == 0

    status = manager.get_status(tenant_id="tenant-alpha", provider="stripe", mock=True)
    assert status["connection"]["readiness_status"] == "ready"
    assert status["credentials"]["stripe_secret_key"].startswith("sk_test_")
    assert status["summary"]["ready"] is True
