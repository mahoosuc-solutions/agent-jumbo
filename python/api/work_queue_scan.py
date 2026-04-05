"""
Work Queue Scan API — trigger codebase scans and Linear syncs.
"""

from __future__ import annotations

import traceback

from python.helpers.api import ApiHandler


class WorkQueueScan(ApiHandler):
    """API endpoint for triggering work queue scans."""

    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            manager = WorkQueueManager()

            action = input.get("action", "full_scan")
            project_path = input.get("project_path", "")

            if not project_path:
                # Default to first registered project
                projects = manager.get_projects()
                if projects:
                    project_path = projects[0]["path"]
                else:
                    return {"success": False, "error": "No project registered. Register a project first."}

            if action == "scan_codebase":
                scan_types = input.get("scan_types")
                result = manager.run_codebase_scan(project_path, scan_types)
                return result

            if action == "sync_linear":
                team_id = input.get("team_id")
                project_id = input.get("project_id")
                result = manager.sync_linear_issues(project_path, team_id, project_id)
                return result

            if action == "full_scan":
                result = manager.run_full_scan(project_path)
                return result

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
