"""
Work Queue Database — SQLite store for discovered work items.

Uses DatabaseConnection for safe connection management with WAL
and transaction safety.
"""

import json
from typing import Any

from python.helpers.db_connection import DatabaseConnection


class WorkQueueDatabase:
    """Local store for work queue items, scan history, and settings."""

    def __init__(self, db_path: str = "data/work_queue.db"):
        self.db = DatabaseConnection(db_path)
        self.init_database()

    def init_database(self) -> None:
        conn = self.db.conn

        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS work_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT NOT NULL,
                source TEXT NOT NULL,
                source_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                file_path TEXT,
                line_number INTEGER,
                url TEXT,
                status TEXT NOT NULL DEFAULT 'discovered',
                priority_score INTEGER DEFAULT 0,
                priority_raw TEXT DEFAULT '{}',
                effort_estimate TEXT,
                effort_minutes INTEGER,
                project_path TEXT NOT NULL,
                linear_priority INTEGER,
                linear_state TEXT,
                linear_assignee TEXT,
                linear_labels TEXT,
                execution_id INTEGER,
                execution_status TEXT,
                discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                queued_at TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_work_items_dedup
            ON work_items(source, external_id, project_path)
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_work_items_status ON work_items(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_work_items_project ON work_items(project_path)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_work_items_priority ON work_items(priority_score DESC)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT NOT NULL,
                project_path TEXT NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'running',
                items_found INTEGER DEFAULT 0,
                error TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

    # ── Project operations ────────────────────────────────────────────

    def register_project(self, path: str, name: str) -> dict[str, Any]:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO projects (path, name) VALUES (?, ?)",
                (path, name),
            )
        return {"path": path, "name": name}

    def get_projects(self) -> list[dict[str, Any]]:
        return self.db.query_rows("SELECT * FROM projects ORDER BY name")

    def remove_project(self, path: str) -> bool:
        with self.db.transaction() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE path = ?", (path,))
            return cursor.rowcount > 0

    # ── Work item operations ──────────────────────────────────────────

    def upsert_item(self, item: dict[str, Any]) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO work_items
                    (external_id, source, source_type, title, description,
                     file_path, line_number, url, status, priority_score, priority_raw,
                     effort_estimate, effort_minutes, project_path,
                     linear_priority, linear_state, linear_assignee, linear_labels,
                     discovered_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT(source, external_id, project_path)
                DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    file_path = excluded.file_path,
                    line_number = excluded.line_number,
                    url = excluded.url,
                    priority_score = excluded.priority_score,
                    priority_raw = excluded.priority_raw,
                    effort_estimate = excluded.effort_estimate,
                    effort_minutes = excluded.effort_minutes,
                    linear_priority = excluded.linear_priority,
                    linear_state = excluded.linear_state,
                    linear_assignee = excluded.linear_assignee,
                    linear_labels = excluded.linear_labels,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    item["external_id"],
                    item["source"],
                    item["source_type"],
                    item["title"],
                    item.get("description", ""),
                    item.get("file_path"),
                    item.get("line_number"),
                    item.get("url"),
                    item.get("status", "discovered"),
                    item.get("priority_score", 0),
                    json.dumps(item.get("priority_raw", {})),
                    item.get("effort_estimate"),
                    item.get("effort_minutes"),
                    item["project_path"],
                    item.get("linear_priority"),
                    item.get("linear_state"),
                    item.get("linear_assignee"),
                    json.dumps(item.get("linear_labels", [])) if item.get("linear_labels") else None,
                ),
            )

    def upsert_items(self, items: list[dict[str, Any]]) -> int:
        for item in items:
            self.upsert_item(item)
        return len(items)

    def get_item(self, item_id: int) -> dict[str, Any] | None:
        return self.db.query_one("SELECT * FROM work_items WHERE id = ?", (item_id,))

    def get_items(
        self,
        status: str | None = None,
        source: str | None = None,
        source_type: str | None = None,
        project_path: str | None = None,
        sort_by: str = "priority_score",
        sort_dir: str = "DESC",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        where_clauses = ["1=1"]
        params: list[Any] = []

        if status:
            where_clauses.append("status = ?")
            params.append(status)
        if source:
            where_clauses.append("source = ?")
            params.append(source)
        if source_type:
            where_clauses.append("source_type = ?")
            params.append(source_type)
        if project_path:
            where_clauses.append("project_path = ?")
            params.append(project_path)

        where = " AND ".join(where_clauses)

        # Count total
        cursor = self.db.conn.execute(f"SELECT COUNT(*) FROM work_items WHERE {where}", params)
        total = cursor.fetchone()[0]

        # Validate sort column
        allowed_sorts = {"priority_score", "updated_at", "discovered_at", "title", "source_type", "status"}
        if sort_by not in allowed_sorts:
            sort_by = "priority_score"
        if sort_dir.upper() not in ("ASC", "DESC"):
            sort_dir = "DESC"

        offset = (page - 1) * page_size
        cursor = self.db.conn.execute(
            f"SELECT * FROM work_items WHERE {where} ORDER BY {sort_by} {sort_dir} LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        )
        cols = [d[0] for d in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        return rows, total

    def search_items(self, query: str, project_path: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
        q = f"%{query}%"
        params: list[Any] = [q, q, q]
        extra = ""
        if project_path:
            extra = " AND project_path = ?"
            params.append(project_path)
        params.append(limit)

        return self.db.query_rows(
            f"""
            SELECT * FROM work_items
            WHERE (title LIKE ? OR description LIKE ? OR file_path LIKE ?){extra}
            ORDER BY priority_score DESC LIMIT ?
            """,
            params,
        )

    def update_item_status(self, item_id: int, status: str) -> bool:
        ts_col = {
            "queued": "queued_at",
            "in_progress": "started_at",
            "done": "completed_at",
        }.get(status)

        with self.db.transaction() as conn:
            if ts_col:
                conn.execute(
                    f"UPDATE work_items SET status = ?, {ts_col} = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, item_id),
                )
            else:
                conn.execute(
                    "UPDATE work_items SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, item_id),
                )
        return True

    def update_item(self, item_id: int, updates: dict[str, Any]) -> bool:
        allowed = {"status", "priority_score", "effort_estimate", "effort_minutes", "execution_id", "execution_status"}
        sets = []
        params: list[Any] = []
        for k, v in updates.items():
            if k in allowed:
                sets.append(f"{k} = ?")
                params.append(v)
        if not sets:
            return False
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(item_id)

        with self.db.transaction() as conn:
            conn.execute(f"UPDATE work_items SET {', '.join(sets)} WHERE id = ?", params)
        return True

    def bulk_update_status(self, item_ids: list[int], status: str) -> int:
        if not item_ids:
            return 0
        placeholders = ",".join("?" * len(item_ids))
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE work_items SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders})",
                [status, *item_ids],
            )
        return len(item_ids)

    # ── Dashboard aggregation ─────────────────────────────────────────

    def get_dashboard_data(self, project_path: str | None = None) -> dict[str, Any]:
        conn = self.db.conn
        where = "WHERE project_path = ?" if project_path else ""
        params: list[Any] = [project_path] if project_path else []

        cursor = conn.execute(f"SELECT COUNT(*) FROM work_items {where}", params)
        total = cursor.fetchone()[0]

        cursor = conn.execute(
            f"SELECT status, COUNT(*) FROM work_items {where} GROUP BY status",
            params,
        )
        by_status = {row[0]: row[1] for row in cursor.fetchall()}

        cursor = conn.execute(
            f"SELECT source, COUNT(*) FROM work_items {where} GROUP BY source",
            params,
        )
        by_source = {row[0]: row[1] for row in cursor.fetchall()}

        cursor = conn.execute(
            f"SELECT source_type, COUNT(*) FROM work_items {where} GROUP BY source_type",
            params,
        )
        by_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Done this week
        cursor = conn.execute(
            f"SELECT COUNT(*) FROM work_items {where + ' AND' if where else 'WHERE'} "
            "status = 'done' AND completed_at >= datetime('now', '-7 days')",
            params,
        )
        done_this_week = cursor.fetchone()[0]

        return {
            "total": total,
            "by_status": by_status,
            "by_source": by_source,
            "by_type": by_type,
            "done_this_week": done_this_week,
        }

    # ── Scan log ──────────────────────────────────────────────────────

    def start_scan(self, scan_type: str, project_path: str) -> int:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO scan_log (scan_type, project_path) VALUES (?, ?)",
                (scan_type, project_path),
            )
            return cursor.lastrowid  # type: ignore[return-value]

    def complete_scan(self, scan_id: int, items_found: int, error: str | None = None) -> None:
        with self.db.transaction() as conn:
            status = "error" if error else "completed"
            conn.execute(
                "UPDATE scan_log SET completed_at = CURRENT_TIMESTAMP, status = ?, items_found = ?, error = ? WHERE id = ?",
                (status, items_found, error, scan_id),
            )

    def get_last_scan(self, scan_type: str | None = None, project_path: str | None = None) -> dict[str, Any] | None:
        where_parts = []
        params: list[Any] = []
        if scan_type:
            where_parts.append("scan_type = ?")
            params.append(scan_type)
        if project_path:
            where_parts.append("project_path = ?")
            params.append(project_path)
        where = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        return self.db.query_one(f"SELECT * FROM scan_log {where} ORDER BY id DESC LIMIT 1", params)

    # ── Settings ──────────────────────────────────────────────────────

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, value),
            )

    def get_all_settings(self) -> dict[str, str]:
        rows = self.db.query_rows("SELECT key, value FROM settings")
        return {row["key"]: row["value"] for row in rows}
