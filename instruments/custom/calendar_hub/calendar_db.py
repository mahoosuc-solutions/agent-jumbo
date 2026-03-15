import json
import sqlite3
from typing import Any

from python.helpers.datetime_utils import isoformat_z, utc_now


class CalendarHubDatabase:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    auth_state TEXT NOT NULL,
                    token_ref TEXT,
                    scopes TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calendars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    external_id TEXT,
                    name TEXT NOT NULL,
                    color TEXT,
                    FOREIGN KEY(account_id) REFERENCES accounts(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    calendar_id INTEGER NOT NULL,
                    external_id TEXT,
                    title TEXT NOT NULL,
                    start TEXT NOT NULL,
                    end TEXT NOT NULL,
                    attendees TEXT,
                    location TEXT,
                    status TEXT DEFAULT 'confirmed',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(calendar_id) REFERENCES calendars(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    rules_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(account_id),
                    FOREIGN KEY(account_id) REFERENCES accounts(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS preps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    brief_text TEXT NOT NULL,
                    sources TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS followups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    task_uuid TEXT NOT NULL,
                    status TEXT DEFAULT 'scheduled',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES events(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    event_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

    def add_account(self, provider: str, auth_state: str, token_ref: str | None, scopes: list[str]) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO accounts (provider, auth_state, token_ref, scopes, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (provider, auth_state, token_ref, json.dumps(scopes), created_at),
            )
            return int(cursor.lastrowid)

    def update_account_auth(self, account_id: int, auth_state: str, token_ref: str | None, scopes: list[str]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE accounts
                SET auth_state = ?, token_ref = ?, scopes = ?
                WHERE id = ?
                """,
                (auth_state, token_ref, json.dumps(scopes), account_id),
            )

    def list_accounts(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, provider, auth_state, token_ref, scopes, created_at
                FROM accounts
                ORDER BY id ASC
                """
            ).fetchall()
        return [
            {
                "id": row[0],
                "provider": row[1],
                "auth_state": row[2],
                "token_ref": row[3],
                "scopes": json.loads(row[4] or "[]"),
                "created_at": row[5],
            }
            for row in rows
        ]

    def add_calendar(self, account_id: int, name: str, external_id: str | None = None, color: str | None = None) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO calendars (account_id, external_id, name, color)
                VALUES (?, ?, ?, ?)
                """,
                (account_id, external_id, name, color),
            )
            return int(cursor.lastrowid)

    def list_calendars(self, account_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, account_id, external_id, name, color
                FROM calendars
                WHERE account_id = ?
                ORDER BY id ASC
                """,
                (account_id,),
            ).fetchall()
        return [
            {
                "id": row[0],
                "account_id": row[1],
                "external_id": row[2],
                "name": row[3],
                "color": row[4],
            }
            for row in rows
        ]

    def add_event(
        self,
        calendar_id: int,
        title: str,
        start: str,
        end: str,
        attendees: list[str] | None = None,
        location: str | None = None,
        status: str = "confirmed",
        notes: str | None = None,
    ) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    calendar_id, title, start, end, attendees, location, status, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    calendar_id,
                    title,
                    start,
                    end,
                    json.dumps(attendees or []),
                    location,
                    status,
                    notes,
                    created_at,
                    created_at,
                ),
            )
            return int(cursor.lastrowid)

    def get_event(self, event_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, calendar_id, external_id, title, start, end, attendees, location, status, notes, created_at, updated_at
                FROM events
                WHERE id = ?
                """,
                (event_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "calendar_id": row[1],
            "external_id": row[2],
            "title": row[3],
            "start": row[4],
            "end": row[5],
            "attendees": json.loads(row[6] or "[]"),
            "location": row[7],
            "status": row[8],
            "notes": row[9],
            "created_at": row[10],
            "updated_at": row[11],
        }

    def update_event(self, event_id: int, updates: dict[str, Any]) -> dict[str, Any] | None:
        if not updates:
            return self.get_event(event_id)
        updates["updated_at"] = isoformat_z(utc_now())
        if "attendees" in updates:
            updates["attendees"] = json.dumps(updates["attendees"])
        columns = ", ".join([f"{key} = ?" for key in updates])
        params = [*list(updates.values()), event_id]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE events SET {columns} WHERE id = ?",  # nosec B608 - controlled query construction
                params,
            )
        return self.get_event(event_id)

    def delete_event(self, event_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
            return cursor.rowcount > 0

    def list_events(self, calendar_id: int | None = None, limit: int = 25) -> list[dict[str, Any]]:
        calendar_clause = ""
        params: list[Any] = [limit]
        if calendar_id is not None:
            calendar_clause = "WHERE calendar_id = ?"
            params = [calendar_id, limit]
        with self._connect() as conn:
            rows = conn.execute(  # nosec B608 - controlled query construction
                f"""
                SELECT id, calendar_id, external_id, title, start, end, attendees, location, status, notes, created_at, updated_at
                FROM events
                {calendar_clause}
                ORDER BY start ASC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [
            {
                "id": row[0],
                "calendar_id": row[1],
                "external_id": row[2],
                "title": row[3],
                "start": row[4],
                "end": row[5],
                "attendees": json.loads(row[6] or "[]"),
                "location": row[7],
                "status": row[8],
                "notes": row[9],
                "created_at": row[10],
                "updated_at": row[11],
            }
            for row in rows
        ]

    def add_audit_entry(self, entity_type: str, entity_id: int, event_hash: str) -> int:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit (entity_type, entity_id, event_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (entity_type, entity_id, event_hash, created_at),
            )
            return int(cursor.lastrowid)

    def upsert_rules(self, account_id: int, rules: dict[str, Any]) -> dict[str, Any]:
        updated_at = isoformat_z(utc_now())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rules (account_id, rules_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    rules_json=excluded.rules_json,
                    updated_at=excluded.updated_at
                """,
                (account_id, json.dumps(rules), updated_at),
            )
        return {"account_id": account_id, **rules}

    def get_rules(self, account_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT rules_json FROM rules WHERE account_id = ?
                """,
                (account_id,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row[0])

    def add_prep(self, event_id: int, brief_text: str, sources: list[str]) -> dict[str, Any]:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO preps (event_id, brief_text, sources, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (event_id, brief_text, json.dumps(sources), created_at),
            )
            prep_id = int(cursor.lastrowid)
        return {"id": prep_id, "event_id": event_id, "brief_text": brief_text, "sources": sources}

    def add_followup(self, event_id: int, task_uuid: str) -> dict[str, Any]:
        created_at = isoformat_z(utc_now())
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO followups (event_id, task_uuid, status, created_at)
                VALUES (?, ?, 'scheduled', ?)
                """,
                (event_id, task_uuid, created_at),
            )
            followup_id = int(cursor.lastrowid)
        return {"id": followup_id, "event_id": event_id, "task_uuid": task_uuid, "status": "scheduled"}
