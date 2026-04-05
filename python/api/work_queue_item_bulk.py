"""
Work Queue Item Bulk API — bulk queue, dismiss, or archive items.
"""

from __future__ import annotations

import traceback

from python.helpers.api import ApiHandler


class WorkQueueItemBulk(ApiHandler):
    """API endpoint for bulk operations on work queue items."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            manager = WorkQueueManager()

            action = input.get("action", "")
            item_ids = input.get("item_ids", [])

            if not item_ids or not isinstance(item_ids, list):
                return {"success": False, "error": "item_ids must be a non-empty list"}

            item_ids = [int(i) for i in item_ids]

            if action == "queue":
                count = manager.bulk_update_status(item_ids, "queued")
                return {"success": True, "updated": count}

            if action == "dismiss":
                count = manager.bulk_update_status(item_ids, "dismissed")
                return {"success": True, "updated": count}

            if action == "archive":
                count = manager.bulk_update_status(item_ids, "done")
                return {"success": True, "updated": count}

            return {"success": False, "error": f"Unknown action: {action}. Use 'queue', 'dismiss', or 'archive'."}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
