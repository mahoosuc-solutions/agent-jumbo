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

            legacy_scheduler.register_task(
                name="mos_analytics_daily_digest",
                cron="0 7 * * *",
                handler=_run_analytics_digest,
            )
            registered.append("mos_analytics_daily_digest")

            legacy_scheduler.register_task(
                name="mos_support_queue_check",
                cron="0 * * * *",
                handler=_run_support_queue_check,
            )
            registered.append("mos_support_queue_check")

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


async def _run_analytics_digest() -> None:
    """Wrapper for analytics daily digest scheduler callback."""
    try:
        from python.helpers.mos_orchestrator import MOSOrchestrator

        await MOSOrchestrator.generate_analytics_digest()
    except Exception:
        traceback.print_exc()


async def _run_support_queue_check() -> None:
    """Wrapper for hourly support queue check scheduler callback."""
    try:
        from python.helpers.mos_orchestrator import MOSOrchestrator

        await MOSOrchestrator.check_support_queue()
    except Exception:
        traceback.print_exc()
