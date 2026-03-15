"""
Linear Integration Manager — business logic for Linear CRUD and sync.
"""

from typing import Any

from .linear_db import LinearDatabase


class LinearManager:
    """Orchestrates Linear API calls and local cache synchronization."""

    def __init__(self, db_path: str, api_key: str | None = None):
        self.db = LinearDatabase(db_path)
        self._api_key = api_key

    def _get_client(self):
        """Lazy-import to avoid import-time side effects."""
        from python.helpers.linear_client import LinearClient

        return LinearClient(api_key=self._api_key)

    # ── CRUD ─────────────────────────────────────────────────────────

    async def create_issue(
        self,
        title: str,
        team_id: str,
        description: str = "",
        priority: int = 0,
        label_ids: list[str] | None = None,
        project_id: str | None = None,
        state_id: str | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        result = await client.create_issue(
            title=title,
            team_id=team_id,
            description=description,
            priority=priority,
            label_ids=label_ids,
            project_id=project_id,
            state_id=state_id,
        )
        # Cache the new issue locally
        issue = result.get("issue")
        if issue:
            self.db.upsert_issue(issue)
        return result

    async def update_issue(
        self,
        issue_id: str,
        title: str | None = None,
        description: str | None = None,
        state_id: str | None = None,
        priority: int | None = None,
        label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        result = await client.update_issue(
            issue_id=issue_id,
            title=title,
            description=description,
            state_id=state_id,
            priority=priority,
            label_ids=label_ids,
        )
        issue = result.get("issue")
        if issue:
            self.db.upsert_issue(issue)
        return result

    async def search_issues(
        self,
        query: str,
        team_id: str | None = None,
        limit: int = 25,
        use_cache: bool = False,
    ) -> list[dict[str, Any]]:
        if use_cache:
            return self.db.search_issues_cached(query, limit)
        client = self._get_client()
        issues = await client.search_issues(query=query, team_id=team_id, limit=limit)
        # Update cache
        self.db.upsert_issues(issues)
        return issues

    async def get_project_issues(
        self,
        project_id: str,
        limit: int = 50,
        use_cache: bool = False,
    ) -> list[dict[str, Any]]:
        if use_cache:
            return self.db.get_issues(project_id=project_id, limit=limit)
        client = self._get_client()
        issues = await client.get_project_issues(project_id=project_id, limit=limit)
        self.db.upsert_issues(issues)
        return issues

    # ── Sync pipeline ────────────────────────────────────────────────

    async def sync_pipeline(self, team_id: str | None = None) -> dict[str, Any]:
        """Full sync: projects + issues from Linear → local cache."""
        sync_id = self.db.start_sync("full")
        total_synced = 0

        try:
            client = self._get_client()

            # Sync projects
            projects = await client.get_projects(team_id=team_id)
            for project in projects:
                if team_id:
                    project["team_id"] = team_id
                self.db.upsert_project(project)
            total_synced += len(projects)

            # Sync issues per project
            for project in projects:
                issues = await client.get_project_issues(project["id"])
                self.db.upsert_issues(issues)
                total_synced += len(issues)

            self.db.complete_sync(sync_id, total_synced)
            return {
                "success": True,
                "projects_synced": len(projects),
                "total_items_synced": total_synced,
            }

        except Exception as e:
            self.db.complete_sync(sync_id, total_synced, error=str(e))
            return {"success": False, "error": str(e), "items_synced": total_synced}

    # ── Dashboard ────────────────────────────────────────────────────

    def get_dashboard(self) -> dict[str, Any]:
        """Get aggregated dashboard data from local cache."""
        return self.db.get_dashboard_data()
