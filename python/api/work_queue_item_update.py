"""
Work Queue Item Update API — update status, priority, notes, tags.
"""

from __future__ import annotations

import traceback

from python.helpers.api import ApiHandler


class WorkQueueItemUpdate(ApiHandler):
    """API endpoint for updating a work queue item."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            manager = WorkQueueManager()

            item_id = input.get("item_id")
            if not item_id:
                return {"success": False, "error": "item_id is required"}

            action = input.get("action", "update_status")

            if action == "update_status":
                status = input.get("status", "")
                valid = {"discovered", "queued", "in_progress", "review", "done", "dismissed"}
                if status not in valid:
                    return {"success": False, "error": f"Invalid status. Must be one of: {valid}"}
                ok = manager.update_item_status(int(item_id), status)
                return {"success": ok}

            if action == "update":
                updates = {}
                for key in ("priority_score", "effort_estimate", "effort_minutes", "execution_id", "execution_status"):
                    if key in input:
                        updates[key] = input[key]
                if "tags" in input:
                    updates["tags"] = input["tags"]
                ok = manager.update_item(int(item_id), updates)
                return {"success": ok}

            if action == "add_tag":
                tag = input.get("tag", "")
                if not tag:
                    return {"success": False, "error": "tag is required"}
                ok = manager.add_tag(int(item_id), tag)
                return {"success": ok}

            if action == "set_tags":
                tags = input.get("tags", [])
                if not isinstance(tags, list):
                    return {"success": False, "error": "tags must be a list"}
                ok = manager.tag_item(int(item_id), tags)
                return {"success": ok}

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
