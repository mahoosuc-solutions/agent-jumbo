"""
Shared SQLite connection manager for integration databases.

Provides:
- DatabaseConnection: lazy-open persistent connection with WAL, transaction safety
- SyncLogMixin: shared start_sync / complete_sync / get_last_sync operations
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class DatabaseConnection:
    """Managed SQLite connection with context manager safety.

    Holds a single persistent connection per instance (one per DB path).
    Sets WAL mode once on first connect. Provides transaction() for
    commit/rollback safety and query helpers that return dicts.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Lazy-open persistent connection with WAL."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
        return self._conn

    @contextmanager
    def transaction(self):
        """Yield connection, commit on success, rollback on error."""
        try:
            yield self.conn
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def query_rows(self, sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
        """Execute SELECT and return list of dicts."""
        cursor = self.conn.execute(sql, params)
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def query_one(self, sql: str, params: tuple | list = ()) -> dict[str, Any] | None:
        """Execute SELECT and return first row as dict, or None."""
        rows = self.query_rows(sql, params)
        return rows[0] if rows else None

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


class SyncLogMixin:
    """Shared sync log operations — requires self.db: DatabaseConnection."""

    db: DatabaseConnection  # provided by the concrete class

    def start_sync(self, sync_type: str) -> int:
        with self.db.transaction() as conn:
            cursor = conn.execute("INSERT INTO sync_log (sync_type) VALUES (?)", (sync_type,))
            return cursor.lastrowid  # type: ignore[return-value]

    def complete_sync(self, sync_id: int, items_synced: int, error: str | None = None) -> None:
        with self.db.transaction() as conn:
            status = "error" if error else "completed"
            conn.execute(
                "UPDATE sync_log SET completed_at = CURRENT_TIMESTAMP, status = ?, items_synced = ?, error = ? WHERE id = ?",
                (status, items_synced, error, sync_id),
            )

    def get_last_sync(self, sync_type: str | None = None) -> dict[str, Any] | None:
        if sync_type:
            return self.db.query_one(
                "SELECT * FROM sync_log WHERE sync_type = ? ORDER BY id DESC LIMIT 1",
                (sync_type,),
            )
        return self.db.query_one("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1")
