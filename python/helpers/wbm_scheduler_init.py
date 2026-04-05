"""
WBM Scheduler Init — seeds the StayHive hospitality recurring workflow tasks at boot.

Registers 9 WBM operational tasks in the persisted TaskScheduler if they do not
already exist. All tasks are idempotent: existing tasks (matched by name) are not
re-added. Silently skipped if TaskScheduler is unavailable or WBM_TENANT_ID is unset.

Task schedule:
  Daily (3):    wbm-daily-ops-brief (7am), wbm-daily-checkin-scan (2:45pm),
                wbm-daily-occupancy-check (8pm)
  Weekly (2):   wbm-weekly-revenue-review (Mon 8am),
                wbm-weekly-competitor-intel (Wed 9am)
  Monthly (2):  wbm-monthly-rate-analysis (1st 8am),
                wbm-monthly-billing-review (2nd 10am)
  Seasonal (1): wbm-seasonal-rate-activation (Mar/Jun/Sep/Dec 1st 6am)
  Yearly (1):   wbm-yearly-platform-audit (Jan 1st 9am)
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are the StayHive hospitality operations agent. "
    "You execute recurring property management workflows, generate structured reports, "
    "and escalate issues that require operator attention. Be concise and actionable."
)

_WBM_TASKS = [
    {
        "name": "wbm-daily-ops-brief",
        "schedule": {"minute": "0", "hour": "7", "day": "*", "month": "*", "weekday": "*"},
        "prompt": (
            "Generate the daily operations brief for the StayHive property. "
            "Use the wbm_embedded_workflow tool with phase='daily_ops_brief'. "
            "Include: check-in/check-out summary, active maintenance tickets, "
            "staff coverage status, and any guest escalations from the past 24 hours. "
            "Send a summary via telegram_send if any issues require operator attention."
        ),
    },
    {
        "name": "wbm-daily-checkin-scan",
        "schedule": {"minute": "45", "hour": "14", "day": "*", "month": "*", "weekday": "*"},
        "prompt": (
            "Run the afternoon check-in readiness scan. "
            "Use the wbm_embedded_workflow tool with phase='checkin_scan'. "
            "Verify: door codes issued for today's arrivals, rooms marked clean and ready, "
            "any late checkouts resolved. Alert via telegram_send if any room is not ready "
            "for a confirmed arrival."
        ),
    },
    {
        "name": "wbm-daily-occupancy-check",
        "schedule": {"minute": "0", "hour": "20", "day": "*", "month": "*", "weekday": "*"},
        "prompt": (
            "Run the evening occupancy check and next-day forecast. "
            "Use the wbm_embedded_workflow tool with phase='occupancy_check'. "
            "Report: tonight's occupancy rate, tomorrow's arrivals and departures, "
            "and any open nights in the next 7 days that pricing automation should address. "
            "Log results and send a summary if occupancy is below the alert threshold."
        ),
    },
    {
        "name": "wbm-weekly-revenue-review",
        "schedule": {"minute": "0", "hour": "8", "day": "*", "month": "*", "weekday": "1"},
        "prompt": (
            "Run the weekly revenue review. "
            "Use the wbm_embedded_workflow tool with phase='revenue_review'. "
            "Include: week-over-week ADR, RevPAR, occupancy trends, top revenue sources, "
            "and any pricing recommendations for the coming week. "
            "Send the summary via telegram_send."
        ),
    },
    {
        "name": "wbm-weekly-competitor-intel",
        "schedule": {"minute": "0", "hour": "9", "day": "*", "month": "*", "weekday": "3"},
        "prompt": (
            "Run the weekly competitor intelligence scan. "
            "Use the wbm_embedded_workflow tool with phase='competitor_intel'. "
            "Check pricing positioning against the configured comp set, "
            "identify any rate gaps or opportunities, and flag if any competitor "
            "is running promotions that should influence our pricing strategy. "
            "Log findings and send a summary if action is recommended."
        ),
    },
    {
        "name": "wbm-monthly-rate-analysis",
        "schedule": {"minute": "0", "hour": "8", "day": "1", "month": "*", "weekday": "*"},
        "prompt": (
            "Run the monthly rate analysis. "
            "Use the wbm_embedded_workflow tool with phase='rate_analysis'. "
            "Analyze: last month's performance vs rate strategy, "
            "upcoming seasonal demand signals, recommended rate adjustments for next month, "
            "and dynamic pricing guardrail review. "
            "Generate a monthly rate memo and send via telegram_send."
        ),
    },
    {
        "name": "wbm-monthly-billing-review",
        "schedule": {"minute": "0", "hour": "10", "day": "2", "month": "*", "weekday": "*"},
        "prompt": (
            "Run the monthly billing review. "
            "Use the wbm_embedded_workflow tool with phase='billing_review'. "
            "Check: subscription charges processed, any failed payments or dunning events, "
            "platform fee reconciliation, and billing configuration health. "
            "Flag any billing anomalies via telegram_send."
        ),
    },
    {
        "name": "wbm-seasonal-rate-activation",
        "schedule": {"minute": "0", "hour": "6", "day": "1", "month": "3,6,9,12", "weekday": "*"},
        "prompt": (
            "Activate seasonal rate adjustments for the new quarter. "
            "Use the wbm_embedded_workflow tool with phase='seasonal_rate_activation'. "
            "Review the seasonal rate plan, activate the appropriate rate season, "
            "verify pricing automation guardrails are set correctly, "
            "and confirm the new season is active in WBM. "
            "Send a confirmation via telegram_send."
        ),
    },
    {
        "name": "wbm-yearly-platform-audit",
        "schedule": {"minute": "0", "hour": "9", "day": "1", "month": "1", "weekday": "*"},
        "prompt": (
            "Run the annual platform audit for the StayHive property. "
            "Use the wbm_embedded_workflow tool with phase='final_validation'. "
            "Audit: all integration health checks, credential expiry, "
            "room inventory accuracy, staff access review, "
            "competitor intel source review, and dynamic pricing configuration. "
            "Generate a full audit report and send via telegram_send. "
            "Flag any items requiring operator action before the busy season."
        ),
    },
]


async def seed_wbm_tasks() -> dict:
    """Seed WBM hospitality scheduler tasks. Idempotent — skips existing tasks."""
    if not os.environ.get("WBM_TENANT_ID"):
        return {"status": "skipped", "reason": "WBM_TENANT_ID not configured"}

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

        for task_def in _WBM_TASKS:
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
            logger.info("[wbm-init] Seeded %s", task_def["name"])

        return {
            "status": "ok",
            "registered": registered,
            "skipped_existing": skipped,
            "total": len(_WBM_TASKS),
        }

    except Exception as e:
        logger.warning("[wbm-init] Failed to seed WBM tasks: %s", e)
        return {"status": "error", "reason": str(e)}
