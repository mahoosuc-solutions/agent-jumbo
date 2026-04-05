"""
MOS Sync History API — paginated sync log for a given integration.
"""

from __future__ import annotations

import sqlite3
import traceback

from python.helpers.api import ApiHandler
from python.helpers.db_paths import db_path

# Integration -> DB name
_DB_PATHS: dict[str, str] = {
    "linear": "linear_integration.db",
    "motion": "motion_integration.db",
    "notion": "notion_integration.db",
}


class MOSSyncHistory(ApiHandler):
    """Returns paginated sync history for a given integration."""

    async def process(self, input: dict, request) -> dict:
        try:
            integration = (input.get("integration") or "").lower().strip()
            if integration not in _DB_PATHS:
                return {
                    "success": False,
                    "error": f"Unknown integration '{integration}'. Must be one of: {', '.join(_DB_PATHS)}",
                }

            limit = max(1, min(int(input.get("limit", 20)), 100))
            offset = max(0, int(input.get("offset", 0)))

            db_file = db_path(_DB_PATHS[integration])
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row

            # Total count
            total_row = conn.execute("SELECT COUNT(*) AS cnt FROM sync_log").fetchone()
            total = total_row["cnt"] if total_row else 0

            # Paginated results (newest first)
            rows = conn.execute(
                "SELECT * FROM sync_log ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()

            history = [dict(row) for row in rows]
            conn.close()

            return {
                "success": True,
                "integration": integration,
                "history": history,
                "total": total,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
