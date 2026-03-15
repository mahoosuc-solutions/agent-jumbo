import json
import sqlite3
from typing import Any

from python.helpers.datetime_utils import isoformat_z, utc_now


class LifeOSDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS life_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS life_daily_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_date TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS life_widgets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    widget_id TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    order_index INTEGER DEFAULT 0,
                    config TEXT,
                    updated_at TEXT NOT NULL,
                    UNIQUE(widget_id)
                )
                """
            )

    def add_event(self, event_type: str, payload: dict[str, Any]) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO life_events (type, payload, created_at)
                VALUES (?, ?, ?)
                """,
                (event_type, json.dumps(payload), created_at),
            )
            return int(cursor.lastrowid)

    def list_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, type, payload, created_at
                FROM life_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "type": row[1],
                "payload": json.loads(row[2]),
                "created_at": row[3],
            }
            for row in rows
        ]

    def add_daily_plan(self, plan_date: str, content: str, status: str = "draft") -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO life_daily_plans (plan_date, content, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (plan_date, content, status, created_at),
            )
            return int(cursor.lastrowid)

    def get_latest_plan(self, plan_date: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, plan_date, content, status, created_at
                FROM life_daily_plans
                WHERE plan_date = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (plan_date,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "plan_date": row[1],
            "content": row[2],
            "status": row[3],
            "created_at": row[4],
        }

    def upsert_widget(self, widget_id: str, enabled: bool, order_index: int, config: dict[str, Any]) -> None:
        updated_at = isoformat_z(utc_now())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO life_widgets (widget_id, enabled, order_index, config, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(widget_id) DO UPDATE SET
                    enabled=excluded.enabled,
                    order_index=excluded.order_index,
                    config=excluded.config,
                    updated_at=excluded.updated_at
                """,
                (widget_id, int(enabled), order_index, json.dumps(config), updated_at),
            )

    def list_widgets(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT widget_id, enabled, order_index, config, updated_at
                FROM life_widgets
                ORDER BY order_index ASC
                """
            ).fetchall()
        return [
            {
                "widget_id": row[0],
                "enabled": bool(row[1]),
                "order_index": row[2],
                "config": json.loads(row[3] or "{}"),
                "updated_at": row[4],
            }
            for row in rows
        ]
