"""
Work Queue Projects API — register, list, and remove project directories.
"""

from __future__ import annotations

import os
import traceback

from python.helpers import files
from python.helpers.api import ApiHandler


class WorkQueueProjects(ApiHandler):
    """API endpoint for managing work queue project directories."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            db_path = files.get_abs_path("./instruments/custom/work_queue/data/work_queue.db")
            manager = WorkQueueManager(db_path)

            action = input.get("action", "list")

            if action == "list":
                projects = manager.get_projects()
                return {"success": True, "projects": projects}

            if action == "register":
                path = input.get("path", "")
                name = input.get("name", "")
                if not path:
                    return {"success": False, "error": "path is required"}
                if not os.path.isdir(path):
                    return {"success": False, "error": f"Directory not found: {path}"}
                if not name:
                    name = os.path.basename(path)
                result = manager.register_project(path, name)
                return {"success": True, "project": result}

            if action == "remove":
                path = input.get("path", "")
                if not path:
                    return {"success": False, "error": "path is required"}
                removed = manager.remove_project(path)
                return {"success": removed, "removed": removed}

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
