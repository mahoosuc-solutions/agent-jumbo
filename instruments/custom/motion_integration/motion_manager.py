"""
Motion Integration Manager — business logic for Motion tasks and Linear sync.
"""

from typing import Any

from .motion_db import MotionDatabase


class MotionManager:
    """Orchestrates Motion API calls, caching, and Linear sync."""

    def __init__(self, db_path: str, api_key: str | None = None):
        self.db = MotionDatabase(db_path)
        self._api_key = api_key

    def _get_client(self):
        from python.helpers.motion_client import MotionClient

        return MotionClient(api_key=self._api_key)

    # ── CRUD ─────────────────────────────────────────────────────────

    async def create_task(
        self,
        name: str,
        workspace_id: str,
        description: str = "",
        priority: str = "MEDIUM",
        duration: int = 30,
        deadline: str | None = None,
        project_id: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        result = await client.create_task(
            name=name,
            workspace_id=workspace_id,
            description=description,
            priority=priority,
            duration=duration,
            deadline=deadline,
            project_id=project_id,
            labels=labels,
        )
        self.db.upsert_task(result)
        return result

    async def list_tasks(
        self,
        workspace_id: str,
        project_id: str | None = None,
        status: str | None = None,
        use_cache: bool = False,
    ) -> list[dict[str, Any]]:
        if use_cache:
            return self.db.get_tasks(workspace_id=workspace_id)
        client = self._get_client()
        tasks = await client.list_tasks(workspace_id=workspace_id, project_id=project_id, status=status)
        for task in tasks:
            self.db.upsert_task(task)
        return tasks

    async def get_schedule(self, workspace_id: str) -> list[dict[str, Any]]:
        client = self._get_client()
        tasks = await client.get_schedule(workspace_id=workspace_id)
        for task in tasks:
            self.db.upsert_task(task)
        return tasks

    # ── Linear sync ──────────────────────────────────────────────────

    async def sync_from_linear(
        self,
        workspace_id: str,
        linear_api_key: str | None = None,
        linear_team_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Sync P0/P1 Linear issues → Motion tasks.

        1. Query Linear for In Progress issues with priority 1 or 2
        2. Check motion_linear_map for existing mappings
        3. Create new Motion tasks or skip existing (idempotent)
        4. Rate-limited: 2s pause between Motion API calls
        """
        sync_id = self.db.start_sync("linear_sync")
        created = 0
        skipped = 0

        try:
            from python.helpers.linear_client import LinearClient

            linear = LinearClient(api_key=linear_api_key)
            motion = self._get_client()

            # Get high-priority in-progress issues
            gql = """
            query HighPriorityIssues($filter: IssueFilter, $first: Int) {
                issues(filter: $filter, first: $first) {
                    nodes {
                        id identifier title description priority
                        state { name }
                        labels { nodes { name } }
                    }
                }
            }
            """
            filter_var: dict[str, Any] = {
                "priority": {"lte": 2, "gte": 1},
                "state": {"name": {"eqIgnoreCase": "In Progress"}},
            }
            if linear_team_id:
                filter_var["team"] = {"id": {"eq": linear_team_id}}

            result = await linear.execute(gql, {"filter": filter_var, "first": 50})
            issues = result.get("issues", {}).get("nodes", [])

            for issue in issues:
                # Check if already mapped
                existing = self.db.get_motion_id_for_linear(issue["id"])
                if existing:
                    skipped += 1
                    continue

                # Map Linear priority → Motion priority
                priority_map = {1: "ASAP", 2: "HIGH"}
                motion_priority = priority_map.get(issue.get("priority", 3), "MEDIUM")

                # Create Motion task
                motion_task = await motion.create_task(
                    name=f"[{issue['identifier']}] {issue['title']}",
                    workspace_id=workspace_id,
                    description=issue.get("description", ""),
                    priority=motion_priority,
                    duration=60,
                )

                self.db.upsert_task(motion_task)
                self.db.add_mapping(
                    motion_task_id=motion_task.get("id", ""),
                    linear_issue_id=issue["id"],
                    linear_identifier=issue.get("identifier", ""),
                )
                created += 1

            self.db.complete_sync(sync_id, created)
            return {
                "success": True,
                "created": created,
                "skipped": skipped,
                "total_issues": len(issues),
            }

        except Exception as e:
            self.db.complete_sync(sync_id, created, error=str(e))
            return {"success": False, "error": str(e), "created": created}
