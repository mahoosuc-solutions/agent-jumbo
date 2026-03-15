"""
Plugin Marketplace Manager - Business logic for plugin discovery and installation
Coordinates registry clients, caching, and installation workflows
"""

import os
import subprocess
from pathlib import Path

from .marketplace_db import PluginMarketplaceDatabase
from .registry_client import BaseRegistryClient, RegistryClientFactory


class PluginMarketplaceManager:
    """Manager for plugin marketplace operations"""

    def __init__(self, db_path: str):
        self.db = PluginMarketplaceDatabase(db_path)
        self._clients: dict[int, BaseRegistryClient] = {}

    def _get_client(self, marketplace_id: int) -> BaseRegistryClient:
        """Get or create registry client for marketplace"""
        if marketplace_id not in self._clients:
            marketplace = self.db.get_marketplace(marketplace_id=marketplace_id)
            if marketplace:
                self._clients[marketplace_id] = RegistryClientFactory.create(
                    marketplace["type"], base_path=marketplace.get("url") if marketplace["type"] == "local" else None
                )
        return self._clients.get(marketplace_id)

    # ========== Marketplace Management ==========

    def add_marketplace(
        self,
        name: str,
        url: str,
        api_endpoint: str | None = None,
        marketplace_type: str = "community",
        auto_update: bool = False,
    ) -> dict:
        """Add a new marketplace source"""
        marketplace_id = self.db.add_marketplace(
            name=name, url=url, api_endpoint=api_endpoint, marketplace_type=marketplace_type, auto_update=auto_update
        )

        return {"marketplace_id": marketplace_id, "name": name, "url": url, "type": marketplace_type, "status": "added"}

    def list_marketplaces(self, enabled_only: bool = False) -> list:
        """List configured marketplaces"""
        return self.db.list_marketplaces(enabled_only)

    def get_marketplace(self, marketplace_id: int | None = None, name: str | None = None) -> dict:
        """Get marketplace details"""
        return self.db.get_marketplace(marketplace_id, name)

    def remove_marketplace(self, marketplace_id: int) -> dict:
        """Remove a marketplace"""
        marketplace = self.db.get_marketplace(marketplace_id=marketplace_id)
        if not marketplace:
            return {"error": "Marketplace not found"}

        self.db.remove_marketplace(marketplace_id)
        return {"status": "removed", "name": marketplace["name"]}

    def toggle_marketplace(self, marketplace_id: int, enabled: bool) -> dict:
        """Enable/disable a marketplace"""
        self.db.toggle_marketplace(marketplace_id, enabled)
        return {"marketplace_id": marketplace_id, "enabled": enabled}

    # ========== Sync Operations ==========

    async def sync_marketplace(self, marketplace_id: int) -> dict:
        """Sync plugins from a marketplace"""
        marketplace = self.db.get_marketplace(marketplace_id=marketplace_id)
        if not marketplace:
            return {"error": "Marketplace not found"}

        client = self._get_client(marketplace_id)
        if not client:
            return {"error": f"No client available for marketplace type: {marketplace['type']}"}

        try:
            # Fetch plugins
            plugins = await client.fetch_plugins(limit=500)

            if plugins and "error" in plugins[0]:
                return {"error": plugins[0]["error"]}

            # Clear old cache and store new
            self.db.clear_marketplace_cache(marketplace_id)

            count = 0
            for plugin in plugins:
                if "error" not in plugin:
                    self.db.cache_plugin(
                        marketplace_id=marketplace_id,
                        identifier=plugin.get("identifier", ""),
                        name=plugin.get("name", ""),
                        description=plugin.get("description"),
                        version=plugin.get("version"),
                        downloads=plugin.get("downloads", 0),
                        stars=plugin.get("stars", 0),
                        tags=plugin.get("tags", []),
                        author=plugin.get("author"),
                        repository=plugin.get("repository"),
                        homepage=plugin.get("homepage"),
                        license=plugin.get("license"),
                        last_updated=plugin.get("last_updated"),
                        metadata=plugin.get("metadata"),
                    )
                    count += 1

            # Update sync timestamp
            self.db.update_marketplace_sync(marketplace_id, count)

            return {"marketplace": marketplace["name"], "plugins_synced": count, "status": "synced"}

        except Exception as e:
            return {"error": str(e)}

    async def sync_all(self) -> dict:
        """Sync all enabled marketplaces"""
        marketplaces = self.db.list_marketplaces(enabled_only=True)
        results = []

        for mp in marketplaces:
            result = await self.sync_marketplace(mp["marketplace_id"])
            results.append({"marketplace": mp["name"], **result})

        total_synced = sum(r.get("plugins_synced", 0) for r in results)
        return {"marketplaces_synced": len(results), "total_plugins": total_synced, "results": results}

    # ========== Plugin Discovery ==========

    def search_plugins(
        self, query: str, marketplace_id: int | None = None, tags: list | None = None, limit: int = 50
    ) -> list:
        """Search plugins by name/description"""
        return self.db.search_plugins(query, marketplace_id, tags, limit)

    def list_plugins(
        self, marketplace_id: int | None = None, sort_by: str = "downloads", limit: int = 50, offset: int = 0
    ) -> list:
        """List plugins with sorting"""
        return self.db.list_plugins(marketplace_id, sort_by, limit, offset)

    def list_popular(self, limit: int = 20) -> list:
        """List most downloaded plugins"""
        return self.db.list_plugins(sort_by="downloads", limit=limit)

    def list_trending(self, limit: int = 20) -> list:
        """List recently updated plugins"""
        return self.db.list_plugins(sort_by="recent", limit=limit)

    def browse_by_tag(self, tag: str, limit: int = 50) -> list:
        """Browse plugins by tag"""
        return self.db.get_plugins_by_tag(tag, limit)

    def get_plugin_details(self, identifier: str, marketplace_id: int | None = None) -> dict:
        """Get detailed plugin information"""
        plugin = self.db.get_plugin(identifier=identifier, marketplace_id=marketplace_id)
        if not plugin:
            return {"error": f"Plugin not found: {identifier}"}
        return plugin

    # ========== Installation ==========

    def install_plugin(
        self, identifier: str, marketplace_id: int | None = None, use_cli: bool = True, target_path: str | None = None
    ) -> dict:
        """
        Install a plugin from marketplace.

        This method supports two installation strategies:
        1. use_cli=True: Use Claude Code CLI (npx claude-plugins install)
        2. use_cli=False: Direct git clone to target_path

        The installation decision affects security and compatibility:
        - CLI installation ensures proper validation and hooks
        - Direct installation gives more control but bypasses checks
        """
        # Get plugin info from cache
        plugin = self.db.get_plugin(identifier=identifier, marketplace_id=marketplace_id)

        if not plugin:
            return {"error": f"Plugin not found in cache: {identifier}. Try syncing first."}

        # Check if already installed
        existing = self.db.get_installed_plugin(identifier)
        if existing and existing["status"] == "installed":
            return {"status": "already_installed", "identifier": identifier, "version": existing.get("version")}

        try:
            if use_cli:
                result = self._install_via_cli(identifier, plugin)
            else:
                result = self._install_direct(identifier, plugin, target_path)

            if "error" not in result:
                # Record installation
                self.db.record_installation(
                    plugin_identifier=identifier,
                    marketplace_id=plugin.get("marketplace_id"),
                    version=plugin.get("version"),
                    local_path=result.get("local_path"),
                    metadata={"install_method": "cli" if use_cli else "direct"},
                )

            return result

        except Exception as e:
            return {"error": str(e)}

    def _install_via_cli(self, identifier: str, plugin: dict) -> dict:
        """Install using Claude Code CLI"""
        try:
            # Try npx claude-plugins first (community CLI)
            result = subprocess.run(
                ["npx", "claude-plugins", "install", identifier], capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                return {
                    "status": "installed",
                    "identifier": identifier,
                    "method": "claude-plugins-cli",
                    "output": result.stdout,
                }

            # Fallback: try claude CLI if available
            result = subprocess.run(
                ["claude", "plugin", "install", identifier], capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                return {
                    "status": "installed",
                    "identifier": identifier,
                    "method": "claude-cli",
                    "output": result.stdout,
                }

            return {"error": f"CLI installation failed: {result.stderr}"}

        except subprocess.TimeoutExpired:
            return {"error": "Installation timed out"}
        except FileNotFoundError:
            return {"error": "Claude Code CLI not found. Install with: npm install -g claude-plugins"}

    def _install_direct(self, identifier: str, plugin: dict, target_path: str | None = None) -> dict:
        """Install directly via git clone"""
        repository = plugin.get("repository")
        if not repository:
            return {"error": "No repository URL available for direct installation"}

        target_path = target_path or os.path.expanduser(f"~/.claude/plugins/{identifier.split('/')[-1]}")
        target = Path(target_path)

        if target.exists():
            return {"error": f"Target path already exists: {target_path}"}

        try:
            result = subprocess.run(
                ["git", "clone", repository, str(target)], capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                return {
                    "status": "installed",
                    "identifier": identifier,
                    "method": "git-clone",
                    "local_path": str(target),
                }

            return {"error": f"Git clone failed: {result.stderr}"}

        except subprocess.TimeoutExpired:
            return {"error": "Git clone timed out"}
        except FileNotFoundError:
            return {"error": "Git not found"}

    def uninstall_plugin(self, identifier: str) -> dict:
        """Uninstall a plugin"""
        installed = self.db.get_installed_plugin(identifier)
        if not installed:
            return {"error": f"Plugin not installed: {identifier}"}

        try:
            # Try CLI uninstall first
            subprocess.run(
                ["npx", "claude-plugins", "uninstall", identifier], capture_output=True, text=True, timeout=60
            )

            # Update status regardless of CLI result
            self.db.update_installation_status(identifier, "uninstalled")

            return {"status": "uninstalled", "identifier": identifier}

        except Exception as e:
            # Mark as uninstalled anyway
            self.db.update_installation_status(identifier, "uninstalled")
            return {"status": "uninstalled", "identifier": identifier, "warning": str(e)}

    def list_installed(self) -> list:
        """List installed plugins"""
        return self.db.list_installed(status="installed")

    def check_updates(self) -> list:
        """Check for available updates"""
        installed = self.db.list_installed(status="installed")
        updates = []

        for plugin in installed:
            cached = self.db.get_plugin(identifier=plugin["plugin_identifier"])
            if cached:
                installed_version = plugin.get("version", "0.0.0")
                latest_version = cached.get("version", "0.0.0")

                # Simple version comparison (would need proper semver for production)
                if latest_version != installed_version:
                    updates.append(
                        {
                            "identifier": plugin["plugin_identifier"],
                            "installed_version": installed_version,
                            "latest_version": latest_version,
                        }
                    )

        return updates

    def update_plugin(self, identifier: str) -> dict:
        """Update a plugin to latest version"""
        # Uninstall and reinstall
        self.uninstall_plugin(identifier)
        return self.install_plugin(identifier)

    # ========== Integration with skill_importer ==========

    def import_installed_plugin(self, identifier: str, skill_importer_manager) -> dict:
        """Import an installed plugin into Agent Zero via skill_importer"""
        installed = self.db.get_installed_plugin(identifier)
        if not installed:
            return {"error": f"Plugin not installed: {identifier}"}

        local_path = installed.get("local_path")
        if not local_path:
            # Try default location
            local_path = os.path.expanduser(f"~/.claude/plugins/{identifier.split('/')[-1]}")

        if not Path(local_path).exists():
            return {"error": f"Plugin path not found: {local_path}"}

        try:
            # Use skill_importer to import the plugin
            result = skill_importer_manager.import_plugin(local_path)

            # Update import status
            self.db.update_installation_status(
                identifier, status="installed", import_status="imported" if "error" not in result else "failed"
            )

            return result

        except Exception as e:
            return {"error": str(e)}

    # ========== Statistics ==========

    def get_stats(self) -> dict:
        """Get marketplace statistics"""
        return self.db.get_stats()

    # ========== Cleanup ==========

    async def close(self):
        """Close all registry clients"""
        for client in self._clients.values():
            if hasattr(client, "close"):
                await client.close()
        self._clients.clear()
