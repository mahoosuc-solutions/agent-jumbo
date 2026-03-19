"""
Work Queue Settings API — get/set scanner config, weights, and Linear filters.
"""

from __future__ import annotations

import json
import traceback

from python.helpers import files
from python.helpers.api import ApiHandler


class WorkQueueSettings(ApiHandler):
    """API endpoint for work queue settings management."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            db_path = files.get_abs_path("./instruments/custom/work_queue/data/work_queue.db")
            manager = WorkQueueManager(db_path)

            action = input.get("action", "get")

            if action == "get":
                settings = manager.get_settings()
                return {"success": True, "settings": settings}

            if action == "set":
                key = input.get("key", "")
                value = input.get("value", "")
                if not key:
                    return {"success": False, "error": "key is required"}
                # If value is a dict/list, JSON-encode it
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                manager.set_setting(key, str(value))
                return {"success": True}

            if action == "set_bulk":
                settings = input.get("settings", {})
                if not isinstance(settings, dict):
                    return {"success": False, "error": "settings must be a dict"}
                for k, v in settings.items():
                    if isinstance(v, (dict, list)):
                        v = json.dumps(v)
                    manager.set_setting(k, str(v))
                return {"success": True, "updated": len(settings)}

            if action == "recalculate":
                count = manager.recalculate_priorities()
                return {"success": True, "recalculated": count}

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
