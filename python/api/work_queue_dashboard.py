"""
Work Queue Dashboard API — stats, item listing, and search.
"""

from __future__ import annotations

import traceback

from python.helpers.api import ApiHandler


class WorkQueueDashboard(ApiHandler):
    """API endpoint for work queue dashboard data."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            manager = WorkQueueManager()

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

            if action == "by_tag":
                tag = input.get("tag", "")
                if not tag:
                    return {"success": False, "error": "tag is required"}
                status = input.get("status")
                items = manager.get_items_by_tag(tag, status=status)
                return {"success": True, "items": items, "total": len(items), "tag": tag}

            if action == "add":
                title = input.get("title", "").strip()
                if not title:
                    return {"success": False, "error": "title is required"}
                import json

                tags = input.get("tags", [])
                item_id = manager.db.upsert_item(
                    title=title,
                    description=input.get("description", ""),
                    source=input.get("source", "manual"),
                    source_type="manual",
                    status="queued",
                    tags=json.dumps(tags) if isinstance(tags, list) else tags,
                )
                return {"success": True, "item_id": item_id}

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
