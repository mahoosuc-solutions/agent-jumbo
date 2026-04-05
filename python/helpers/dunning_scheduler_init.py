"""
Dunning Scheduler Init — seeds the payment dunning cron task at boot.

Registers a daily 3am dunning cycle task in the persisted TaskScheduler if one
does not already exist. Idempotent: checks task name before adding.
Silently skipped if crontab/TaskScheduler is unavailable or STRIPE_API_KEY is unset.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_DUNNING_TASK_NAME = "payment-dunning-cycle"
_DUNNING_PROMPT = (
    "Run the automated payment dunning cycle to recover failed payments. "
    "Use the payment_dunning tool with action='run_cycle'. "
    "If any subscriptions were paused or cancelled, send a brief summary via telegram_send. "
    "If there is nothing past-due, confirm with a one-line log and exit."
)
_DUNNING_SYSTEM_PROMPT = (
    "You are an automated payment recovery agent. You execute the dunning cycle, "
    "retry failed payments according to the configured schedule, and report outcomes concisely."
)


async def seed_dunning_task() -> dict:
    """Seed the dunning cycle task into the scheduler. Idempotent."""
    if not os.environ.get("STRIPE_API_KEY"):
        return {"status": "skipped", "reason": "STRIPE_API_KEY not configured"}

    try:
        from python.helpers.task_scheduler import ScheduledTask, TaskSchedule, TaskScheduler
    except ImportError as e:
        return {"status": "skipped", "reason": f"TaskScheduler unavailable: {e}"}

    try:
        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Idempotency check: don't add if a task with this name already exists.
        existing = [t for t in scheduler.get_tasks() if t.name == _DUNNING_TASK_NAME]
        if existing:
            return {"status": "already_registered", "task_name": _DUNNING_TASK_NAME}

        schedule = TaskSchedule(minute="0", hour="3", day="*", month="*", weekday="*")
        task = ScheduledTask.create(
            name=_DUNNING_TASK_NAME,
            system_prompt=_DUNNING_SYSTEM_PROMPT,
            prompt=_DUNNING_PROMPT,
            schedule=schedule,
        )
        await scheduler.add_task(task)
        logger.info("[dunning-init] Seeded %s (daily 03:00)", _DUNNING_TASK_NAME)
        return {"status": "registered", "task_name": _DUNNING_TASK_NAME, "uuid": task.uuid}

    except Exception as e:
        logger.warning("[dunning-init] Failed to seed dunning task: %s", e)
        return {"status": "error", "reason": str(e)}
