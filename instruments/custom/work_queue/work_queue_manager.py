"""
Work Queue Manager — business logic for work discovery, scoring, and execution.

Follows the LinearManager pattern: wraps DB + scanner + scorer.
"""

from typing import Any

from .codebase_scanner import scan_all as codebase_scan_all
from .priority_scorer import score_item
from .work_queue_db import WorkQueueDatabase


class WorkQueueManager:
    """Orchestrates codebase scanning, Linear sync, scoring, and execution."""

    def __init__(self, db_path: str, linear_api_key: str | None = None):
        self.db = WorkQueueDatabase(db_path)
        self._linear_api_key = linear_api_key

    # ── Project registration ──────────────────────────────────────────

    def register_project(self, path: str, name: str) -> dict[str, Any]:
        return self.db.register_project(path, name)

    def get_projects(self) -> list[dict[str, Any]]:
        return self.db.get_projects()

    def remove_project(self, path: str) -> bool:
        return self.db.remove_project(path)

    # ── Codebase scanning ─────────────────────────────────────────────

    def run_codebase_scan(
        self,
        project_path: str,
        scan_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Scan a project, score findings, and upsert into queue."""
        scan_id = self.db.start_scan("codebase", project_path)

        try:
            results = codebase_scan_all(project_path, scan_types)
            total_items = 0

            for scan_type, items in results.items():
                for item in items:
                    item["project_path"] = project_path
                    score, breakdown = score_item(item)
                    item["priority_score"] = score
                    item["priority_raw"] = breakdown
                    self.db.upsert_item(item)
                    total_items += 1

            self.db.complete_scan(scan_id, total_items)
            return {
                "success": True,
                "scan_id": scan_id,
                "items_found": total_items,
                "by_type": {k: len(v) for k, v in results.items()},
            }

        except Exception as e:
            self.db.complete_scan(scan_id, 0, str(e))
            return {"success": False, "error": str(e), "scan_id": scan_id}

    # ── Linear sync ───────────────────────────────────────────────────

    def sync_linear_issues(
        self,
        project_path: str,
        team_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Read Linear issues from the existing Linear cache and upsert into work queue."""
        scan_id = self.db.start_scan("linear", project_path)

        try:
            from instruments.custom.linear_integration.linear_db import LinearDatabase

            linear_db_path = self.db.get_setting(
                "linear_db_path",
                "instruments/custom/linear_integration/data/linear_integration.db",
            )
            linear_db = LinearDatabase(linear_db_path)
            issues = linear_db.get_issues(project_id=project_id, limit=200)

            count = 0
            for issue in issues:
                if team_id and issue.get("team_id") != team_id:
                    continue

                item = {
                    "source": "linear",
                    "source_type": "linear_issue",
                    "external_id": issue["id"],
                    "title": f"{issue.get('identifier', '')} {issue.get('title', '')}".strip(),
                    "description": issue.get("description", ""),
                    "url": issue.get("url", ""),
                    "project_path": project_path,
                    "linear_priority": issue.get("priority", 0),
                    "linear_state": issue.get("state_name", ""),
                    "linear_assignee": issue.get("assignee_name", ""),
                    "linear_labels": issue.get("labels", "[]"),
                }
                score, breakdown = score_item(item)
                item["priority_score"] = score
                item["priority_raw"] = breakdown
                self.db.upsert_item(item)
                count += 1

            self.db.complete_scan(scan_id, count)
            return {"success": True, "scan_id": scan_id, "items_synced": count}

        except ImportError:
            self.db.complete_scan(scan_id, 0, "Linear integration not available")
            return {"success": False, "error": "Linear integration not available"}
        except Exception as e:
            self.db.complete_scan(scan_id, 0, str(e))
            return {"success": False, "error": str(e), "scan_id": scan_id}

    # ── Full scan ─────────────────────────────────────────────────────

    def run_full_scan(self, project_path: str) -> dict[str, Any]:
        """Run both codebase scan and Linear sync."""
        codebase_result = self.run_codebase_scan(project_path)
        linear_result = self.sync_linear_issues(project_path)
        return {
            "success": codebase_result.get("success", False),
            "codebase": codebase_result,
            "linear": linear_result,
        }

    # ── Dashboard & queries ───────────────────────────────────────────

    def get_dashboard(self, project_path: str | None = None) -> dict[str, Any]:
        stats = self.db.get_dashboard_data(project_path)
        last_scan = self.db.get_last_scan(project_path=project_path)
        projects = self.db.get_projects()
        return {
            **stats,
            "last_scan": last_scan,
            "projects": projects,
        }

    def get_items(self, **kwargs) -> dict[str, Any]:
        items, total = self.db.get_items(**kwargs)
        return {"items": items, "total": total}

    def get_item(self, item_id: int) -> dict[str, Any] | None:
        return self.db.get_item(item_id)

    def search_items(self, query: str, project_path: str | None = None) -> list[dict[str, Any]]:
        return self.db.search_items(query, project_path)

    # ── Item mutations ────────────────────────────────────────────────

    def update_item_status(self, item_id: int, status: str) -> bool:
        return self.db.update_item_status(item_id, status)

    def update_item(self, item_id: int, updates: dict[str, Any]) -> bool:
        return self.db.update_item(item_id, updates)

    def bulk_update_status(self, item_ids: list[int], status: str) -> int:
        return self.db.bulk_update_status(item_ids, status)

    # ── Priority recalculation ────────────────────────────────────────

    def recalculate_priorities(self) -> int:
        """Re-score all non-terminal items with current weights."""
        items, _total = self.db.get_items(page_size=10000)
        count = 0
        for item in items:
            if item.get("status") in ("done", "dismissed"):
                continue
            score, _breakdown = score_item(item)
            if score != item.get("priority_score"):
                self.db.update_item(item["id"], {"priority_score": score})
                count += 1
        return count

    # ── Scheduled scanning (Phase 5) ─────────────────────────────────

    def get_scan_schedule(self) -> dict[str, Any] | None:
        """Return the current scan schedule config from settings."""
        enabled = self.db.get_setting("scan_schedule_enabled", "false")
        cron = self.db.get_setting("scan_schedule_cron", "0 */6 * * *")
        scan_types = self.db.get_setting("scan_schedule_types", "")
        project_path = self.db.get_setting("scan_schedule_project_path", "")
        task_uuid = self.db.get_setting("scan_schedule_task_uuid", "")
        return {
            "enabled": enabled == "true",
            "cron": cron,
            "scan_types": [s.strip() for s in scan_types.split(",") if s.strip()] if scan_types else [],
            "project_path": project_path,
            "task_uuid": task_uuid,
        }

    async def schedule_scan(
        self,
        cron: str = "0 */6 * * *",
        project_path: str = ".",
        scan_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Register a ScheduledTask that runs work queue scans on a cron schedule."""
        try:
            from python.helpers.task_scheduler import (
                ScheduledTask,
                TaskSchedule,
                TaskScheduler,
            )
        except ImportError:
            return {"success": False, "error": "Scheduler not available (crontab not installed)"}

        # Remove existing schedule first
        await self.unschedule_scan()

        # Parse cron expression
        parts = cron.split()
        if len(parts) != 5:
            return {"success": False, "error": f"Invalid cron expression: {cron} (need 5 fields)"}

        schedule = TaskSchedule(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            weekday=parts[4],
        )

        types_str = ",".join(scan_types) if scan_types else ""
        prompt = (
            f"Run a work queue scan for project at '{project_path}'.\n"
            f"Call the work_queue_scan API endpoint with project_path='{project_path}'"
        )
        if types_str:
            prompt += f" and scan_types=[{types_str}]"
        prompt += ".\nReport the scan results summary."

        task = ScheduledTask.create(
            name="Work Queue Scan",
            system_prompt=(
                "You are a maintenance agent. When triggered, call the work_queue_scan API "
                "to scan the codebase for TODOs, skipped tests, coverage gaps, and other work items. "
                "Report a brief summary of what was found."
            ),
            prompt=prompt,
            schedule=schedule,
        )

        scheduler = TaskScheduler.get()
        await scheduler.reload()
        await scheduler.add_task(task)

        # Persist config in work queue settings
        self.db.set_setting("scan_schedule_enabled", "true")
        self.db.set_setting("scan_schedule_cron", cron)
        self.db.set_setting("scan_schedule_types", types_str)
        self.db.set_setting("scan_schedule_project_path", project_path)
        self.db.set_setting("scan_schedule_task_uuid", task.uuid)

        return {
            "success": True,
            "task_uuid": task.uuid,
            "cron": cron,
            "project_path": project_path,
            "scan_types": scan_types or [],
        }

    async def unschedule_scan(self) -> dict[str, Any]:
        """Remove the scheduled scan task if it exists."""
        task_uuid = self.db.get_setting("scan_schedule_task_uuid", "")
        if not task_uuid:
            return {"success": True, "message": "No scan schedule to remove"}

        try:
            from python.helpers.task_scheduler import TaskScheduler

            scheduler = TaskScheduler.get()
            await scheduler.reload()
            await scheduler.remove_task_by_uuid(task_uuid)
        except ImportError:
            pass
        except Exception as e:
            return {"success": False, "error": f"Failed to remove scheduler task: {e}"}

        self.db.set_setting("scan_schedule_enabled", "false")
        self.db.set_setting("scan_schedule_task_uuid", "")

        return {"success": True, "message": "Scan schedule removed"}

    # ── Execution bridge (Phase 4) ────────────────────────────────────

    def execute_item(self, item_id: int) -> dict[str, Any]:
        """Start a workflow execution for the given work item.

        Guards:
        - Rejects if item not found.
        - Rejects if item is already in_progress (double-execution guard).
        - Rejects if item is in a terminal state (done/dismissed).
        - Sets status to in_progress with timestamp before launching workflow.
        """
        item = self.db.get_item(item_id)
        if not item:
            return {"success": False, "error": "Item not found"}

        current_status = item.get("status", "discovered")
        if current_status == "in_progress":
            return {
                "success": False,
                "error": "Item is already in progress",
                "execution_id": item.get("execution_id"),
            }
        if current_status in ("done", "dismissed"):
            return {"success": False, "error": f"Item is already {current_status}"}

        try:
            from instruments.custom.workflow_engine.workflow_manager import WorkflowEngineManager
            from python.helpers import files

            db_path = files.get_abs_path("./instruments/custom/workflow_engine/data/workflow.db")
            wf_manager = WorkflowEngineManager(db_path)

            context = {
                "work_item_id": item_id,
                "title": item["title"],
                "description": item.get("description", ""),
                "file_path": item.get("file_path", ""),
                "line_number": item.get("line_number"),
                "project_path": item.get("project_path", ""),
                "source": item.get("source", ""),
                "source_type": item.get("source_type", ""),
            }

            # Ensure the workflow definition exists (load from template on first use)
            workflow_name = "work_item_implementation"
            wf = wf_manager.get_workflow(name=workflow_name)
            if not wf or "error" in wf:
                template_path = files.get_abs_path(
                    "./instruments/custom/workflow_engine/templates/work_item_implementation.json"
                )
                created = wf_manager.create_from_template(template_path, workflow_name)
                if "error" in created:
                    import logging

                    logging.getLogger(__name__).warning(
                        "Could not load work_item_implementation template: %s", created["error"]
                    )
                    self.db.update_item(item_id, {"status": "in_progress"})
                    self.db.update_item_status(item_id, "in_progress")
                    return {"success": True, "item_id": item_id, "workflow": False}

            execution = wf_manager.start_workflow(
                workflow_name=workflow_name,
                context=context,
            )

            execution_id = execution.get("id") or execution.get("execution_id")
            self.db.update_item(
                item_id,
                {
                    "status": "in_progress",
                    "execution_id": execution_id,
                    "execution_status": "running",
                },
            )
            self.db.update_item_status(item_id, "in_progress")

            return {"success": True, "execution_id": execution_id, "item_id": item_id}

        except ImportError:
            return {"success": False, "error": "Workflow engine not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Stale item cleanup ──────────────────────────────────────────────

    def cleanup_stale_items(self, stale_hours: int = 24) -> int:
        """Reset in_progress items older than stale_hours back to 'queued'.

        This catches items whose workflow execution died without reporting back.
        Returns the number of items reset.
        """
        with self.db.db.transaction() as conn:
            cursor = conn.execute(
                "UPDATE work_items SET status = 'queued', execution_status = 'stale', "
                "updated_at = CURRENT_TIMESTAMP "
                "WHERE status = 'in_progress' "
                "AND started_at < datetime('now', ?)",
                (f"-{stale_hours} hours",),
            )
            count = cursor.rowcount
        return count

    # ── Settings ──────────────────────────────────────────────────────

    def get_settings(self) -> dict[str, str]:
        return self.db.get_all_settings()

    def set_setting(self, key: str, value: str) -> None:
        self.db.set_setting(key, value)
