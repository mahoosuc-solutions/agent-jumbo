"""SQLite persistence for payment account setup sessions, connections, and catalogs."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any


class SetupDatabase:
    """SQLite backend for payment account setup sessions and tenant billing state."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _decode_json(value: str | None, fallback: Any) -> Any:
        if not value:
            return fallback
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return fallback

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS setup_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    tenant_id TEXT DEFAULT 'default',
                    provider TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    current_step INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    extracted_credentials TEXT DEFAULT '{}',
                    screenshot_paths TEXT DEFAULT '[]',
                    business_name TEXT,
                    email TEXT,
                    country TEXT DEFAULT 'us',
                    phase TEXT DEFAULT 'guided_setup',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS setup_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    step_id TEXT UNIQUE NOT NULL,
                    session_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    automation_type TEXT NOT NULL,
                    human_instructions TEXT,
                    action TEXT DEFAULT '{}',
                    completion_check TEXT,
                    extract_fields TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'pending',
                    result_data TEXT DEFAULT '{}',
                    error TEXT,
                    executed_at TEXT,
                    FOREIGN KEY (session_id) REFERENCES setup_sessions(session_id)
                );

                CREATE TABLE IF NOT EXISTS billing_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    display_name TEXT,
                    mode TEXT DEFAULT 'test',
                    account_status TEXT DEFAULT 'not_connected',
                    readiness_status TEXT DEFAULT 'needs_attention',
                    provider_account_id TEXT,
                    metadata TEXT DEFAULT '{}',
                    capabilities TEXT DEFAULT '[]',
                    missing_capabilities TEXT DEFAULT '[]',
                    next_actions TEXT DEFAULT '[]',
                    connected_at TEXT,
                    last_verified_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tenant_id, provider)
                );

                CREATE TABLE IF NOT EXISTS provider_secrets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    secret_name TEXT NOT NULL,
                    secret_value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tenant_id, provider, secret_name)
                );

                CREATE TABLE IF NOT EXISTS tenant_catalog_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    catalog_family TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    name TEXT NOT NULL,
                    tagline TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    billing_mode TEXT NOT NULL,
                    monthly_price_usd REAL DEFAULT 0,
                    setup_price_usd REAL DEFAULT 0,
                    active INTEGER DEFAULT 1,
                    source_kind TEXT DEFAULT 'template',
                    source_path TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    provider_product_id TEXT,
                    provider_monthly_price_id TEXT,
                    provider_setup_price_id TEXT,
                    sync_status TEXT DEFAULT 'pending',
                    provider_metadata TEXT DEFAULT '{}',
                    last_synced_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tenant_id, provider, slug)
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_provider ON setup_sessions(provider);
                CREATE INDEX IF NOT EXISTS idx_sessions_status ON setup_sessions(status);
                CREATE INDEX IF NOT EXISTS idx_sessions_tenant ON setup_sessions(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_steps_session ON setup_steps(session_id);
                CREATE INDEX IF NOT EXISTS idx_connection_tenant ON billing_connections(tenant_id);
                CREATE INDEX IF NOT EXISTS idx_catalog_tenant_provider ON tenant_catalog_items(tenant_id, provider);
                CREATE INDEX IF NOT EXISTS idx_provider_secrets_tenant_provider
                ON provider_secrets(tenant_id, provider);
                """
            )
            self._ensure_column(conn, "setup_sessions", "tenant_id", "tenant_id TEXT DEFAULT 'default'")
            self._ensure_column(conn, "setup_sessions", "phase", "phase TEXT DEFAULT 'guided_setup'")

    def create_session(
        self,
        session_id: str,
        provider: str,
        business_name: str,
        email: str,
        country: str = "us",
        tenant_id: str = "default",
        phase: str = "guided_setup",
    ) -> dict:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO setup_sessions
                    (session_id, tenant_id, provider, status, business_name, email, country, phase, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?)
                """,
                (session_id, tenant_id, provider, business_name, email, country, phase, now, now),
            )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM setup_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        return self._decode_session_row(row)

    def list_sessions(self, tenant_id: str | None = None, provider: str | None = None) -> list[dict]:
        query = "SELECT * FROM setup_sessions"
        clauses: list[str] = []
        params: list[Any] = []
        if tenant_id:
            clauses.append("tenant_id = ?")
            params.append(tenant_id)
        if provider:
            clauses.append("provider = ?")
            params.append(provider)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._decode_session_row(row) for row in rows]

    def update_session(
        self,
        session_id: str,
        status: str | None = None,
        current_step: int | None = None,
        total_steps: int | None = None,
        extracted_credentials: dict | None = None,
        screenshot_paths: list | None = None,
        notes: str | None = None,
        phase: str | None = None,
    ) -> dict | None:
        fields: list[str] = ["updated_at = ?"]
        params: list[Any] = [self._now()]
        if status is not None:
            fields.append("status = ?")
            params.append(status)
        if current_step is not None:
            fields.append("current_step = ?")
            params.append(current_step)
        if total_steps is not None:
            fields.append("total_steps = ?")
            params.append(total_steps)
        if extracted_credentials is not None:
            fields.append("extracted_credentials = ?")
            params.append(json.dumps(extracted_credentials))
        if screenshot_paths is not None:
            fields.append("screenshot_paths = ?")
            params.append(json.dumps(screenshot_paths))
        if notes is not None:
            fields.append("notes = ?")
            params.append(notes)
        if phase is not None:
            fields.append("phase = ?")
            params.append(phase)
        params.append(session_id)
        with self._connect() as conn:
            conn.execute(f"UPDATE setup_sessions SET {', '.join(fields)} WHERE session_id = ?", params)
        return self.get_session(session_id)

    def insert_step(
        self,
        step_id: str,
        session_id: str,
        step_index: int,
        title: str,
        description: str,
        automation_type: str,
        human_instructions: str,
        action: dict,
        completion_check: str,
        extract_fields: list[str],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO setup_steps
                    (step_id, session_id, step_index, title, description,
                     automation_type, human_instructions, action,
                     completion_check, extract_fields)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_id,
                    session_id,
                    step_index,
                    title,
                    description,
                    automation_type,
                    human_instructions,
                    json.dumps(action),
                    completion_check,
                    json.dumps(extract_fields),
                ),
            )

    def get_step(self, step_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM setup_steps WHERE step_id = ?", (step_id,)).fetchone()
        if row is None:
            return None
        return self._decode_step_row(row)

    def list_steps(self, session_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM setup_steps WHERE session_id = ? ORDER BY step_index ASC",
                (session_id,),
            ).fetchall()
        return [self._decode_step_row(row) for row in rows]

    def update_step(
        self,
        step_id: str,
        status: str,
        result_data: dict | None = None,
        error: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE setup_steps
                SET status = ?, result_data = ?, error = ?, executed_at = ?
                WHERE step_id = ?
                """,
                (status, json.dumps(result_data or {}), error, self._now(), step_id),
            )

    def upsert_connection(
        self,
        tenant_id: str,
        provider: str,
        display_name: str = "",
        mode: str = "test",
        account_status: str = "not_connected",
        readiness_status: str = "needs_attention",
        provider_account_id: str = "",
        metadata: dict[str, Any] | None = None,
        capabilities: list[str] | None = None,
        missing_capabilities: list[str] | None = None,
        next_actions: list[dict[str, Any]] | None = None,
        connected_at: str | None = None,
        last_verified_at: str | None = None,
    ) -> dict:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO billing_connections (
                    tenant_id, provider, display_name, mode, account_status, readiness_status,
                    provider_account_id, metadata, capabilities, missing_capabilities, next_actions,
                    connected_at, last_verified_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, provider) DO UPDATE SET
                    display_name = excluded.display_name,
                    mode = excluded.mode,
                    account_status = excluded.account_status,
                    readiness_status = excluded.readiness_status,
                    provider_account_id = excluded.provider_account_id,
                    metadata = excluded.metadata,
                    capabilities = excluded.capabilities,
                    missing_capabilities = excluded.missing_capabilities,
                    next_actions = excluded.next_actions,
                    connected_at = COALESCE(excluded.connected_at, billing_connections.connected_at),
                    last_verified_at = excluded.last_verified_at,
                    updated_at = excluded.updated_at
                """,
                (
                    tenant_id,
                    provider,
                    display_name,
                    mode,
                    account_status,
                    readiness_status,
                    provider_account_id,
                    json.dumps(metadata or {}),
                    json.dumps(capabilities or []),
                    json.dumps(missing_capabilities or []),
                    json.dumps(next_actions or []),
                    connected_at,
                    last_verified_at,
                    now,
                    now,
                ),
            )
        return self.get_connection(tenant_id, provider) or {}

    def get_connection(self, tenant_id: str, provider: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM billing_connections WHERE tenant_id = ? AND provider = ?",
                (tenant_id, provider),
            ).fetchone()
        if row is None:
            return None
        return self._decode_connection_row(row)

    def store_secret(self, tenant_id: str, provider: str, secret_name: str, secret_value: str) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_secrets (tenant_id, provider, secret_name, secret_value, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, provider, secret_name) DO UPDATE SET
                    secret_value = excluded.secret_value,
                    updated_at = excluded.updated_at
                """,
                (tenant_id, provider, secret_name, secret_value, now, now),
            )

    def read_secret(self, tenant_id: str, provider: str, secret_name: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT secret_value FROM provider_secrets
                WHERE tenant_id = ? AND provider = ? AND secret_name = ?
                """,
                (tenant_id, provider, secret_name),
            ).fetchone()
        if row is None:
            return None
        return str(row["secret_value"])

    def list_secret_names(self, tenant_id: str, provider: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT secret_name FROM provider_secrets WHERE tenant_id = ? AND provider = ? ORDER BY secret_name",
                (tenant_id, provider),
            ).fetchall()
        return [str(row["secret_name"]) for row in rows]

    def upsert_catalog_item(
        self,
        tenant_id: str,
        provider: str,
        catalog_family: str,
        slug: str,
        name: str,
        tagline: str,
        description: str,
        billing_mode: str,
        monthly_price_usd: float,
        setup_price_usd: float,
        active: bool,
        source_kind: str,
        source_path: str,
        metadata: dict[str, Any] | None = None,
        provider_product_id: str | None = None,
        provider_monthly_price_id: str | None = None,
        provider_setup_price_id: str | None = None,
        sync_status: str = "pending",
        provider_metadata: dict[str, Any] | None = None,
        last_synced_at: str | None = None,
    ) -> dict:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tenant_catalog_items (
                    tenant_id, provider, catalog_family, slug, name, tagline, description, billing_mode,
                    monthly_price_usd, setup_price_usd, active, source_kind, source_path, metadata,
                    provider_product_id, provider_monthly_price_id, provider_setup_price_id, sync_status,
                    provider_metadata, last_synced_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, provider, slug) DO UPDATE SET
                    catalog_family = excluded.catalog_family,
                    name = excluded.name,
                    tagline = excluded.tagline,
                    description = excluded.description,
                    billing_mode = excluded.billing_mode,
                    monthly_price_usd = excluded.monthly_price_usd,
                    setup_price_usd = excluded.setup_price_usd,
                    active = excluded.active,
                    source_kind = excluded.source_kind,
                    source_path = excluded.source_path,
                    metadata = excluded.metadata,
                    provider_product_id = COALESCE(excluded.provider_product_id, tenant_catalog_items.provider_product_id),
                    provider_monthly_price_id = COALESCE(excluded.provider_monthly_price_id, tenant_catalog_items.provider_monthly_price_id),
                    provider_setup_price_id = COALESCE(excluded.provider_setup_price_id, tenant_catalog_items.provider_setup_price_id),
                    sync_status = excluded.sync_status,
                    provider_metadata = excluded.provider_metadata,
                    last_synced_at = COALESCE(excluded.last_synced_at, tenant_catalog_items.last_synced_at),
                    updated_at = excluded.updated_at
                """,
                (
                    tenant_id,
                    provider,
                    catalog_family,
                    slug,
                    name,
                    tagline,
                    description,
                    billing_mode,
                    monthly_price_usd,
                    setup_price_usd,
                    int(active),
                    source_kind,
                    source_path,
                    json.dumps(metadata or {}),
                    provider_product_id,
                    provider_monthly_price_id,
                    provider_setup_price_id,
                    sync_status,
                    json.dumps(provider_metadata or {}),
                    last_synced_at,
                    now,
                    now,
                ),
            )
        return self.get_catalog_item(tenant_id, provider, slug) or {}

    def get_catalog_item(self, tenant_id: str, provider: str, slug: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM tenant_catalog_items
                WHERE tenant_id = ? AND provider = ? AND slug = ?
                """,
                (tenant_id, provider, slug),
            ).fetchone()
        if row is None:
            return None
        return self._decode_catalog_row(row)

    def list_catalog_items(self, tenant_id: str, provider: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tenant_catalog_items
                WHERE tenant_id = ? AND provider = ?
                ORDER BY catalog_family ASC, slug ASC
                """,
                (tenant_id, provider),
            ).fetchall()
        return [self._decode_catalog_row(row) for row in rows]

    def _decode_session_row(self, row: sqlite3.Row) -> dict:
        result = dict(row)
        result["extracted_credentials"] = self._decode_json(result.get("extracted_credentials"), {})
        result["screenshot_paths"] = self._decode_json(result.get("screenshot_paths"), [])
        return result

    def _decode_step_row(self, row: sqlite3.Row) -> dict:
        result = dict(row)
        result["action"] = self._decode_json(result.get("action"), {})
        result["extract_fields"] = self._decode_json(result.get("extract_fields"), [])
        result["result_data"] = self._decode_json(result.get("result_data"), {})
        return result

    def _decode_connection_row(self, row: sqlite3.Row) -> dict:
        result = dict(row)
        result["metadata"] = self._decode_json(result.get("metadata"), {})
        result["capabilities"] = self._decode_json(result.get("capabilities"), [])
        result["missing_capabilities"] = self._decode_json(result.get("missing_capabilities"), [])
        result["next_actions"] = self._decode_json(result.get("next_actions"), [])
        return result

    def _decode_catalog_row(self, row: sqlite3.Row) -> dict:
        result = dict(row)
        result["metadata"] = self._decode_json(result.get("metadata"), {})
        result["provider_metadata"] = self._decode_json(result.get("provider_metadata"), {})
        result["active"] = bool(result.get("active"))
        return result
