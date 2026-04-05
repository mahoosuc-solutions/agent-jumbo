"""
MOS Sync Status API — sync job status across all integrations.

Supports triggering a sync for a given integration via ``trigger_sync``.
"""

from __future__ import annotations

import sqlite3
import traceback
from datetime import datetime, timezone

from python.helpers.api import ApiHandler
from python.helpers.db_paths import db_path
from python.helpers.defer import DeferredTask
from python.helpers.print_style import PrintStyle

# Maps integration name -> (db name, integration label)
_INTEGRATION_META: dict[str, tuple[str, str]] = {
    "linear": ("linear_integration.db", "linear_integration"),
    "motion": ("motion_integration.db", "motion_integration"),
    "notion": ("notion_integration.db", "notion_integration"),
}


class MOSSyncStatus(ApiHandler):
    """Shows sync job status: last run, success/fail counts, next scheduled.

    When ``trigger_sync`` is set to ``"linear"``, ``"motion"``, or ``"notion"``
    the handler spawns a background sync using the lightweight helpers in
    ``python.helpers.*_client`` and returns immediately with a ``sync_id``.
    """

    async def process(self, input: dict, request) -> dict:
        try:
            # ── Optional: trigger a sync ────────────────────────────────
            trigger = input.get("trigger_sync", "").lower().strip()
            if trigger and trigger in _INTEGRATION_META:
                sync_id = self._start_background_sync(trigger)
                return {"success": True, "triggered": True, "sync_id": sync_id}

            # ── Default: return status for every integration ────────────
            result: dict = {
                "success": True,
                "syncs": {},
            }

            for name, (db_rel, label) in _INTEGRATION_META.items():
                result["syncs"][name] = self._get_sync_status(db_rel, label)

            return result

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}

    # ── Background sync launcher ────────────────────────────────────────

    def _start_background_sync(self, integration: str) -> int:
        """Insert a ``started`` row, then spawn the sync on a DeferredTask."""
        db_name, _label = _INTEGRATION_META[integration]
        db_file = db_path(db_name)
        self._ensure_sync_log_table(db_file)

        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(db_file)
        try:
            cursor = conn.execute(
                "INSERT INTO sync_log (sync_type, started_at, status) VALUES (?, ?, ?)",
                (f"{integration}_sync", now, "running"),
            )
            sync_id = cursor.lastrowid or 0
            conn.commit()
        finally:
            conn.close()

        # Fire-and-forget via DeferredTask
        task = DeferredTask(thread_name=f"mos-sync-{integration}-{sync_id}")
        task.start_task(self._run_sync, integration, db_file, sync_id)

        return sync_id

    @staticmethod
    async def _run_sync(integration: str, db_path: str, sync_id: int) -> None:
        """Perform the actual sync, updating sync_log when done."""
        items_synced = 0
        error_msg: str | None = None

        try:
            from python.helpers.settings import get_settings

            settings = get_settings()

            if integration == "linear":
                from python.helpers.linear_client import LinearClient

                api_key = settings.get("linear_api_key", "") or ""
                client = LinearClient(api_key=api_key or None)
                teams = await client.get_teams()
                if teams:
                    team_id = teams[0]["id"]
                    issues = await client.search_issues("", team_id=team_id, limit=50)
                    items_synced = len(issues)
                    # Cache issues into the local DB
                    _cache_linear_issues(db_path, issues)
                else:
                    items_synced = 0

            elif integration == "motion":
                from python.helpers.motion_client import MotionClient

                api_key = settings.get("motion_api_key", "") or ""
                client = MotionClient(api_key=api_key or None)
                workspaces = await client.list_workspaces()
                all_tasks: list = []
                for ws in workspaces:
                    ws_id = ws.get("id", "")
                    if ws_id:
                        tasks = await client.list_tasks(workspace_id=ws_id)
                        all_tasks.extend(tasks)
                items_synced = len(all_tasks)
                _cache_motion_tasks(db_path, all_tasks)

            elif integration == "notion":
                from python.helpers.notion_client import NotionClient

                api_key = settings.get("notion_api_key", "") or ""
                client = NotionClient(api_key=api_key or None)
                # Search for databases to discover the default one, then query it
                databases = await client.search("", filter_type="database", page_size=5)
                all_pages: list = []
                for db in databases:
                    db_id = db.get("id", "")
                    if db_id:
                        pages = await client.query_database(db_id, page_size=50)
                        all_pages.extend(pages)
                items_synced = len(all_pages)

            status = "success"

        except Exception as exc:
            traceback.print_exc()
            status = "error"
            error_msg = str(exc)

        # Update the sync_log row
        completed = datetime.now(timezone.utc).isoformat()
        try:
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                UPDATE sync_log
                   SET completed_at = ?, status = ?, items_synced = ?, error = ?
                 WHERE id = ?
                """,
                (completed, status, items_synced, error_msg, sync_id),
            )
            conn.commit()
            conn.close()
        except Exception:
            traceback.print_exc()

        PrintStyle().print(f"MOS sync [{integration}] #{sync_id} completed: {status}, {items_synced} items")

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _ensure_sync_log_table(db_path: str) -> None:
        """Create the sync_log table if it doesn't exist yet."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                sync_type     TEXT,
                started_at    TEXT,
                completed_at  TEXT,
                status        TEXT,
                items_synced  INTEGER DEFAULT 0,
                error         TEXT
            )
            """
        )
        conn.commit()
        conn.close()

    def _get_sync_status(self, db_name: str, integration_name: str) -> dict:
        try:
            db_file = db_path(db_name)
            conn = sqlite3.connect(db_file)

            # Last sync
            cursor = conn.execute("SELECT * FROM sync_log ORDER BY id DESC LIMIT 1")
            cols = [d[0] for d in cursor.description] if cursor.description else []
            row = cursor.fetchone()
            last_sync = dict(zip(cols, row)) if row else None

            # Success/fail counts (last 30 days)
            cursor = conn.execute(
                """
                SELECT status, COUNT(*) FROM sync_log
                WHERE started_at > datetime('now', '-30 days')
                GROUP BY status
                """
            )
            counts = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()

            return {
                "last_sync": last_sync,
                "last_30_days": counts,
                "integration": integration_name,
            }
        except Exception as e:
            return {"error": str(e), "integration": integration_name}


# ── Local cache helpers (outside class for simplicity) ──────────────────


def _cache_linear_issues(db_path: str, issues: list[dict]) -> None:
    """Upsert Linear issues into a local cache table."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS issues_cache (
            id          TEXT PRIMARY KEY,
            identifier  TEXT,
            title       TEXT,
            url         TEXT,
            priority    INTEGER,
            state       TEXT,
            assignee    TEXT,
            updated_at  TEXT,
            cached_at   TEXT
        )
        """
    )
    now = datetime.now(timezone.utc).isoformat()
    for issue in issues:
        conn.execute(
            """
            INSERT OR REPLACE INTO issues_cache
                (id, identifier, title, url, priority, state, assignee, updated_at, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                issue.get("id", ""),
                issue.get("identifier", ""),
                issue.get("title", ""),
                issue.get("url", ""),
                issue.get("priority", 0),
                (issue.get("state") or {}).get("name", ""),
                (issue.get("assignee") or {}).get("name", ""),
                issue.get("updatedAt", ""),
                now,
            ),
        )
    conn.commit()
    conn.close()


def _cache_motion_tasks(db_path: str, tasks: list[dict]) -> None:
    """Upsert Motion tasks into a local cache table."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks_cache (
            id          TEXT PRIMARY KEY,
            name        TEXT,
            status      TEXT,
            priority    TEXT,
            workspace   TEXT,
            due_date    TEXT,
            cached_at   TEXT
        )
        """
    )
    now = datetime.now(timezone.utc).isoformat()
    for task in tasks:
        conn.execute(
            """
            INSERT OR REPLACE INTO tasks_cache
                (id, name, status, priority, workspace, due_date, cached_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.get("id", ""),
                task.get("name", ""),
                task.get("status", ""),
                task.get("priority", ""),
                task.get("workspace", {}).get("id", "") if isinstance(task.get("workspace"), dict) else "",
                task.get("dueDate", ""),
                now,
            ),
        )
    conn.commit()
    conn.close()
