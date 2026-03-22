"""SQLite storage for knowledge ingestion."""

import json
import sqlite3
from datetime import timedelta
from typing import Any

from python.helpers.datetime_utils import isoformat_z, utc_now


class KnowledgeIngestDatabase:
    """SQLite persistence for sources, items, and digests."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    uri TEXT NOT NULL,
                    tags TEXT,
                    cadence TEXT,
                    config TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._ensure_columns(conn, "sources", {"config": "TEXT"})
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    fetched_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    item_count INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    FOREIGN KEY(source_id) REFERENCES sources(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT,
                    published_at TEXT,
                    content TEXT,
                    content_hash TEXT NOT NULL,
                    tags TEXT,
                    confidence REAL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_id, content_hash),
                    FOREIGN KEY(source_id) REFERENCES sources(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS digests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    window_start TEXT NOT NULL,
                    window_end TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    channels TEXT
                )
                """
            )

    def _ensure_columns(self, conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for column, col_type in columns.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")

    def add_source(
        self,
        name: str,
        source_type: str,
        uri: str,
        tags: list[str] | None = None,
        cadence: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sources (name, type, uri, tags, cadence, config, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    source_type,
                    uri,
                    json.dumps(tags or []),
                    cadence,
                    json.dumps(config or {}),
                    created_at,
                ),
            )
            return int(cursor.lastrowid)

    def list_sources(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name, type, uri, tags, cadence, config, created_at FROM sources").fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "type": row[2],
                "uri": row[3],
                "tags": json.loads(row[4] or "[]"),
                "cadence": row[5],
                "config": json.loads(row[6] or "{}"),
                "created_at": row[7],
            }
            for row in rows
        ]

    def get_source(self, source_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, type, uri, tags, cadence, config, created_at FROM sources WHERE id = ?",
                (source_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "type": row[2],
            "uri": row[3],
            "tags": json.loads(row[4] or "[]"),
            "cadence": row[5],
            "config": json.loads(row[6] or "{}"),
            "created_at": row[7],
        }

    def find_source(self, name: str, uri: str) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM sources WHERE name = ? AND uri = ?",
                (name, uri),
            ).fetchone()
        return int(row[0]) if row else None

    def record_ingestion(
        self,
        source_id: int,
        status: str,
        item_count: int,
        error: str | None = None,
    ) -> int:
        fetched_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ingestions (source_id, fetched_at, status, item_count, error)
                VALUES (?, ?, ?, ?, ?)
                """,
                (source_id, fetched_at, status, item_count, error),
            )
            return int(cursor.lastrowid)

    def add_item(
        self,
        source_id: int,
        title: str,
        url: str | None,
        published_at: str | None,
        content: str | None,
        content_hash: str,
        tags: list[str] | None,
        confidence: float,
    ) -> bool:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO items (
                        source_id, title, url, published_at, content, content_hash,
                        tags, confidence, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        source_id,
                        title,
                        url,
                        published_at,
                        content,
                        content_hash,
                        json.dumps(tags or []),
                        confidence,
                        created_at,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def list_items(
        self,
        since_hours: int = 24,
        tags: list[str] | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        since = utc_now() - timedelta(hours=since_hours)
        since_iso = since.isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source_id, title, url, published_at, content, content_hash,
                       tags, confidence, created_at
                FROM items
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (since_iso, limit),
            ).fetchall()
        items = [
            {
                "id": row[0],
                "source_id": row[1],
                "title": row[2],
                "url": row[3],
                "published_at": row[4],
                "content": row[5],
                "content_hash": row[6],
                "tags": json.loads(row[7] or "[]"),
                "confidence": row[8],
                "created_at": row[9],
            }
            for row in rows
        ]
        if tags:
            tags_lower = {tag.lower() for tag in tags}
            items = [item for item in items if tags_lower.intersection({t.lower() for t in item["tags"]})]
        return items

    def add_digest(
        self,
        window_start: str,
        window_end: str,
        summary: str,
        channels: list[str] | None = None,
    ) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO digests (created_at, window_start, window_end, summary, channels)
                VALUES (?, ?, ?, ?, ?)
                """,
                (created_at, window_start, window_end, summary, json.dumps(channels or [])),
            )
            return int(cursor.lastrowid)

    def list_digests(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, window_start, window_end, summary, channels
                FROM digests
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "created_at": row[1],
                "window_start": row[2],
                "window_end": row[3],
                "summary": row[4],
                "channels": json.loads(row[5] or "[]"),
            }
            for row in rows
        ]
