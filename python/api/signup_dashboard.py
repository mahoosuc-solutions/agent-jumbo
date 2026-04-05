"""
Signup Dashboard API
Provides aggregated signup/lead data from data/signups.db for operator visibility.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from python.helpers.api import ApiHandler

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "signups.db"

_ALL_PLANS = ["free_cloud", "pro", "enterprise", "community"]


def _get_conn() -> sqlite3.Connection | None:
    if not _DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


class SignupDashboard(ApiHandler):
    """API endpoint for signup/lead analytics dashboard."""

    async def process(self, input: dict, request) -> dict:
        """
        Return aggregated signup metrics.

        Optional input params:
        - days: int (default 30) — lookback window for daily series
        - plan: str — filter to a single plan
        """
        days = int(input.get("days", 30))
        plan_filter = (input.get("plan") or "").strip().lower() or None

        conn = _get_conn()
        if conn is None:
            return {
                "success": True,
                "total": 0,
                "by_plan": dict.fromkeys(_ALL_PLANS, 0),
                "recent": [],
                "daily_series": [],
                "note": "No signups yet.",
            }

        try:
            # Total count
            if plan_filter:
                total = conn.execute("SELECT COUNT(*) FROM signups WHERE plan = ?", (plan_filter,)).fetchone()[0]
            else:
                total = conn.execute("SELECT COUNT(*) FROM signups").fetchone()[0]

            # By-plan breakdown
            rows = conn.execute("SELECT plan, COUNT(*) as count FROM signups GROUP BY plan").fetchall()
            by_plan = dict.fromkeys(_ALL_PLANS, 0)
            for row in rows:
                by_plan[row["plan"]] = row["count"]

            # Recent signups (last 20)
            if plan_filter:
                recent_rows = conn.execute(
                    "SELECT id, created_at, name, email, company, plan, source "
                    "FROM signups WHERE plan = ? ORDER BY created_at DESC LIMIT 20",
                    (plan_filter,),
                ).fetchall()
            else:
                recent_rows = conn.execute(
                    "SELECT id, created_at, name, email, company, plan, source "
                    "FROM signups ORDER BY created_at DESC LIMIT 20"
                ).fetchall()
            recent = [dict(r) for r in recent_rows]

            # Daily series (last N days)
            if plan_filter:
                series_rows = conn.execute(
                    "SELECT DATE(created_at) as day, COUNT(*) as signups "
                    "FROM signups WHERE plan = ? "
                    "  AND created_at > datetime('now', ? || ' days') "
                    "GROUP BY day ORDER BY day",
                    (plan_filter, f"-{days}"),
                ).fetchall()
            else:
                series_rows = conn.execute(
                    "SELECT DATE(created_at) as day, COUNT(*) as signups "
                    "FROM signups WHERE created_at > datetime('now', ? || ' days') "
                    "GROUP BY day ORDER BY day",
                    (f"-{days}",),
                ).fetchall()
            daily_series = [dict(r) for r in series_rows]

        finally:
            conn.close()

        return {
            "success": True,
            "total": total,
            "by_plan": by_plan,
            "recent": recent,
            "daily_series": daily_series,
        }
