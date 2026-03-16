"""
Motion Integration Database — local SQLite cache for Motion tasks and mappings.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any


class MotionDatabase:
    """Local cache for Motion tasks and Linear↔Motion mappings."""

    def __init__(self, db_path: str = "data/motion_integration.db"):
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
            CREATE TABLE IF NOT EXISTS tasks_cache (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'MEDIUM',
                status TEXT,
                duration INTEGER,
                deadline TEXT,
                workspace_id TEXT,
                project_id TEXT,
                scheduled_start TEXT,
                scheduled_end TEXT,
                labels TEXT,
                created_at TEXT,
                updated_at TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS motion_linear_map (
                motion_task_id TEXT PRIMARY KEY,
                linear_issue_id TEXT NOT NULL,
                linear_identifier TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(linear_issue_id)
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

        # Indexes for commonly-queried columns
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_workspace_id ON tasks_cache(workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks_cache(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks_cache(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks_cache(project_id)")

        conn.commit()
        conn.close()

    # ── Task cache ───────────────────────────────────────────────────

    def upsert_task(self, task: dict[str, Any]) -> None:
        conn = self.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO tasks_cache
                (id, name, description, priority, status, duration, deadline,
                 workspace_id, project_id, scheduled_start, scheduled_end,
                 labels, created_at, updated_at, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                task.get("id", ""),
                task.get("name", ""),
                task.get("description", ""),
                task.get("priority", "MEDIUM"),
                task.get("status", ""),
                task.get("duration"),
                task.get("dueDate", ""),
                task.get("workspaceId", task.get("workspace_id", "")),
                task.get("projectId", task.get("project_id", "")),
                task.get("scheduledStart", ""),
                task.get("scheduledEnd", ""),
                json.dumps(task.get("labels", [])),
                task.get("createdAt", task.get("created_at", "")),
                task.get("updatedAt", task.get("updated_at", "")),
            ),
        )
        conn.commit()
        conn.close()

    def get_tasks(self, workspace_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        conn = self.get_connection()
        query = "SELECT * FROM tasks_cache WHERE 1=1"
        params: list[Any] = []
        if workspace_id:
            query += " AND workspace_id = ?"
            params.append(workspace_id)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return rows

    # ── Motion↔Linear mapping ────────────────────────────────────────

    def add_mapping(self, motion_task_id: str, linear_issue_id: str, linear_identifier: str = "") -> None:
        conn = self.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO motion_linear_map
                (motion_task_id, linear_issue_id, linear_identifier)
            VALUES (?, ?, ?)
            """,
            (motion_task_id, linear_issue_id, linear_identifier),
        )
        conn.commit()
        conn.close()

    def get_motion_id_for_linear(self, linear_issue_id: str) -> str | None:
        conn = self.get_connection()
        cursor = conn.execute(
            "SELECT motion_task_id FROM motion_linear_map WHERE linear_issue_id = ?",
            (linear_issue_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_all_mappings(self) -> list[dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.execute("SELECT * FROM motion_linear_map")
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return rows

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
