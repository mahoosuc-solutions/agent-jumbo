import json

from instruments.custom.pms_hub.pms_provider import ProviderType
from instruments.custom.pms_hub.provider_registry import ProviderConfig, ProviderRegistry


def test_pms_hub_registry_roundtrip(tmp_path):
    config_path = tmp_path / "providers.json"
    registry = ProviderRegistry(config_path=config_path)

    # Initially empty
    assert registry.list_providers() == []

    # Register a provider (disabled to skip validation/auth)
    result = registry.register_provider(
        provider_id="hostaway-1",
        provider_type=ProviderType.HOSTAWAY,
        name="Hostaway Main",
        credentials={"api_key": "test-key-123", "account_id": "acc-456"},  # pragma: allowlist secret
        options={"sync_interval": 300},
        enabled=False,
    )
    assert result is True

    # List providers
    all_providers = registry.list_providers()
    assert "hostaway-1" in all_providers

    # List enabled only
    enabled = registry.list_providers(enabled_only=True)
    assert "hostaway-1" not in enabled

    # Get config
    config = registry.get_provider_config("hostaway-1")
    assert config is not None
    assert config.name == "Hostaway Main"
    assert config.provider_type == ProviderType.HOSTAWAY
    assert config.credentials["api_key"] == "test-key-123"  # pragma: allowlist secret
    assert config.options["sync_interval"] == 300
    assert config.enabled is False

    # Update config
    result = registry.update_provider_config(
        "hostaway-1",
        credentials={"api_key": "new-key-789"},  # pragma: allowlist secret
        enabled=True,
    )
    assert result is True

    updated = registry.get_provider_config("hostaway-1")
    assert updated.credentials["api_key"] == "new-key-789"  # pragma: allowlist secret
    assert updated.credentials["account_id"] == "acc-456"  # preserved
    assert updated.enabled is True

    # Now shows in enabled list
    enabled_after = registry.list_providers(enabled_only=True)
    assert "hostaway-1" in enabled_after

    # Register second provider
    registry.register_provider(
        provider_id="lodgify-1",
        provider_type=ProviderType.LODGIFY,
        name="Lodgify Account",
        credentials={"api_key": "lodgify-key"},  # pragma: allowlist secret
        enabled=False,
    )
    assert len(registry.list_providers()) == 2

    # Export config
    exported = registry.export_config()
    assert "providers" in exported
    assert "hostaway-1" in exported["providers"]
    assert "lodgify-1" in exported["providers"]

    # Config persisted to file
    assert config_path.exists()
    with open(config_path) as f:
        saved = json.load(f)
    assert "hostaway-1" in saved["providers"]

    # Unregister
    assert registry.unregister_provider("lodgify-1") is True
    assert len(registry.list_providers()) == 1
    assert registry.unregister_provider("nonexistent") is False

    # Import config
    import_data = {
        "providers": {
            "ical-1": {
                "provider_type": "ical",
                "name": "iCal Feed",
                "enabled": True,
                "credentials": {"url": "https://example.com/cal.ics"},
                "options": {},
            }
        }
    }
    assert registry.import_config(import_data) is True
    assert registry.list_providers() == ["ical-1"]

    # ProviderConfig round-trip
    pc = ProviderConfig(
        provider_type=ProviderType.HOSTAWAY,
        name="Test",
        credentials={"key": "val"},
    )
    d = pc.to_dict()
    restored = ProviderConfig.from_dict(d)
    assert restored.provider_type == ProviderType.HOSTAWAY
    assert restored.name == "Test"
    assert restored.credentials == {"key": "val"}
