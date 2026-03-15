"""
Notion Integration Database — local SQLite cache for Notion pages and mappings.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any


class NotionDatabase:
    """Local cache for Notion pages and Linear/CRM↔Notion mappings."""

    def __init__(self, db_path: str = "data/notion_integration.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def init_database(self) -> None:
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notion_linear_map (
                notion_page_id TEXT PRIMARY KEY,
                linear_issue_id TEXT NOT NULL,
                linear_identifier TEXT,
                sync_type TEXT DEFAULT 'spec',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(linear_issue_id, sync_type)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notion_crm_map (
                notion_page_id TEXT PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                customer_name TEXT,
                sync_type TEXT DEFAULT 'contact',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(customer_id, sync_type)
            )
        """)

        cursor.execute("""
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

        conn.commit()
        conn.close()

    # ── Page cache ───────────────────────────────────────────────────

    def upsert_page(self, page: dict[str, Any]) -> None:
        conn = self.get_connection()
        # Extract title from Notion page properties
        title = ""
        props = page.get("properties", {})
        name_prop = props.get("Name", props.get("name", props.get("title", {})))
        if isinstance(name_prop, dict):
            title_arr = name_prop.get("title", [])
            if title_arr and isinstance(title_arr, list):
                title = title_arr[0].get("text", {}).get("content", "") if title_arr else ""

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
        conn.commit()
        conn.close()

    def get_pages(self, database_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        conn = self.get_connection()
        query = "SELECT * FROM pages_cache WHERE 1=1"
        params: list[Any] = []
        if database_id:
            query += " AND database_id = ?"
            params.append(database_id)
        query += " ORDER BY last_edited_time DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return rows

    # ── Mappings ─────────────────────────────────────────────────────

    def get_notion_id_for_linear(self, linear_issue_id: str, sync_type: str = "spec") -> str | None:
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT notion_page_id FROM notion_linear_map WHERE linear_issue_id = ? AND sync_type = ?",
            (linear_issue_id, sync_type),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def add_linear_mapping(
        self, notion_page_id: str, linear_issue_id: str, linear_identifier: str = "", sync_type: str = "spec"
    ) -> None:
        conn = self.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO notion_linear_map
                (notion_page_id, linear_issue_id, linear_identifier, sync_type)
            VALUES (?, ?, ?, ?)
            """,
            (notion_page_id, linear_issue_id, linear_identifier, sync_type),
        )
        conn.commit()
        conn.close()

    def get_notion_id_for_customer(self, customer_id: int, sync_type: str = "contact") -> str | None:
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT notion_page_id FROM notion_crm_map WHERE customer_id = ? AND sync_type = ?",
            (customer_id, sync_type),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def add_crm_mapping(
        self, notion_page_id: str, customer_id: int, customer_name: str = "", sync_type: str = "contact"
    ) -> None:
        conn = self.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO notion_crm_map
                (notion_page_id, customer_id, customer_name, sync_type)
            VALUES (?, ?, ?, ?)
            """,
            (notion_page_id, customer_id, customer_name, sync_type),
        )
        conn.commit()
        conn.close()

    # ── Sync log ─────────────────────────────────────────────────────

    def start_sync(self, sync_type: str) -> int:
        conn = self.get_connection()
        cursor = conn.execute("INSERT INTO sync_log (sync_type) VALUES (?)", (sync_type,))
        sync_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return sync_id  # type: ignore[return-value]

    def complete_sync(self, sync_id: int, items_synced: int, error: str | None = None) -> None:
        conn = self.get_connection()
        status = "error" if error else "completed"
        conn.execute(
            """
            UPDATE sync_log
            SET completed_at = CURRENT_TIMESTAMP, status = ?, items_synced = ?, error = ?
            WHERE id = ?
            """,
            (status, items_synced, error, sync_id),
        )
        conn.commit()
        conn.close()

    def get_last_sync(self, sync_type: str | None = None) -> dict[str, Any] | None:
        conn = self.get_connection()
        if sync_type:
            cursor = conn.execute(
                "SELECT * FROM sync_log WHERE sync_type = ? ORDER BY id DESC LIMIT 1",
                (sync_type,),
            )
        else:
            cursor = conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        cols = [d[0] for d in cursor.description]
        result = dict(zip(cols, row))
        conn.close()
        return result
