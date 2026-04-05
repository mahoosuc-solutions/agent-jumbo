"""
Signup Leads Tool
Query and export lead data from data/signups.db.
Actions: query, summary, export_csv
"""

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from python.helpers.tool import Response, Tool

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "signups.db"


def _get_conn() -> sqlite3.Connection | None:
    if not _DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


class SignupLeads(Tool):
    async def execute(self, **kwargs):
        """
        Query and export signup lead data.

        Args:
            action (str): 'query' | 'summary' | 'export_csv'
            plan (str): Filter by plan (free_cloud, pro, enterprise, community)
            email (str): Filter by email substring
            days (int): Lookback window in days (default: all time)
            limit (int): Max rows to return for query (default: 50)
        """
        action = self.args.get("action", "").lower()

        action_map = {
            "query": self._query,
            "summary": self._summary,
            "export_csv": self._export_csv,
        }

        handler = action_map.get(action)
        if not handler:
            valid = ", ".join(sorted(action_map.keys()))
            return Response(
                message=f"Unknown action: '{action}'. Valid actions: {valid}",
                break_loop=False,
            )

        try:
            return await handler()
        except Exception as e:
            return Response(message=f"SignupLeads error: {e!s}", break_loop=False)

    # ------------------------------------------------------------------

    async def _query(self) -> Response:
        plan = (self.args.get("plan") or "").strip().lower() or None
        email_substr = (self.args.get("email") or "").strip().lower() or None
        days = self.args.get("days")
        limit = int(self.args.get("limit", 50))

        conn = _get_conn()
        if conn is None:
            return Response(message="No signups found (database does not exist yet).", break_loop=False)

        try:
            clauses = []
            params: list = []
            if plan:
                clauses.append("plan = ?")
                params.append(plan)
            if email_substr:
                clauses.append("email LIKE ?")
                params.append(f"%{email_substr}%")
            if days:
                clauses.append(f"created_at > datetime('now', '-{int(days)} days')")

            where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
            rows = conn.execute(
                f"SELECT id, created_at, name, email, company, plan, source "
                f"FROM signups {where} ORDER BY created_at DESC LIMIT ?",
                [*params, limit],
            ).fetchall()
            leads = [dict(r) for r in rows]
        finally:
            conn.close()

        if not leads:
            return Response(message="No signups match the given filters.", break_loop=False)

        lines = [f"**{len(leads)} signup(s) found**\n"]
        for lead in leads:
            lines.append(
                f"- [{lead['created_at'][:10]}] **{lead['email']}** — {lead['plan']}"
                + (f" ({lead['name']})" if lead.get("name") else "")
            )
        return Response(message="\n".join(lines), break_loop=False)

    async def _summary(self) -> Response:
        days = int(self.args.get("days", 30))

        conn = _get_conn()
        if conn is None:
            return Response(message="No signups yet.", break_loop=False)

        try:
            total = conn.execute("SELECT COUNT(*) FROM signups").fetchone()[0]
            by_plan_rows = conn.execute("SELECT plan, COUNT(*) as count FROM signups GROUP BY plan").fetchall()
            by_plan = {r["plan"]: r["count"] for r in by_plan_rows}
            series_rows = conn.execute(
                "SELECT DATE(created_at) as day, COUNT(*) as signups "
                "FROM signups WHERE created_at > datetime('now', ? || ' days') "
                "GROUP BY day ORDER BY day",
                (f"-{days}",),
            ).fetchall()
            daily_series = [dict(r) for r in series_rows]
        finally:
            conn.close()

        lines = [
            f"**Signup Summary** (last {days} days for daily series)\n",
            f"Total signups: **{total}**",
        ]
        for plan, count in sorted(by_plan.items(), key=lambda x: -x[1]):
            lines.append(f"  - {plan}: {count}")
        if daily_series:
            lines.append(f"\nDaily activity ({len(daily_series)} days with signups):")
            for entry in daily_series[-7:]:  # show last 7 days
                lines.append(f"  {entry['day']}: {entry['signups']} signup(s)")

        return Response(message="\n".join(lines), break_loop=False)

    async def _export_csv(self) -> Response:
        conn = _get_conn()
        if conn is None:
            return Response(message="No signups yet — nothing to export.", break_loop=False)

        try:
            rows = conn.execute(
                "SELECT id, created_at, name, email, company, plan, source, referrer "
                "FROM signups ORDER BY created_at DESC"
            ).fetchall()
        finally:
            conn.close()

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        export_dir = _DB_PATH.parent
        export_path = export_dir / f"signups_export_{ts}.csv"

        with open(export_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "created_at", "name", "email", "company", "plan", "source", "referrer"],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))

        return Response(
            message=f"Exported {len(rows)} signup(s) to `{export_path}`.",
            break_loop=False,
        )
