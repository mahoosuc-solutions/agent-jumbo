from instruments.custom.payment_account_setup.setup_manager import PaymentAccountSetupManager


def build_manager(tmp_path):
    return PaymentAccountSetupManager(str(tmp_path / "payment_setup.db"))


def test_get_catalog_bootstraps_template_offers(tmp_path):
    manager = build_manager(tmp_path)

    catalog = manager.get_catalog(tenant_id="tenant-alpha", provider="stripe")

    assert catalog["offer_count"] == 10  # 4 platform tiers + 1 free_cloud + 5 solution packages
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
    assert status["journey"]["current_stage"] == "operate"
    assert any(playbook["id"] == "catalog_change" for playbook in status["process_playbooks"])


def test_update_catalog_offer_marks_customized_and_inactive(tmp_path):
    manager = build_manager(tmp_path)

    updated = manager.update_catalog_offer(
        tenant_id="tenant-alpha",
        provider="stripe",
        slug="pro",
        active=False,
        monthly_price_usd=129.0,
        setup_price_usd=49.0,
    )

    assert updated["status"] == "updated"
    assert updated["offer"]["slug"] == "pro"
    assert updated["offer"]["active"] is False
    assert updated["offer"]["monthly_price_usd"] == 129.0
    assert updated["offer"]["setup_price_usd"] == 49.0
    assert updated["offer"]["source_kind"] == "customized"
    assert updated["offer"]["sync_status"] == "inactive"

    diff = manager.diff_catalog(tenant_id="tenant-alpha", provider="stripe", mock=True)
    pro_offer = next(offer for offer in diff["offers"] if offer["slug"] == "pro")
    assert pro_offer["recommended_action"] == "inactive"


def test_catalog_override_persists_and_diff_reflects_updated_price(tmp_path):
    """update_catalog_offer persists customized price; diff reflects it; re-sync returns a price ID."""
    manager = build_manager(tmp_path)
    manager.store_credentials(
        provider="stripe",
        tenant_id="tenant-alpha",
        credentials={
            "stripe_secret_key": "sk_test_mock_replace",  # pragma: allowlist secret
            "stripe_webhook_secret": "whsec_mock_replace",  # pragma: allowlist secret
        },
    )

    # Initial sync creates a price ID
    initial = manager.sync_catalog(
        tenant_id="tenant-alpha", provider="stripe", apply=True, selected_slugs=["pro"], mock=True
    )
    initial_offer = next(offer for offer in initial["offers"] if offer["slug"] == "pro")
    assert initial_offer["monthly_price_id"], "sync should create a mock price ID"

    # Override the price
    manager.update_catalog_offer(
        tenant_id="tenant-alpha",
        provider="stripe",
        slug="pro",
        monthly_price_usd=149.0,
    )

    # Diff should show the updated price
    diff = manager.diff_catalog(tenant_id="tenant-alpha", provider="stripe", mock=True)
    pro_diff = next(offer for offer in diff["offers"] if offer["slug"] == "pro")
    assert pro_diff["monthly_price_usd"] == 149.0

    # Re-sync should succeed and return a price ID
    updated = manager.sync_catalog(
        tenant_id="tenant-alpha", provider="stripe", apply=True, selected_slugs=["pro"], mock=True
    )
    updated_offer = next(offer for offer in updated["offers"] if offer["slug"] == "pro")
    assert updated_offer["monthly_price_id"], "re-sync should still return a mock price ID"
