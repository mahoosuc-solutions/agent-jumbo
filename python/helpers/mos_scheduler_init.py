"""
MOS Scheduler Init — auto-registers MOS cron tasks on startup.

Called during app initialization to schedule cross-system sync jobs.
Uses the existing task_scheduler infrastructure if available,
otherwise falls back to a simple asyncio-based scheduler.
"""

import traceback
from typing import Any


def register_mos_schedules() -> dict[str, Any]:
    """Register MOS sync jobs. Safe to call multiple times (idempotent)."""
    registered = []
    status = "skipped"
    reason = ""

    try:
        # This module was written for an older callback-based scheduler API.
        # The current persisted scheduler uses task models instead of handler callbacks.
        from python.helpers.task_scheduler import TaskScheduler

        has_legacy_api = hasattr(TaskScheduler, "get_instance")
        scheduler = TaskScheduler.get() if hasattr(TaskScheduler, "get") else None
        can_register_callbacks = scheduler is not None and hasattr(scheduler, "register_task")

        if has_legacy_api and can_register_callbacks:
            legacy_scheduler = TaskScheduler.get_instance()

            legacy_scheduler.register_task(
                name="mos_linear_to_motion",
                cron="0 8,12,17 * * 1-5",
                handler=_run_linear_to_motion,
            )
            registered.append("mos_linear_to_motion")

            legacy_scheduler.register_task(
                name="mos_linear_activity_digest",
                cron="0 6 * * *",
                handler=_run_linear_activity_digest,
            )
            registered.append("mos_linear_activity_digest")
            status = "registered"
        else:
            reason = "current scheduler does not expose the legacy callback registration API"

    except Exception as e:
        status = "error"
        reason = str(e)
        traceback.print_exc()

    return {
        "registered": registered,
        "count": len(registered),
        "status": status,
        "reason": reason,
        "skipped_reason": reason if status == "skipped" else "",
    }


async def _run_linear_to_motion() -> None:
    """Wrapper for scheduler callback."""
    try:
        from python.helpers.mos_orchestrator import MOSOrchestrator

        await MOSOrchestrator.sync_linear_to_motion()
    except Exception:
        traceback.print_exc()


async def _run_linear_activity_digest() -> None:
    """Wrapper for scheduler callback."""
    try:
        from python.helpers.mos_orchestrator import MOSOrchestrator

        await MOSOrchestrator.sync_linear_activity_to_digest()
    except Exception:
        traceback.print_exc()
