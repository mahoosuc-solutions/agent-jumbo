import os

from instruments.custom.plugin_marketplace.marketplace_db import PluginMarketplaceDatabase


def test_plugin_marketplace_db_roundtrip(tmp_path):
    db_path = os.path.join(tmp_path, "marketplace.db")
    db = PluginMarketplaceDatabase(db_path)

    # Default marketplaces are seeded
    marketplaces = db.list_marketplaces()
    assert len(marketplaces) >= 3  # claude-plugins-dev, anthropic-official, local

    # Get default marketplace by name
    community = db.get_marketplace(name="claude-plugins-dev")
    assert community is not None
    assert community["type"] == "community"

    # Add custom marketplace
    mp_id = db.add_marketplace(
        name="my-registry",
        url="https://my-registry.example.com",
        api_endpoint="https://my-registry.example.com/api",
        marketplace_type="private",
        auto_update=True,
        metadata={"org": "acme"},
    )
    assert mp_id

    custom = db.get_marketplace(marketplace_id=mp_id)
    assert custom["name"] == "my-registry"
    assert custom["metadata"] == {"org": "acme"}

    # Toggle marketplace
    db.toggle_marketplace(mp_id, enabled=False)
    disabled = db.get_marketplace(marketplace_id=mp_id)
    assert disabled["enabled"] == 0

    db.toggle_marketplace(mp_id, enabled=True)

    # Cache a plugin
    plugin_id = db.cache_plugin(
        marketplace_id=mp_id,
        identifier="acme/data-loader",
        name="Data Loader",
        description="Loads data from various sources",
        version="1.2.0",
        downloads=500,
        stars=42,
        tags=["data", "etl"],
        author="acme-team",
        repository="https://github.com/acme/data-loader",
    )
    assert plugin_id

    # Get plugin by identifier
    plugin = db.get_plugin(identifier="acme/data-loader", marketplace_id=mp_id)
    assert plugin["name"] == "Data Loader"
    assert plugin["tags"] == ["data", "etl"]
    assert plugin["version"] == "1.2.0"

    # Search plugins
    results = db.search_plugins("Data", marketplace_id=mp_id)
    assert len(results) == 1
    assert results[0]["identifier"] == "acme/data-loader"

    # List plugins
    all_plugins = db.list_plugins(marketplace_id=mp_id)
    assert len(all_plugins) == 1

    # Record installation
    install_id = db.record_installation(
        plugin_identifier="acme/data-loader",
        marketplace_id=mp_id,
        version="1.2.0",
        local_path="/plugins/data-loader",
    )
    assert install_id

    installed = db.get_installed_plugin("acme/data-loader")
    assert installed["status"] == "installed"
    assert installed["version"] == "1.2.0"

    # Update installation status
    db.update_installation_status("acme/data-loader", "active", import_status="loaded")
    updated = db.get_installed_plugin("acme/data-loader")
    assert updated["status"] == "active"
    assert updated["import_status"] == "loaded"

    # List installed
    installed_list = db.list_installed()
    assert len(installed_list) == 1

    # Update marketplace sync
    db.update_marketplace_sync(mp_id, plugin_count=1)
    synced = db.get_marketplace(marketplace_id=mp_id)
    assert synced["plugin_count"] == 1
    assert synced["last_synced"] is not None

    # Stats
    stats = db.get_stats()
    assert stats["cached_plugins"] >= 1

    # Remove installation
    db.remove_installation("acme/data-loader")
    assert db.get_installed_plugin("acme/data-loader") is None

    # Clear cache
    db.clear_marketplace_cache(mp_id)
    assert len(db.list_plugins(marketplace_id=mp_id)) == 0

    # Remove marketplace
    db.remove_marketplace(mp_id)
    assert db.get_marketplace(marketplace_id=mp_id) is None
