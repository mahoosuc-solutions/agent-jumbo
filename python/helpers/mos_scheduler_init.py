"""
MOS Scheduler Init — seeds MOS cross-system sync tasks at boot.

Registers 4 MOS operational tasks in the persisted TaskScheduler if they do not
already exist. All tasks are idempotent: existing tasks (matched by name) are not
re-added. Silently skipped if TaskScheduler is unavailable.

Task schedule:
  3x/day weekdays: mos-linear-to-motion (8am, 12pm, 5pm Mon–Fri)
  Daily (1):       mos-linear-activity-digest (6am)
  Daily (1):       mos-analytics-daily-digest (7am)
  Hourly (1):      mos-support-queue-check (top of every hour)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are the MOS operations orchestrator. "
    "You execute cross-system sync jobs, generate operational digests, "
    "and monitor support queues. Be concise and actionable."
)

_MOS_TASKS = [
    {
        "name": "mos-linear-to-motion",
        "schedule": {"minute": "0", "hour": "8,12,17", "day": "*", "month": "*", "weekday": "1-5"},
        "prompt": (
            "Sync P0/P1 Linear issues to Motion time blocks. "
            "Use the MOS orchestrator sync_linear_to_motion method. "
            "Report any sync failures or missing API keys."
        ),
    },
    {
        "name": "mos-linear-activity-digest",
        "schedule": {"minute": "0", "hour": "6", "day": "*", "month": "*", "weekday": "*"},
        "prompt": (
            "Fetch recent Linear changes for the daily digest. "
            "Use the MOS orchestrator sync_linear_activity_to_digest method. "
            "Summarize new issues, state changes, and completions from the past 24 hours."
        ),
    },
    {
        "name": "mos-analytics-daily-digest",
        "schedule": {"minute": "0", "hour": "7", "day": "*", "month": "*", "weekday": "*"},
        "prompt": (
            "Generate the daily MOS analytics digest. "
            "Use the MOS orchestrator generate_analytics_digest method. "
            "Include work queue summary and Linear activity from the past 24 hours."
        ),
    },
    {
        "name": "mos-support-queue-check",
        "schedule": {"minute": "0", "hour": "*", "day": "*", "month": "*", "weekday": "*"},
        "prompt": (
            "Check the MOS work queue for open support-tagged items. "
            "Use the MOS orchestrator check_support_queue method. "
            "Escalate any items older than 4 hours or with severity >= high."
        ),
    },
]


async def seed_mos_tasks() -> dict:
    """Seed MOS scheduler tasks. Idempotent — skips existing tasks."""
    try:
        from python.helpers.task_scheduler import ScheduledTask, TaskSchedule, TaskScheduler
    except ImportError as e:
        return {"status": "skipped", "reason": f"TaskScheduler unavailable: {e}"}

    try:
        scheduler = TaskScheduler.get()
        await scheduler.reload()

        existing_names = {t.name for t in scheduler.get_tasks()}
        registered = []
        skipped = []

        for task_def in _MOS_TASKS:
            if task_def["name"] in existing_names:
                skipped.append(task_def["name"])
                continue

            sched = task_def["schedule"]
            schedule = TaskSchedule(
                minute=sched["minute"],
                hour=sched["hour"],
                day=sched["day"],
                month=sched["month"],
                weekday=sched["weekday"],
            )
            task = ScheduledTask.create(
                name=task_def["name"],
                system_prompt=_SYSTEM_PROMPT,
                prompt=task_def["prompt"],
                schedule=schedule,
            )
            await scheduler.add_task(task)
            registered.append(task_def["name"])
            logger.info("[mos-init] Seeded %s", task_def["name"])

        return {
            "status": "ok",
            "registered": registered,
            "skipped_existing": skipped,
            "total": len(_MOS_TASKS),
        }

    except Exception as e:
        logger.warning("[mos-init] Failed to seed MOS tasks: %s", e)
        return {"status": "error", "reason": str(e)}
