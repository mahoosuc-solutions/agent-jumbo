"""
Work Queue Item Execute API — start workflow execution for a work item.
"""

from __future__ import annotations

import traceback

from python.helpers import files
from python.helpers.api import ApiHandler


class WorkQueueItemExecute(ApiHandler):
    """API endpoint for executing a work queue item via workflow engine."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            db_path = files.get_abs_path("./instruments/custom/work_queue/data/work_queue.db")
            manager = WorkQueueManager(db_path)

            item_id = input.get("item_id")
            if not item_id:
                return {"success": False, "error": "item_id is required"}

            result = manager.execute_item(int(item_id))
            return result

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
