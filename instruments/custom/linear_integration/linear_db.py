"""
Linear Integration Database — local SQLite cache for Linear data.

Mirrors Linear state for fast dashboard queries and offline resilience.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any


class LinearDatabase:
    """Local cache for Linear issues, projects, and sync state."""

    def __init__(self, db_path: str = "data/linear_integration.db"):
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
            CREATE TABLE IF NOT EXISTS issues (
                id TEXT PRIMARY KEY,
                identifier TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                url TEXT,
                priority INTEGER DEFAULT 0,
                state_id TEXT,
                state_name TEXT,
                project_id TEXT,
                project_name TEXT,
                team_id TEXT,
                assignee_name TEXT,
                labels TEXT,
                created_at TEXT,
                updated_at TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                state TEXT,
                slug_id TEXT,
                team_id TEXT,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    # ── Issue operations ─────────────────────────────────────────────

    def upsert_issue(self, issue: dict[str, Any]) -> None:
        conn = self.get_connection()
        labels_json = json.dumps([lbl.get("name", "") for lbl in (issue.get("labels", {}).get("nodes", []))])
        conn.execute(
            """
            INSERT OR REPLACE INTO issues
                (id, identifier, title, description, url, priority,
                 state_id, state_name, project_id, project_name,
                 team_id, assignee_name, labels, created_at, updated_at, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                issue["id"],
                issue.get("identifier", ""),
                issue.get("title", ""),
                issue.get("description", ""),
                issue.get("url", ""),
                issue.get("priority", 0),
                (issue.get("state") or {}).get("id", ""),
                (issue.get("state") or {}).get("name", ""),
                (issue.get("project") or {}).get("id", ""),
                (issue.get("project") or {}).get("name", ""),
                issue.get("team_id", ""),
                (issue.get("assignee") or {}).get("name", ""),
                labels_json,
                issue.get("createdAt", ""),
                issue.get("updatedAt", ""),
            ),
        )
        conn.commit()
        conn.close()

    def upsert_issues(self, issues: list[dict[str, Any]]) -> int:
        for issue in issues:
            self.upsert_issue(issue)
        return len(issues)

    def get_issues(
        self,
        project_id: str | None = None,
        state_name: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        conn = self.get_connection()
        query = "SELECT * FROM issues WHERE 1=1"
        params: list[Any] = []

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if state_name:
            query += " AND state_name = ?"
            params.append(state_name)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return rows

    def search_issues_cached(self, query: str, limit: int = 25) -> list[dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.execute(
            """
            SELECT * FROM issues
            WHERE title LIKE ? OR description LIKE ? OR identifier LIKE ?
            ORDER BY updated_at DESC LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        )
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return rows

    # ── Project operations ───────────────────────────────────────────

    def upsert_project(self, project: dict[str, Any]) -> None:
        conn = self.get_connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO projects (id, name, state, slug_id, team_id, synced_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                project["id"],
                project.get("name", ""),
                project.get("state", ""),
                project.get("slugId", ""),
                project.get("team_id", ""),
            ),
        )
        conn.commit()
        conn.close()

    def get_projects(self) -> list[dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.execute("SELECT * FROM projects ORDER BY name")
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

    # ── Dashboard aggregation ────────────────────────────────────────

    def get_dashboard_data(self) -> dict[str, Any]:
        conn = self.get_connection()

        # Issues by state
        cursor = conn.execute("SELECT state_name, COUNT(*) FROM issues GROUP BY state_name ORDER BY COUNT(*) DESC")
        issues_by_state = {row[0]: row[1] for row in cursor.fetchall()}

        # Issues by priority
        cursor = conn.execute("SELECT priority, COUNT(*) FROM issues GROUP BY priority ORDER BY priority")
        priority_labels = {0: "No priority", 1: "Urgent", 2: "High", 3: "Medium", 4: "Low"}
        issues_by_priority = {priority_labels.get(row[0], f"P{row[0]}"): row[1] for row in cursor.fetchall()}

        # Projects count
        cursor = conn.execute("SELECT COUNT(*) FROM projects")
        projects_count = cursor.fetchone()[0]

        # Total issues
        cursor = conn.execute("SELECT COUNT(*) FROM issues")
        total_issues = cursor.fetchone()[0]

        # Last sync
        last_sync = self.get_last_sync()

        conn.close()

        return {
            "total_issues": total_issues,
            "issues_by_state": issues_by_state,
            "issues_by_priority": issues_by_priority,
            "projects_count": projects_count,
            "last_sync": last_sync,
        }
