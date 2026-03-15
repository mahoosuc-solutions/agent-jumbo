"""
MOS Test Connection API — lightweight connectivity check for each integration.
"""

from __future__ import annotations

import traceback

from python.helpers.api import ApiHandler

_VALID_INTEGRATIONS = {"linear", "motion", "notion"}


class MOSTestConnection(ApiHandler):
    """Tests API connectivity for a given integration.

    Accepts ``integration`` (``"linear"`` | ``"motion"`` | ``"notion"``) and an
    optional ``api_key``.  If ``api_key`` is omitted the value stored in
    settings / env is used.
    """

    async def process(self, input: dict, request) -> dict:
        integration = (input.get("integration") or "").lower().strip()
        if integration not in _VALID_INTEGRATIONS:
            return {
                "success": False,
                "error": f"Unknown integration '{integration}'. Must be one of: {', '.join(sorted(_VALID_INTEGRATIONS))}",
            }

        api_key: str | None = input.get("api_key") or None

        # Fall back to settings / env when no key provided
        if not api_key:
            api_key = self._key_from_settings(integration)

        try:
            if integration == "linear":
                details = await self._test_linear(api_key)
            elif integration == "motion":
                details = await self._test_motion(api_key)
            else:
                details = await self._test_notion(api_key)

            return {
                "success": True,
                "connected": True,
                "integration": integration,
                "details": details,
            }

        except Exception as e:
            traceback.print_exc()
            return {
                "success": True,
                "connected": False,
                "integration": integration,
                "error": str(e),
            }

    # ── Per-integration test methods ────────────────────────────────────

    @staticmethod
    async def _test_linear(api_key: str | None) -> dict:
        from python.helpers.linear_client import LinearClient

        client = LinearClient(api_key=api_key)
        teams = await client.get_teams()
        return {
            "teams": len(teams),
            "team_names": [t.get("name", "") for t in teams[:5]],
        }

    @staticmethod
    async def _test_motion(api_key: str | None) -> dict:
        from python.helpers.motion_client import MotionClient

        client = MotionClient(api_key=api_key)
        workspaces = await client.list_workspaces()
        return {
            "workspaces": len(workspaces),
            "workspace_names": [w.get("name", "") for w in workspaces[:5]],
        }

    @staticmethod
    async def _test_notion(api_key: str | None) -> dict:
        from python.helpers.notion_client import NotionClient

        client = NotionClient(api_key=api_key)
        databases = await client.search("", filter_type="database", page_size=5)
        return {
            "databases_found": len(databases),
            "database_titles": [_notion_title(db) for db in databases[:5]],
        }

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _key_from_settings(integration: str) -> str | None:
        """Try to load the API key from persisted settings."""
        try:
            from python.helpers.settings import get_settings

            key_map = {
                "linear": "linear_api_key",
                "motion": "motion_api_key",
                "notion": "notion_api_key",
            }
            settings = get_settings()
            return settings.get(key_map[integration], "") or None
        except Exception:
            return None


def _notion_title(db: dict) -> str:
    """Extract a human-readable title from a Notion database object."""
    title_parts = db.get("title", [])
    if isinstance(title_parts, list) and title_parts:
        return title_parts[0].get("plain_text", "(untitled)")
    return "(untitled)"
