"""
Work Queue Item Get API — single item detail with scoring breakdown.
"""

from __future__ import annotations

import json
import traceback

from python.helpers.api import ApiHandler


class WorkQueueItemGet(ApiHandler):
    """API endpoint for retrieving a single work queue item."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            manager = WorkQueueManager()

            item_id = input.get("item_id")
            if not item_id:
                return {"success": False, "error": "item_id is required"}

            item = manager.get_item(int(item_id))
            if not item:
                return {"success": False, "error": f"Item {item_id} not found"}

            # Parse priority_raw JSON for the breakdown
            try:
                item["priority_breakdown"] = json.loads(item.get("priority_raw", "{}"))
            except (json.JSONDecodeError, TypeError):
                item["priority_breakdown"] = {}

            return {"success": True, "item": item}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
