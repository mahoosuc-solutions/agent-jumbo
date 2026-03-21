"""
Motion Integration Database — local SQLite cache for Motion tasks and mappings.
"""

import json
from typing import Any

from python.helpers.db_connection import DatabaseConnection, SyncLogMixin


class MotionDatabase(SyncLogMixin):
    """Local cache for Motion tasks and Linear<>Motion mappings."""

    def __init__(self, db_path: str = "data/motion_integration.db"):
        self.db = DatabaseConnection(db_path)
        self.init_database()

    def init_database(self) -> None:
        conn = self.db.conn

        conn.execute("""
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

        conn.execute("""
            CREATE TABLE IF NOT EXISTS motion_linear_map (
                motion_task_id TEXT PRIMARY KEY,
                linear_issue_id TEXT NOT NULL,
                linear_identifier TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(linear_issue_id)
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_workspace_id ON tasks_cache(workspace_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks_cache(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks_cache(updated_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks_cache(project_id)")

        conn.commit()

    # ── Task cache ───────────────────────────────────────────────────

    def upsert_task(self, task: dict[str, Any]) -> None:
        with self.db.transaction() as conn:
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

    def get_tasks(self, workspace_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        query = "SELECT * FROM tasks_cache WHERE 1=1"
        params: list[Any] = []
        if workspace_id:
            query += " AND workspace_id = ?"
            params.append(workspace_id)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        return self.db.query_rows(query, params)

    # ── Motion<>Linear mapping ────────────────────────────────────────

    def add_mapping(self, motion_task_id: str, linear_issue_id: str, linear_identifier: str = "") -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO motion_linear_map
                    (motion_task_id, linear_issue_id, linear_identifier)
                VALUES (?, ?, ?)
                """,
                (motion_task_id, linear_issue_id, linear_identifier),
            )

    def get_motion_id_for_linear(self, linear_issue_id: str) -> str | None:
        row = self.db.query_one(
            "SELECT motion_task_id FROM motion_linear_map WHERE linear_issue_id = ?",
            (linear_issue_id,),
        )
        return row["motion_task_id"] if row else None

    def get_all_mappings(self) -> list[dict[str, Any]]:
        return self.db.query_rows("SELECT * FROM motion_linear_map")
