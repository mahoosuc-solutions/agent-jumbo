"""
Database module for Plugin Marketplace tool
Caches marketplace data and tracks installations
"""

import json
import sqlite3
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now


class PluginMarketplaceDatabase:
    """SQLite database for marketplace caching and installation tracking"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        """Initialize database schema with default marketplaces"""
        with self._connect() as conn:
            conn.executescript("""
                -- Marketplace sources
                CREATE TABLE IF NOT EXISTS marketplaces (
                    marketplace_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    url TEXT NOT NULL,
                    api_endpoint TEXT,
                    type TEXT DEFAULT 'community',
                    auto_update BOOLEAN DEFAULT FALSE,
                    enabled BOOLEAN DEFAULT TRUE,
                    last_synced TEXT,
                    plugin_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Cached plugin listings
                CREATE TABLE IF NOT EXISTS marketplace_plugins (
                    plugin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    marketplace_id INTEGER NOT NULL,
                    identifier TEXT NOT NULL,
                    name TEXT,
                    description TEXT,
                    version TEXT,
                    downloads INTEGER DEFAULT 0,
                    stars INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    author TEXT,
                    repository TEXT,
                    homepage TEXT,
                    license TEXT,
                    last_updated TEXT,
                    cached_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (marketplace_id) REFERENCES marketplaces(marketplace_id),
                    UNIQUE(marketplace_id, identifier)
                );

                -- Installation history
                CREATE TABLE IF NOT EXISTS installed_plugins (
                    install_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plugin_identifier TEXT NOT NULL UNIQUE,
                    marketplace_id INTEGER,
                    version TEXT,
                    installed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT,
                    status TEXT DEFAULT 'installed',
                    local_path TEXT,
                    import_status TEXT DEFAULT 'pending',
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (marketplace_id) REFERENCES marketplaces(marketplace_id)
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_plugins_marketplace ON marketplace_plugins(marketplace_id);
                CREATE INDEX IF NOT EXISTS idx_plugins_identifier ON marketplace_plugins(identifier);
                CREATE INDEX IF NOT EXISTS idx_plugins_tags ON marketplace_plugins(tags);
                CREATE INDEX IF NOT EXISTS idx_installed_status ON installed_plugins(status);
            """)

            # Seed default marketplaces
            self._seed_default_marketplaces(conn)

    def _seed_default_marketplaces(self, conn):
        """Seed default marketplace sources"""
        defaults = [
            {
                "name": "claude-plugins-dev",
                "url": "https://claude-plugins.dev",
                "api_endpoint": "https://claude-plugins.dev/api/registry",
                "type": "community",
                "metadata": {"description": "Community-maintained plugin registry"},
            },
            {
                "name": "anthropic-official",
                "url": "https://github.com/anthropics",
                "api_endpoint": None,
                "type": "official",
                "metadata": {"description": "Official Anthropic plugins"},
            },
            {
                "name": "local",
                "url": "~/.claude/plugins",
                "api_endpoint": None,
                "type": "local",
                "metadata": {"description": "Locally installed plugins"},
            },
        ]

        for mp in defaults:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO marketplaces (name, url, api_endpoint, type, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (mp["name"], mp["url"], mp["api_endpoint"], mp["type"], json.dumps(mp["metadata"])),
                )
            except sqlite3.IntegrityError:
                pass

    # ========== Marketplace Operations ==========

    def add_marketplace(
        self,
        name: str,
        url: str,
        api_endpoint: str | None = None,
        marketplace_type: str = "community",
        auto_update: bool = False,
        metadata: dict | None = None,
    ) -> int:
        """Add a new marketplace source"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO marketplaces (name, url, api_endpoint, type, auto_update, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (name, url, api_endpoint, marketplace_type, auto_update, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_marketplace(self, marketplace_id: int | None = None, name: str | None = None) -> dict:
        """Get marketplace by ID or name"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if marketplace_id:
                row = conn.execute("SELECT * FROM marketplaces WHERE marketplace_id = ?", (marketplace_id,)).fetchone()
            elif name:
                row = conn.execute("SELECT * FROM marketplaces WHERE name = ?", (name,)).fetchone()
            else:
                return None

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def list_marketplaces(self, enabled_only: bool = False) -> list:
        """List all marketplaces"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM marketplaces"
            if enabled_only:
                query += " WHERE enabled = 1"
            query += " ORDER BY type, name"

            rows = conn.execute(query).fetchall()
            results = []
            for row in rows:
                r = dict(row)
                r["metadata"] = json.loads(r.get("metadata", "{}"))
                results.append(r)
            return results

    def update_marketplace_sync(self, marketplace_id: int, plugin_count: int):
        """Update marketplace sync timestamp and plugin count"""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE marketplaces SET last_synced = ?, plugin_count = ?
                WHERE marketplace_id = ?
            """,
                (isoformat_z(utc_now()), plugin_count, marketplace_id),
            )

    def toggle_marketplace(self, marketplace_id: int, enabled: bool):
        """Enable/disable a marketplace"""
        with self._connect() as conn:
            conn.execute("UPDATE marketplaces SET enabled = ? WHERE marketplace_id = ?", (enabled, marketplace_id))

    def remove_marketplace(self, marketplace_id: int):
        """Remove a marketplace and its cached plugins"""
        with self._connect() as conn:
            conn.execute("DELETE FROM marketplace_plugins WHERE marketplace_id = ?", (marketplace_id,))
            conn.execute("DELETE FROM marketplaces WHERE marketplace_id = ?", (marketplace_id,))

    # ========== Plugin Cache Operations ==========

    def cache_plugin(
        self,
        marketplace_id: int,
        identifier: str,
        name: str,
        description: str | None = None,
        version: str | None = None,
        downloads: int = 0,
        stars: int = 0,
        tags: list | None = None,
        author: str | None = None,
        repository: str | None = None,
        homepage: str | None = None,
        license: str | None = None,
        last_updated: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Cache a plugin from marketplace"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO marketplace_plugins
                (marketplace_id, identifier, name, description, version, downloads, stars,
                 tags, author, repository, homepage, license, last_updated, cached_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    marketplace_id,
                    identifier,
                    name,
                    description,
                    version,
                    downloads,
                    stars,
                    json.dumps(tags or []),
                    author,
                    repository,
                    homepage,
                    license,
                    last_updated,
                    isoformat_z(utc_now()),
                    json.dumps(metadata or {}),
                ),
            )
            return cursor.lastrowid

    def get_plugin(
        self, plugin_id: int | None = None, identifier: str | None = None, marketplace_id: int | None = None
    ) -> dict:
        """Get cached plugin by ID or identifier"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if plugin_id:
                row = conn.execute("SELECT * FROM marketplace_plugins WHERE plugin_id = ?", (plugin_id,)).fetchone()
            elif identifier:
                if marketplace_id:
                    row = conn.execute(
                        """
                        SELECT * FROM marketplace_plugins
                        WHERE identifier = ? AND marketplace_id = ?
                    """,
                        (identifier, marketplace_id),
                    ).fetchone()
                else:
                    row = conn.execute(
                        "SELECT * FROM marketplace_plugins WHERE identifier = ?", (identifier,)
                    ).fetchone()
            else:
                return None

            if row:
                result = dict(row)
                result["tags"] = json.loads(result.get("tags", "[]"))
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def search_plugins(
        self, query: str, marketplace_id: int | None = None, tags: list | None = None, limit: int = 50
    ) -> list:
        """Search plugins by name/description"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            sql = """
                SELECT p.*, m.name as marketplace_name
                FROM marketplace_plugins p
                JOIN marketplaces m ON p.marketplace_id = m.marketplace_id
                WHERE m.enabled = 1
                AND (p.name LIKE ? OR p.description LIKE ? OR p.identifier LIKE ?)
            """
            params = [f"%{query}%", f"%{query}%", f"%{query}%"]

            if marketplace_id:
                sql += " AND p.marketplace_id = ?"
                params.append(marketplace_id)

            if tags:
                for tag in tags:
                    sql += " AND p.tags LIKE ?"
                    params.append(f'%"{tag}"%')

            sql += " ORDER BY p.downloads DESC, p.stars DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            results = []
            for row in rows:
                r = dict(row)
                r["tags"] = json.loads(r.get("tags", "[]"))
                r["metadata"] = json.loads(r.get("metadata", "{}"))
                results.append(r)
            return results

    def list_plugins(
        self, marketplace_id: int | None = None, sort_by: str = "downloads", limit: int = 50, offset: int = 0
    ) -> list:
        """List plugins with sorting and pagination"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row

            sort_columns = {
                "downloads": "downloads DESC",
                "stars": "stars DESC",
                "recent": "last_updated DESC",
                "name": "name ASC",
            }
            order = sort_columns.get(sort_by, "downloads DESC")

            if marketplace_id:
                sql = f"""
                    SELECT p.*, m.name as marketplace_name
                    FROM marketplace_plugins p
                    JOIN marketplaces m ON p.marketplace_id = m.marketplace_id
                    WHERE p.marketplace_id = ?
                    ORDER BY {order}
                    LIMIT ? OFFSET ?
                """
                params = [marketplace_id, limit, offset]
            else:
                sql = f"""
                    SELECT p.*, m.name as marketplace_name
                    FROM marketplace_plugins p
                    JOIN marketplaces m ON p.marketplace_id = m.marketplace_id
                    WHERE m.enabled = 1
                    ORDER BY {order}
                    LIMIT ? OFFSET ?
                """
                params = [limit, offset]

            rows = conn.execute(sql, params).fetchall()
            results = []
            for row in rows:
                r = dict(row)
                r["tags"] = json.loads(r.get("tags", "[]"))
                results.append(r)
            return results

    def get_plugins_by_tag(self, tag: str, limit: int = 50) -> list:
        """Get plugins by tag"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT p.*, m.name as marketplace_name
                FROM marketplace_plugins p
                JOIN marketplaces m ON p.marketplace_id = m.marketplace_id
                WHERE m.enabled = 1 AND p.tags LIKE ?
                ORDER BY p.downloads DESC
                LIMIT ?
            """,
                (f'%"{tag}"%', limit),
            ).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["tags"] = json.loads(r.get("tags", "[]"))
                results.append(r)
            return results

    def clear_marketplace_cache(self, marketplace_id: int):
        """Clear cached plugins for a marketplace"""
        with self._connect() as conn:
            conn.execute("DELETE FROM marketplace_plugins WHERE marketplace_id = ?", (marketplace_id,))

    # ========== Installation Tracking ==========

    def record_installation(
        self,
        plugin_identifier: str,
        marketplace_id: int | None = None,
        version: str | None = None,
        local_path: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Record a plugin installation"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO installed_plugins
                (plugin_identifier, marketplace_id, version, local_path, status, metadata)
                VALUES (?, ?, ?, ?, 'installed', ?)
            """,
                (plugin_identifier, marketplace_id, version, local_path, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def update_installation_status(self, plugin_identifier: str, status: str, import_status: str | None = None):
        """Update installation status"""
        with self._connect() as conn:
            if import_status:
                conn.execute(
                    """
                    UPDATE installed_plugins SET status = ?, import_status = ?, updated_at = ?
                    WHERE plugin_identifier = ?
                """,
                    (status, import_status, isoformat_z(utc_now()), plugin_identifier),
                )
            else:
                conn.execute(
                    """
                    UPDATE installed_plugins SET status = ?, updated_at = ?
                    WHERE plugin_identifier = ?
                """,
                    (status, isoformat_z(utc_now()), plugin_identifier),
                )

    def get_installed_plugin(self, plugin_identifier: str) -> dict:
        """Get installed plugin record"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM installed_plugins WHERE plugin_identifier = ?", (plugin_identifier,)
            ).fetchone()

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def list_installed(self, status: str | None = None) -> list:
        """List installed plugins"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if status:
                rows = conn.execute(
                    "SELECT * FROM installed_plugins WHERE status = ? ORDER BY installed_at DESC", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM installed_plugins ORDER BY installed_at DESC").fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["metadata"] = json.loads(r.get("metadata", "{}"))
                results.append(r)
            return results

    def remove_installation(self, plugin_identifier: str):
        """Remove installation record"""
        with self._connect() as conn:
            conn.execute("DELETE FROM installed_plugins WHERE plugin_identifier = ?", (plugin_identifier,))

    # ========== Statistics ==========

    def get_stats(self) -> dict:
        """Get marketplace statistics"""
        with self._connect() as conn:
            marketplaces = conn.execute("SELECT COUNT(*) FROM marketplaces WHERE enabled = 1").fetchone()[0]

            cached_plugins = conn.execute("SELECT COUNT(*) FROM marketplace_plugins").fetchone()[0]

            installed = conn.execute("SELECT COUNT(*) FROM installed_plugins WHERE status = 'installed'").fetchone()[0]

            # Top tags
            all_tags = conn.execute("SELECT tags FROM marketplace_plugins").fetchall()

            tag_counts = {}
            for row in all_tags:
                tags = json.loads(row[0])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            return {
                "marketplaces_enabled": marketplaces,
                "cached_plugins": cached_plugins,
                "installed_plugins": installed,
                "top_tags": dict(top_tags),
            }
