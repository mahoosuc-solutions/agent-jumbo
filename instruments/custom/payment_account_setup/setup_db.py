"""SQLite persistence for payment account setup sessions and steps."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone


class SetupDatabase:
    """SQLite backend for payment account setup sessions."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS setup_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    current_step INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,
                    extracted_credentials TEXT DEFAULT '{}',
                    screenshot_paths TEXT DEFAULT '[]',
                    business_name TEXT,
                    email TEXT,
                    country TEXT DEFAULT 'us',
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

                CREATE INDEX IF NOT EXISTS idx_sessions_provider ON setup_sessions(provider);
                CREATE INDEX IF NOT EXISTS idx_sessions_status ON setup_sessions(status);
                CREATE INDEX IF NOT EXISTS idx_steps_session ON setup_steps(session_id);
            """)

    # -- session operations --------------------------------------------------

    def create_session(
        self,
        session_id: str,
        provider: str,
        business_name: str,
        email: str,
        country: str = "us",
    ) -> dict:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO setup_sessions
                    (session_id, provider, status, business_name, email, country, created_at, updated_at)
                VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)
                """,
                (session_id, provider, business_name, email, country, now, now),
            )
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict | None:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM setup_sessions WHERE session_id = ?", (session_id,))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if row is None:
            return None
        result = dict(zip(cols, row))
        result["extracted_credentials"] = json.loads(result.get("extracted_credentials") or "{}")
        result["screenshot_paths"] = json.loads(result.get("screenshot_paths") or "[]")
        return result

    def list_sessions(self) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM setup_sessions ORDER BY created_at DESC")
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        results = []
        for row in rows:
            r = dict(zip(cols, row))
            r["extracted_credentials"] = json.loads(r.get("extracted_credentials") or "{}")
            r["screenshot_paths"] = json.loads(r.get("screenshot_paths") or "[]")
            results.append(r)
        return results

    def update_session(
        self,
        session_id: str,
        status: str | None = None,
        current_step: int | None = None,
        total_steps: int | None = None,
        extracted_credentials: dict | None = None,
        screenshot_paths: list | None = None,
        notes: str | None = None,
    ) -> dict | None:
        fields: list[str] = ["updated_at = ?"]
        params: list = [self._now()]

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

        params.append(session_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE setup_sessions SET {', '.join(fields)} WHERE session_id = ?",
                params,
            )
        return self.get_session(session_id)

    # -- step operations -----------------------------------------------------

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
            cur = conn.execute("SELECT * FROM setup_steps WHERE step_id = ?", (step_id,))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if row is None:
            return None
        result = dict(zip(cols, row))
        result["action"] = json.loads(result.get("action") or "{}")
        result["extract_fields"] = json.loads(result.get("extract_fields") or "[]")
        result["result_data"] = json.loads(result.get("result_data") or "{}")
        return result

    def list_steps(self, session_id: str) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM setup_steps WHERE session_id = ? ORDER BY step_index ASC",
                (session_id,),
            )
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        results = []
        for row in rows:
            r = dict(zip(cols, row))
            r["action"] = json.loads(r.get("action") or "{}")
            r["extract_fields"] = json.loads(r.get("extract_fields") or "[]")
            r["result_data"] = json.loads(r.get("result_data") or "{}")
            results.append(r)
        return results

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
                (
                    status,
                    json.dumps(result_data or {}),
                    error,
                    self._now(),
                    step_id,
                ),
            )
