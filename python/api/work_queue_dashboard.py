"""
Work Queue Dashboard API — stats, item listing, and search.
"""

from __future__ import annotations

import traceback

from python.helpers import files
from python.helpers.api import ApiHandler


class WorkQueueDashboard(ApiHandler):
    """API endpoint for work queue dashboard data."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            db_path = files.get_abs_path("./instruments/custom/work_queue/data/work_queue.db")
            manager = WorkQueueManager(db_path)

            action = input.get("action", "dashboard")

            if action == "dashboard":
                project_path = input.get("project_path")
                data = manager.get_dashboard(project_path)
                return {"success": True, **data}

            if action == "list":
                result = manager.get_items(
                    status=input.get("status"),
                    source=input.get("source"),
                    source_type=input.get("source_type"),
                    project_path=input.get("project_path"),
                    sort_by=input.get("sort_by", "priority_score"),
                    sort_dir=input.get("sort_dir", "DESC"),
                    page=int(input.get("page", 1)),
                    page_size=int(input.get("page_size", 50)),
                )
                return {"success": True, **result}

            if action == "search":
                query = input.get("query", "")
                items = manager.search_items(query, input.get("project_path"))
                return {"success": True, "items": items, "total": len(items)}

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
