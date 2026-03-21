"""
Notion Integration Database — local SQLite cache for Notion pages and mappings.
"""

import json
from typing import Any

from python.helpers.db_connection import DatabaseConnection, SyncLogMixin


class NotionDatabase(SyncLogMixin):
    """Local cache for Notion pages and Linear/CRM<>Notion mappings."""

    def __init__(self, db_path: str = "data/notion_integration.db"):
        self.db = DatabaseConnection(db_path)
        self.init_database()

    def init_database(self) -> None:
        conn = self.db.conn

        conn.execute("""
            CREATE TABLE IF NOT EXISTS pages_cache (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                database_id TEXT,
                url TEXT,
                properties TEXT,
                created_time TEXT,
                last_edited_time TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS notion_linear_map (
                notion_page_id TEXT PRIMARY KEY,
                linear_issue_id TEXT NOT NULL,
                linear_identifier TEXT,
                sync_type TEXT DEFAULT 'spec',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(linear_issue_id, sync_type)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS notion_crm_map (
                notion_page_id TEXT PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                customer_name TEXT,
                sync_type TEXT DEFAULT 'contact',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(customer_id, sync_type)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'running',
                items_synced INTEGER DEFAULT 0,
                error TEXT
            )
        """)

        # Indexes for commonly-queried columns
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_database_id ON pages_cache(database_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pages_last_edited ON pages_cache(last_edited_time)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notion_linear_map_linear_id ON notion_linear_map(linear_issue_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notion_crm_map_customer_id ON notion_crm_map(customer_id)")

        conn.commit()

    # ── Page cache ───────────────────────────────────────────────────

    def upsert_page(self, page: dict[str, Any]) -> None:
        # Extract title from Notion page properties
        title = ""
        props = page.get("properties", {})
        name_prop = props.get("Name", props.get("name", props.get("title", {})))
        if isinstance(name_prop, dict):
            title_arr = name_prop.get("title", [])
            if title_arr and isinstance(title_arr, list):
                title = title_arr[0].get("text", {}).get("content", "") if title_arr else ""

        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pages_cache
                    (id, title, database_id, url, properties, created_time, last_edited_time, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    page.get("id", ""),
                    title or page.get("_title", ""),
                    page.get("parent", {}).get("database_id", ""),
                    page.get("url", ""),
                    json.dumps(props),
                    page.get("created_time", ""),
                    page.get("last_edited_time", ""),
                ),
            )

    def get_pages(self, database_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        query = "SELECT * FROM pages_cache WHERE 1=1"
        params: list[Any] = []
        if database_id:
            query += " AND database_id = ?"
            params.append(database_id)
        query += " ORDER BY last_edited_time DESC LIMIT ?"
        params.append(limit)

        return self.db.query_rows(query, params)

    # ── Mappings ─────────────────────────────────────────────────────

    def get_notion_id_for_linear(self, linear_issue_id: str, sync_type: str = "spec") -> str | None:
        row = self.db.query_one(
            "SELECT notion_page_id FROM notion_linear_map WHERE linear_issue_id = ? AND sync_type = ?",
            (linear_issue_id, sync_type),
        )
        return row["notion_page_id"] if row else None

    def add_linear_mapping(
        self, notion_page_id: str, linear_issue_id: str, linear_identifier: str = "", sync_type: str = "spec"
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO notion_linear_map
                    (notion_page_id, linear_issue_id, linear_identifier, sync_type)
                VALUES (?, ?, ?, ?)
                """,
                (notion_page_id, linear_issue_id, linear_identifier, sync_type),
            )

    def get_notion_id_for_customer(self, customer_id: int, sync_type: str = "contact") -> str | None:
        row = self.db.query_one(
            "SELECT notion_page_id FROM notion_crm_map WHERE customer_id = ? AND sync_type = ?",
            (customer_id, sync_type),
        )
        return row["notion_page_id"] if row else None

    def add_crm_mapping(
        self, notion_page_id: str, customer_id: int, customer_name: str = "", sync_type: str = "contact"
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO notion_crm_map
                    (notion_page_id, customer_id, customer_name, sync_type)
                VALUES (?, ?, ?, ?)
                """,
                (notion_page_id, customer_id, customer_name, sync_type),
            )
