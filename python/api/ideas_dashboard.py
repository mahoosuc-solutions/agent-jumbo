"""
Ideas Dashboard API — stats and listing for action-oriented ideas.
"""

from __future__ import annotations

import traceback

from python.helpers import files
from python.helpers.api import ApiHandler


class IdeasDashboard(ApiHandler):
    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.ideas.ideas_manager import IdeasManager

            db_path = files.get_abs_path("./instruments/custom/ideas/data/ideas.db")
            manager = IdeasManager(db_path)

            action = input.get("action", "dashboard")
            if action == "dashboard":
                return {"success": True, **manager.get_dashboard()}
            if action == "list":
                items = manager.list_ideas(
                    status=input.get("status"),
                    priority=input.get("priority"),
                    q=input.get("query"),
                )
                return {"success": True, "ideas": items, "total": len(items)}
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
