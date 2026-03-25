"""
Ideas Database — SQLite storage for action-oriented ideas.
"""

from __future__ import annotations

from typing import Any

from python.helpers.db_connection import DatabaseConnection


class IdeasDatabase:
    """Persist ideas and lightweight dashboard stats."""

    def __init__(self, db_path: str = "data/ideas.db"):
        self.db = DatabaseConnection(db_path)
        self.init_database()

    def init_database(self) -> None:
        conn = self.db.conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                raw_note TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'captured',
                priority TEXT NOT NULL DEFAULT 'medium',
                theme TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'manual',
                conversation_context_id TEXT,
                project_name TEXT,
                workflow_name TEXT,
                clarified_summary TEXT,
                first_slice TEXT,
                promotion_readiness TEXT,
                promoted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._ensure_column("ideas", "workflow_name", "TEXT")
        self._ensure_column("ideas", "clarified_summary", "TEXT")
        self._ensure_column("ideas", "first_slice", "TEXT")
        self._ensure_column("ideas", "promotion_readiness", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ideas_priority ON ideas(priority)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ideas_theme ON ideas(theme)")
        conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = self.db.query_rows(f"PRAGMA table_info({table})")
        if any(col["name"] == column for col in columns):
            return
        with self.db.transaction() as conn:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def create_idea(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ideas (
                    title, raw_note, summary, status, priority, theme, source,
                    conversation_context_id, project_name, workflow_name,
                    clarified_summary, first_slice, promotion_readiness
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["title"],
                    payload.get("raw_note", ""),
                    payload.get("summary", ""),
                    payload.get("status", "captured"),
                    payload.get("priority", "medium"),
                    payload.get("theme", ""),
                    payload.get("source", "manual"),
                    payload.get("conversation_context_id"),
                    payload.get("project_name"),
                    payload.get("workflow_name"),
                    payload.get("clarified_summary"),
                    payload.get("first_slice"),
                    payload.get("promotion_readiness"),
                ),
            )
            idea_id = int(cursor.lastrowid)
        idea = self.get_idea(idea_id)
        if not idea:
            raise RuntimeError(f"Failed to load created idea {idea_id}")
        return idea

    def get_idea(self, idea_id: int) -> dict[str, Any] | None:
        return self.db.query_one("SELECT * FROM ideas WHERE id = ?", (idea_id,))

    def list_ideas(
        self,
        status: str | None = None,
        priority: str | None = None,
        q: str | None = None,
    ) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []
        if status:
            where.append("status = ?")
            params.append(status)
        if priority:
            where.append("priority = ?")
            params.append(priority)
        if q:
            like = f"%{q}%"
            where.append("(title LIKE ? OR raw_note LIKE ? OR summary LIKE ? OR theme LIKE ?)")
            params.extend([like, like, like, like])
        sql = f"""
            SELECT * FROM ideas
            WHERE {" AND ".join(where)}
            ORDER BY
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    ELSE 3
                END,
                updated_at DESC,
                id DESC
        """
        return self.db.query_rows(sql, params)

    def update_idea(self, idea_id: int, updates: dict[str, Any]) -> bool:
        allowed = {
            "title",
            "raw_note",
            "summary",
            "status",
            "priority",
            "theme",
            "conversation_context_id",
            "project_name",
            "workflow_name",
            "clarified_summary",
            "first_slice",
            "promotion_readiness",
        }
        sets: list[str] = []
        params: list[Any] = []
        for key, value in updates.items():
            if key in allowed:
                sets.append(f"{key} = ?")
                params.append(value)
        if not sets:
            return False
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(idea_id)
        with self.db.transaction() as conn:
            cursor = conn.execute(f"UPDATE ideas SET {', '.join(sets)} WHERE id = ?", params)
            return cursor.rowcount > 0

    def mark_promoted(self, idea_id: int, project_name: str, workflow_name: str | None = None) -> bool:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE ideas
                SET status = 'promoted',
                    project_name = ?,
                    workflow_name = ?,
                    promoted_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (project_name, workflow_name, idea_id),
            )
            return cursor.rowcount > 0

    def get_dashboard_data(self) -> dict[str, Any]:
        conn = self.db.conn
        total = conn.execute("SELECT COUNT(*) FROM ideas").fetchone()[0]
        promoted = conn.execute("SELECT COUNT(*) FROM ideas WHERE status = 'promoted'").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM ideas WHERE status IN ('captured', 'clarifying', 'proposed')"
        ).fetchone()[0]
        by_status_rows = conn.execute("SELECT status, COUNT(*) FROM ideas GROUP BY status").fetchall()
        by_priority_rows = conn.execute("SELECT priority, COUNT(*) FROM ideas GROUP BY priority").fetchall()
        recent = self.db.query_rows("SELECT * FROM ideas ORDER BY updated_at DESC, id DESC LIMIT 5")
        return {
            "total": total,
            "active": active,
            "promoted": promoted,
            "by_status": {row[0]: row[1] for row in by_status_rows},
            "by_priority": {row[0]: row[1] for row in by_priority_rows},
            "recent": recent,
        }
