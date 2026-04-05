"""
MOS Orchestrator — static methods for cross-system sync jobs and event hooks.

Used by:
- Scheduled cron jobs (via mos_scheduler_init.py)
- Event hooks in existing tools (customer_lifecycle, deployment_orchestrator, etc.)

All methods are fire-and-forget safe: wrapped in try/except, never crash the caller.
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger("mos.orchestrator")


def _resolve_keys(*names: str) -> dict[str, str]:
    """Resolve API keys/settings from settings store or env vars."""
    result: dict[str, str] = {}
    settings: dict[str, Any] = {}
    try:
        from python.helpers.settings import get_settings

        settings = get_settings()
    except Exception:
        pass

    env_map = {
        "linear_api_key": "LINEAR_API_KEY",
        "linear_default_team_id": "LINEAR_DEFAULT_TEAM_ID",
        "motion_api_key": "MOTION_API_KEY",
        "motion_workspace_id": "MOTION_WORKSPACE_ID",
        "notion_api_key": "NOTION_API_KEY",
        "notion_default_database_id": "NOTION_DEFAULT_DATABASE_ID",
    }
    for name in names:
        result[name] = settings.get(name, "") or os.getenv(env_map.get(name, ""), "")
    return result


async def _save_digest_to_executive(source: str, digest: dict[str, Any]) -> None:
    """Save a digest summary to EXECUTIVE memory (best-effort, non-blocking)."""
    try:
        from python.helpers.memory import Memory

        db = await Memory.get_by_subdir("default")
        summary = f"## MOS Digest — {source}\n```json\n{json.dumps(digest, default=str, indent=2)}\n```"
        await db.insert_text(summary, {"area": "executive", "source": source})
        logger.info("EXECUTIVE memory updated by %s", source)
    except Exception:
        logger.warning("Failed to write EXECUTIVE memory from %s", source, exc_info=True)


class MOSOrchestrator:
    """Static methods for cross-system orchestration."""

    # ── Scheduled sync jobs ──────────────────────────────────────────

    @staticmethod
    async def sync_linear_to_motion() -> dict[str, Any]:
        """Sync P0/P1 Linear issues → Motion time blocks.
        Scheduled: 8am, 12pm, 5pm weekdays."""
        try:
            from instruments.custom.motion_integration.motion_manager import MotionManager

            keys = _resolve_keys("motion_api_key", "linear_api_key", "motion_workspace_id")
            if not all(keys.values()):
                missing = [k for k, v in keys.items() if not v]
                logger.info("sync_linear_to_motion skipped: missing %s", missing)
                return {"skipped": True, "reason": f"Missing: {', '.join(missing)}"}

            manager = MotionManager(api_key=keys["motion_api_key"])
            logger.info("sync_linear_to_motion: starting")
            result = await manager.sync_from_linear(
                workspace_id=keys["motion_workspace_id"],
                linear_api_key=keys["linear_api_key"],
            )
            logger.info("sync_linear_to_motion: completed — %s", result)
            return result
        except Exception:
            logger.exception("sync_linear_to_motion failed")
            return {"error": "sync_linear_to_motion failed — see logs"}

    @staticmethod
    async def sync_linear_activity_to_digest() -> dict[str, Any]:
        """Fetch recent Linear changes for digest_builder.
        Scheduled: 6am daily."""
        try:
            from instruments.custom.linear_integration.linear_manager import LinearManager

            keys = _resolve_keys("linear_api_key")
            if not keys["linear_api_key"]:
                logger.info("sync_linear_activity_to_digest skipped: no LINEAR_API_KEY")
                return {"skipped": True, "reason": "No LINEAR_API_KEY"}

            manager = LinearManager(api_key=keys["linear_api_key"])
            logger.info("sync_linear_activity_to_digest: starting")
            result = await manager.sync_pipeline()
            logger.info("sync_linear_activity_to_digest: completed — %s", result)
            await _save_digest_to_executive("sync_linear_activity_to_digest", result)
            return result
        except Exception:
            logger.exception("sync_linear_activity_to_digest failed")
            return {"error": "sync_linear_activity_to_digest failed — see logs"}

    # ── Analytics & support scheduled jobs ──────────────────────────

    @staticmethod
    async def generate_analytics_digest() -> dict[str, Any]:
        """Generate the daily MOS analytics digest using digest_builder and analytics_roi_calculator.
        Scheduled: 7am daily."""
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            logger.info("generate_analytics_digest: starting")

            # Pull work queue summary for the past 24 hours
            wq_summary: dict[str, Any] = {}
            try:
                wq = WorkQueueManager()
                wq_summary = await wq.get_summary(hours=24)
            except Exception:
                logger.warning("generate_analytics_digest: work queue unavailable")

            # Pull Linear activity if available
            linear_summary: dict[str, Any] = {}
            try:
                from instruments.custom.linear_integration.linear_manager import LinearManager

                keys = _resolve_keys("linear_api_key")
                if keys["linear_api_key"]:
                    manager = LinearManager(api_key=keys["linear_api_key"])
                    linear_summary = await manager.get_activity_summary(hours=24)
            except Exception:
                logger.warning("generate_analytics_digest: linear activity unavailable")

            digest = {
                "type": "mos_analytics_digest",
                "period": "24h",
                "work_queue": wq_summary,
                "linear_activity": linear_summary,
                "status": "completed",
            }
            logger.info("generate_analytics_digest: completed")
            await _save_digest_to_executive("generate_analytics_digest", digest)
            return digest
        except Exception:
            logger.exception("generate_analytics_digest failed")
            return {"error": "generate_analytics_digest failed — see logs"}

    @staticmethod
    async def check_support_queue() -> dict[str, Any]:
        """Check the MOS work queue for open support-tagged items.
        Scheduled: hourly."""
        try:
            from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

            logger.info("check_support_queue: checking for open support items")

            wq = WorkQueueManager()
            items = await wq.get_items_by_tag("support")
            open_items = [i for i in items if i.get("status") not in ("done", "closed")]

            result = {
                "type": "mos_support_queue_check",
                "open_count": len(open_items),
                "items": [
                    {
                        "id": i.get("id"),
                        "title": i.get("title"),
                        "severity": i.get("severity", "unknown"),
                        "age_hours": i.get("age_hours", 0),
                    }
                    for i in open_items
                ],
                "status": "completed",
            }
            logger.info("check_support_queue: %d open support item(s)", len(open_items))
            return result
        except Exception:
            logger.exception("check_support_queue failed")
            return {"error": "check_support_queue failed — see logs"}

    # ── Event hooks (fire-and-forget) ────────────────────────────────

    @staticmethod
    async def on_lead_captured(
        customer_name: str,
        company: str = "",
        customer_id: int | None = None,
    ) -> None:
        """Hook: customer_lifecycle.capture_lead → create Linear issue."""
        try:
            from instruments.custom.linear_integration.linear_manager import LinearManager

            keys = _resolve_keys("linear_api_key", "linear_default_team_id")
            if not keys["linear_api_key"] or not keys["linear_default_team_id"]:
                return

            manager = LinearManager(api_key=keys["linear_api_key"])
            title = f"New Lead: {customer_name}" + (f" ({company})" if company else "")
            logger.info("on_lead_captured: creating Linear issue — %s", title)
            await manager.create_issue(
                title=title,
                team_id=keys["linear_default_team_id"],
                description=f"Lead captured via customer_lifecycle.\nCustomer ID: {customer_id}",
                priority=3,  # Medium
            )
        except Exception:
            logger.exception("on_lead_captured failed for %s", customer_name)

    @staticmethod
    async def on_deployment_success(
        project_name: str = "",
        related_issue_ids: list[str] | None = None,
    ) -> None:
        """Hook: deployment_orchestrator success → close related Linear issues."""
        try:
            if not related_issue_ids:
                return

            from instruments.custom.linear_integration.linear_manager import LinearManager

            keys = _resolve_keys("linear_api_key", "linear_default_team_id")
            if not keys["linear_api_key"]:
                return

            manager = LinearManager(api_key=keys["linear_api_key"])
            client = manager._get_client()

            team_id = keys["linear_default_team_id"]
            if team_id:
                states = await client.get_workflow_states(team_id)
                done_state = next(
                    (s for s in states if s.get("name", "").lower() == "done"),
                    None,
                )
                if done_state:
                    logger.info(
                        "on_deployment_success: closing %d issues for %s",
                        len(related_issue_ids),
                        project_name,
                    )
                    for issue_id in related_issue_ids:
                        await manager.update_issue(
                            issue_id=issue_id,
                            state_id=done_state["id"],
                        )
        except Exception:
            logger.exception("on_deployment_success failed for %s", project_name)
