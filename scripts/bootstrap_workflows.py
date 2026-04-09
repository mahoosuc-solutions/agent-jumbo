"""
Bootstrap 26 scheduled workflow tasks for Agent Mahoo's daily operating system.

Usage:
    python scripts/bootstrap_workflows.py

Idempotent — skips tasks that already exist (matched by name).
"""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.helpers.task_scheduler import ScheduledTask, TaskSchedule, TaskScheduler

# ---------------------------------------------------------------------------
# Task definitions grouped by priority
# ---------------------------------------------------------------------------

TASKS = [
    # ======================================================================
    # P0 — Critical daily operations
    # ======================================================================
    {
        "name": "pms-checkin-checkout-scan",
        "schedule": TaskSchedule(minute="45", hour="6", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a hospitality operations assistant for a vacation rental business. "
            "You have access to the PMS via pms_hub_tool. Your job is to scan today's "
            "check-ins and check-outs and produce a concise operational summary."
        ),
        "prompt": (
            "Scan today's reservations using pms_hub_tool.\n\n"
            "1. List all CHECK-INS today with guest name, property, arrival time, and any special requests.\n"
            "2. List all CHECK-OUTS today with guest name, property, and departure time.\n"
            "3. Flag any overlaps where a check-out and check-in happen at the same property today (turnover alert).\n\n"
            "Format as a clean Telegram message and send via telegram_send to the operator channel."
        ),
    },
    {
        "name": "pms-pre-arrival-messages",
        "schedule": TaskSchedule(minute="15", hour="7", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a guest communications specialist for a vacation rental business. "
            "You draft warm, professional pre-arrival messages for guests checking in today. "
            "All messages require operator approval before sending."
        ),
        "prompt": (
            "Using pms_hub_tool, find all guests checking in today.\n\n"
            "For each guest, draft a personalized pre-arrival message that includes:\n"
            "- Warm greeting using their first name\n"
            "- Check-in time and property address\n"
            "- Key access instructions (from property notes)\n"
            "- Local weather forecast mention\n"
            "- Invitation to reach out with questions\n\n"
            "Send each draft to Telegram via telegram_send with prefix '[APPROVE] Pre-arrival for {guest_name}:' "
            "so the operator can review and approve before it goes to the guest.\n"
            "If no check-ins today, skip silently — do not send a message."
        ),
    },
    {
        "name": "pms-cleaning-dispatch",
        "schedule": TaskSchedule(minute="0", hour="9", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a cleaning operations coordinator for a vacation rental business. "
            "You prioritize and dispatch cleaning tasks based on today's turnover schedule."
        ),
        "prompt": (
            "Using pms_hub_tool, identify all properties that need cleaning today.\n\n"
            "Priority rules:\n"
            "- URGENT: Same-day turnover (check-out + check-in same day) — must be cleaned first\n"
            "- HIGH: Check-out today, check-in tomorrow\n"
            "- NORMAL: Check-out today, no upcoming check-in within 48h\n\n"
            "Create a prioritized cleaning task list with property name, priority level, "
            "check-out time, and next check-in time.\n\n"
            "Send via telegram_send to the operator channel.\n"
            "If no cleanings needed today, skip silently."
        ),
    },
    {
        "name": "pms-new-booking-alert",
        "schedule": TaskSchedule(minute="*/15", hour="8-22", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a booking notification assistant. You check for new reservations "
            "and alert the operator immediately when new bookings come in."
        ),
        "prompt": (
            "Using pms_hub_tool, check for any new bookings created in the last 15 minutes.\n\n"
            "For each new booking, send a Telegram alert via telegram_send with:\n"
            "- Guest name\n"
            "- Property name\n"
            "- Check-in and check-out dates\n"
            "- Total amount\n"
            "- Booking source (direct, Airbnb, VRBO, etc.)\n\n"
            "If no new bookings, skip silently — do not send any message."
        ),
    },
    {
        "name": "personal-morning-briefing",
        "schedule": TaskSchedule(minute="0", hour="7", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a personal executive assistant providing a concise morning briefing. "
            "You synthesize information from multiple sources into a single actionable digest."
        ),
        "prompt": (
            "Compile the morning briefing by gathering data from these sources:\n\n"
            "1. calendar_hub: Today's meetings and events with times\n"
            "2. finance_manager: Quick cash position and any notable transactions\n"
            "3. pms_hub_tool: Property occupancy snapshot (X of Y units occupied)\n"
            "4. linear_integration: Any overdue or due-today issues\n"
            "5. life_os: Today's priority items if any are set\n\n"
            "Format as a clean morning briefing with sections, sent via telegram_send.\n"
            "Keep it scannable — bullet points, no paragraphs. Under 30 lines."
        ),
    },
    {
        "name": "client-morning-standup",
        "schedule": TaskSchedule(minute="0", hour="8", day="*", month="*", weekday="1-5"),
        "system_prompt": (
            "You are a project management assistant that produces a daily standup digest "
            "from Linear issue tracker data. Focus on what matters: blockers, due items, "
            "and progress since yesterday."
        ),
        "prompt": (
            "Using linear_integration, compile a weekday standup digest:\n\n"
            "1. BLOCKERS: Any issues marked as blocked or with blocker labels\n"
            "2. DUE TODAY: Issues with today's due date\n"
            "3. IN PROGRESS: Issues moved to 'In Progress' status\n"
            "4. COMPLETED YESTERDAY: Issues closed since yesterday\n\n"
            "Group by project/team. Send via telegram_send.\n"
            "If nothing notable, send a brief 'All clear — no blockers, N issues in progress' message."
        ),
    },
    {
        "name": "client-deadline-reminder",
        "schedule": TaskSchedule(minute="0", hour="9", day="*", month="*", weekday="1-5"),
        "system_prompt": (
            "You are a deadline tracking assistant. You monitor upcoming deadlines "
            "and send proactive reminders before things become overdue."
        ),
        "prompt": (
            "Using linear_integration, check for issues with due dates in the next 3 business days.\n\n"
            "Group by urgency:\n"
            "- OVERDUE: Past due date\n"
            "- DUE TODAY: Due today\n"
            "- DUE TOMORROW: Due tomorrow\n"
            "- DUE THIS WEEK: Due within 3 business days\n\n"
            "Send via telegram_send only if there are items to report.\n"
            "If no upcoming deadlines, skip silently."
        ),
    },
    # ======================================================================
    # P1 — Important but not time-critical
    # ======================================================================
    {
        "name": "pms-guest-midstay-checkin",
        "schedule": TaskSchedule(minute="0", hour="14", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a guest experience specialist. You draft friendly mid-stay check-in "
            "messages for guests who are 1-2 days into their stay. Messages require approval."
        ),
        "prompt": (
            "Using pms_hub_tool, find guests who checked in yesterday or the day before "
            "(1-2 days into their stay).\n\n"
            "For each guest, draft a brief, warm mid-stay check-in message:\n"
            "- Ask if everything is going well\n"
            "- Mention one local recommendation relevant to the season\n"
            "- Remind them you're available if they need anything\n\n"
            "Send each draft to Telegram via telegram_send with prefix "
            "'[APPROVE] Mid-stay check-in for {guest_name}:'\n"
            "If no mid-stay guests, skip silently."
        ),
    },
    {
        "name": "pms-review-solicitation",
        "schedule": TaskSchedule(minute="0", hour="21", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a guest review specialist. You draft review solicitation messages "
            "for guests who checked out today. Keep it genuine, not pushy. Requires approval."
        ),
        "prompt": (
            "Using pms_hub_tool, find guests who checked out today.\n\n"
            "For each guest, draft a review request message:\n"
            "- Thank them warmly for their stay\n"
            "- Reference the specific property by name\n"
            "- Ask if they'd be willing to share their experience\n"
            "- Include the review link if available from PMS\n"
            "- Keep tone genuine and brief (3-4 sentences max)\n\n"
            "Send each draft to Telegram via telegram_send with prefix "
            "'[APPROVE] Review request for {guest_name}:'\n"
            "If no check-outs today, skip silently."
        ),
    },
    {
        "name": "pms-reservation-monitor",
        "schedule": TaskSchedule(minute="0", hour="18", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a reservations analyst. You monitor upcoming reservations for the next "
            "48 hours and flag any issues: missing guest info, unconfirmed bookings, or gaps."
        ),
        "prompt": (
            "Using pms_hub_tool, review all reservations for the next 48 hours.\n\n"
            "Flag issues:\n"
            "- Missing guest contact info\n"
            "- Unconfirmed or pending payment bookings\n"
            "- Back-to-back turnovers with less than 4 hours between checkout and checkin\n"
            "- Properties with no bookings (gap opportunities)\n\n"
            "Send via telegram_send only if issues are found.\n"
            "If everything looks clean, skip silently."
        ),
    },
    {
        "name": "efficiency-automation-health",
        "schedule": TaskSchedule(minute="0", hour="6", day="*", month="*", weekday="1"),
        "system_prompt": (
            "You are a systems reliability engineer. You check the health of all "
            "automation systems and report any issues found."
        ),
        "prompt": (
            "Run a weekly automation health check:\n\n"
            "1. Check scheduler task states — list any tasks in ERROR state\n"
            "2. Review last_run timestamps — flag tasks that haven't run in over 7 days\n"
            "3. Check Telegram webhook connectivity\n"
            "4. Verify PMS API connectivity via pms_hub_tool (simple query)\n"
            "5. Check calendar_hub connectivity\n\n"
            "Send a health report via telegram_send with status indicators.\n"
            "Use checkmarks for healthy, warning signs for degraded, X for failed."
        ),
    },
    {
        "name": "client-midday-triage",
        "schedule": TaskSchedule(minute="0", hour="12", day="*", month="*", weekday="1-5"),
        "system_prompt": (
            "You are a project triage assistant. You scan for urgent issues that "
            "need attention and escalate only what matters."
        ),
        "prompt": (
            "Using linear_integration, scan for issues that need midday attention:\n\n"
            "1. Any issues marked urgent or critical that are unassigned\n"
            "2. Issues where someone requested review and it's been >4 hours\n"
            "3. New issues created today that haven't been triaged\n\n"
            "Send via telegram_send only if urgent items found.\n"
            "If nothing urgent, skip silently."
        ),
    },
    {
        "name": "client-eod-status",
        "schedule": TaskSchedule(minute="0", hour="17", day="*", month="*", weekday="1-5"),
        "system_prompt": (
            "You are a project status reporter. You compile end-of-day progress "
            "summaries across all active client projects."
        ),
        "prompt": (
            "Using linear_integration, compile an end-of-day status report:\n\n"
            "1. Issues completed today (count and list)\n"
            "2. Issues still in progress\n"
            "3. Any new blockers surfaced during the day\n"
            "4. Tomorrow's priority items\n\n"
            "Send via telegram_send. Keep it concise — this is a quick pulse check."
        ),
    },
    {
        "name": "client-weekly-report",
        "schedule": TaskSchedule(minute="0", hour="16", day="*", month="*", weekday="5"),
        "system_prompt": (
            "You are a project reporting specialist. You compile comprehensive weekly "
            "progress reports for client projects."
        ),
        "prompt": (
            "Using linear_integration, compile a Friday weekly report:\n\n"
            "1. SUMMARY: One-paragraph overview of the week\n"
            "2. COMPLETED: All issues closed this week, grouped by project\n"
            "3. IN PROGRESS: Carry-over items with status notes\n"
            "4. BLOCKERS: Anything stalled and why\n"
            "5. NEXT WEEK: Top priorities for next week\n\n"
            "Send via telegram_send.\n"
            "Also send a formatted version via email to the operator's email."
        ),
    },
    {
        "name": "personal-calendar-prep",
        "schedule": TaskSchedule(minute="0", hour="20", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a calendar preparation assistant. You review tomorrow's schedule "
            "and prepare the operator for the next day."
        ),
        "prompt": (
            "Using calendar_hub, review tomorrow's calendar:\n\n"
            "1. List all meetings/events with times and attendees\n"
            "2. Flag any back-to-back meetings (no buffer)\n"
            "3. Note any prep needed (documents to review, topics to prepare)\n"
            "4. Identify free blocks for deep work\n\n"
            "Send via telegram_send as 'Tomorrow's Schedule' message."
        ),
    },
    {
        "name": "personal-weekly-finance",
        "schedule": TaskSchedule(minute="0", hour="17", day="*", month="*", weekday="5"),
        "system_prompt": (
            "You are a financial reporting assistant. You provide weekly financial "
            "summaries across all business operations."
        ),
        "prompt": (
            "Using finance_manager, compile a Friday financial summary:\n\n"
            "1. Week's revenue (property income, client billing)\n"
            "2. Week's expenses (notable outflows)\n"
            "3. Cash position across accounts\n"
            "4. Outstanding invoices / receivables\n"
            "5. Any anomalies or items needing attention\n\n"
            "Send via telegram_send."
        ),
    },
    {
        "name": "bizdev-lead-followup",
        "schedule": TaskSchedule(minute="0", hour="10", day="*", month="*", weekday="1-5"),
        "system_prompt": (
            "You are a business development assistant. You track leads and ensure "
            "timely follow-ups so nothing falls through the cracks."
        ),
        "prompt": (
            "Using customer_lifecycle, check for leads or prospects needing follow-up:\n\n"
            "1. Leads with no activity in the last 3 business days\n"
            "2. Proposals sent but not responded to (>48h)\n"
            "3. Meetings scheduled this week that need prep\n\n"
            "Send via telegram_send with suggested follow-up actions.\n"
            "If no follow-ups needed, skip silently."
        ),
    },
    {
        "name": "bizdev-weekly-pipeline",
        "schedule": TaskSchedule(minute="30", hour="7", day="*", month="*", weekday="1"),
        "system_prompt": (
            "You are a sales pipeline analyst. You provide a Monday morning overview "
            "of the business development pipeline."
        ),
        "prompt": (
            "Using customer_lifecycle, compile a Monday pipeline review:\n\n"
            "1. PIPELINE SUMMARY: Total deals by stage (lead, qualified, proposal, negotiation, closed)\n"
            "2. THIS WEEK'S PRIORITIES: Deals most likely to close or needing attention\n"
            "3. STALE DEALS: Anything stuck in the same stage for >2 weeks\n"
            "4. NEW LEADS: Leads added last week\n"
            "5. REVENUE FORECAST: Expected close value this month\n\n"
            "Send via telegram_send."
        ),
    },
    # ======================================================================
    # P2 — Nice-to-have, optimization
    # ======================================================================
    {
        "name": "pms-monthly-revenue",
        "schedule": TaskSchedule(minute="0", hour="9", day="1", month="*", weekday="*"),
        "system_prompt": (
            "You are a property revenue analyst. You compile monthly revenue reports for the vacation rental portfolio."
        ),
        "prompt": (
            "Using pms_hub_tool and finance_manager, compile last month's revenue report:\n\n"
            "1. Total revenue by property\n"
            "2. Occupancy rate by property\n"
            "3. Average daily rate (ADR) by property\n"
            "4. Revenue per available night (RevPAN)\n"
            "5. Month-over-month comparison if data available\n"
            "6. Top-performing and underperforming properties\n\n"
            "Send via telegram_send."
        ),
    },
    {
        "name": "personal-daily-metrics",
        "schedule": TaskSchedule(minute="30", hour="17", day="*", month="*", weekday="*"),
        "system_prompt": (
            "You are a metrics analyst. You compile a daily snapshot of key business metrics and flag anomalies."
        ),
        "prompt": (
            "Compile daily metrics snapshot:\n\n"
            "1. Property occupancy rate (today vs 7-day avg)\n"
            "2. Open Linear issues count (vs yesterday)\n"
            "3. Revenue collected today\n"
            "4. Any significant deviations from normal patterns\n\n"
            "Use pms_hub_tool, linear_integration, and finance_manager.\n\n"
            "Send via telegram_send only if there's an anomaly (>20% deviation from average).\n"
            "If all metrics normal, skip silently."
        ),
    },
    {
        "name": "personal-week-planning",
        "schedule": TaskSchedule(minute="0", hour="19", day="*", month="*", weekday="0"),
        "system_prompt": (
            "You are a weekly planning assistant. You help prepare for the upcoming "
            "week by reviewing commitments and suggesting priorities."
        ),
        "prompt": (
            "Compile a Sunday week-ahead plan:\n\n"
            "1. calendar_hub: Next week's meetings and commitments\n"
            "2. pms_hub_tool: Expected check-ins/check-outs next week\n"
            "3. linear_integration: Sprint goals and key deliverables\n"
            "4. customer_lifecycle: Pipeline items needing attention\n"
            "5. Suggested top-3 priorities for the week\n\n"
            "Send via telegram_send."
        ),
    },
    {
        "name": "bizdev-proposal-followup",
        "schedule": TaskSchedule(minute="0", hour="10", day="*", month="*", weekday="3"),
        "system_prompt": (
            "You are a proposal follow-up specialist. You draft follow-up messages "
            "for outstanding proposals. Messages require approval before sending."
        ),
        "prompt": (
            "Using customer_lifecycle, find proposals that have been sent but not responded to.\n\n"
            "For each outstanding proposal (>3 days since sent):\n"
            "- Draft a brief, professional follow-up message\n"
            "- Reference the specific proposal and its key value proposition\n"
            "- Include a soft call-to-action\n\n"
            "Send each draft to Telegram via telegram_send with prefix "
            "'[APPROVE] Proposal follow-up for {client_name}:'\n"
            "If no outstanding proposals, skip silently."
        ),
    },
    {
        "name": "bizdev-content-scanner",
        "schedule": TaskSchedule(minute="0", hour="9", day="*", month="*", weekday="1"),
        "system_prompt": (
            "You are a content and market intelligence scanner. You identify relevant "
            "opportunities and trends from business communications and market signals."
        ),
        "prompt": (
            "Monday content scan:\n\n"
            "1. Review recent email threads (via email) for any inbound inquiries or opportunities\n"
            "2. Check customer_lifecycle for any client feedback or expansion signals\n"
            "3. Identify any content creation opportunities (case studies, blog posts) from recent wins\n\n"
            "Send findings via telegram_send as an interactive list — the operator can reply "
            "to indicate which items to pursue.\n"
            "If nothing notable found, send a brief 'No new opportunities this week' message."
        ),
    },
    {
        "name": "efficiency-process-scan",
        "schedule": TaskSchedule(minute="0", hour="8", day="*", month="*", weekday="1"),
        "system_prompt": (
            "You are a process improvement analyst. You identify workflow bottlenecks "
            "and suggest efficiency improvements."
        ),
        "prompt": (
            "Monday process efficiency scan:\n\n"
            "1. Review scheduler task results from last week — any repeated errors?\n"
            "2. Check for tasks that consistently produce no output (candidates for schedule adjustment)\n"
            "3. Identify any manual steps that could be automated\n"
            "4. Note any tasks that take unusually long\n\n"
            "Send recommendations via telegram_send."
        ),
    },
    {
        "name": "efficiency-cost-analysis",
        "schedule": TaskSchedule(minute="0", hour="9", day="1", month="*", weekday="*"),
        "system_prompt": (
            "You are a cost optimization analyst. You review operational costs and identify savings opportunities."
        ),
        "prompt": (
            "Monthly cost analysis:\n\n"
            "Using finance_manager:\n"
            "1. Total operational costs by category (property, tech, marketing, admin)\n"
            "2. Cost per booking / cost per occupied night\n"
            "3. Month-over-month cost trends\n"
            "4. Top 5 expense items\n"
            "5. Savings recommendations\n\n"
            "Send via telegram_send."
        ),
    },
    {
        "name": "efficiency-agent-performance",
        "schedule": TaskSchedule(minute="0", hour="9", day="*", month="*", weekday="5"),
        "system_prompt": (
            "You are an AI operations analyst. You review the performance and effectiveness "
            "of the automated agent system itself."
        ),
        "prompt": (
            "Friday agent performance review:\n\n"
            "1. Scheduler task execution stats this week (success/error/skip counts)\n"
            "2. Average task execution time\n"
            "3. Most common error types\n"
            "4. Tasks with highest skip rate (candidates for schedule adjustment)\n"
            "5. Approval-required tasks: approval rate and response time\n\n"
            "Send via telegram_send."
        ),
    },
]


async def main():
    scheduler = TaskScheduler.get()
    await scheduler.reload()

    created = 0
    skipped = 0

    for task_def in TASKS:
        name = task_def["name"]

        # Idempotent: skip if already exists
        existing = scheduler.get_task_by_name(name)
        if existing:
            print(f"  SKIP  {name} (already exists)")
            skipped += 1
            continue

        task = ScheduledTask.create(
            name=name,
            system_prompt=task_def["system_prompt"],
            prompt=task_def["prompt"],
            schedule=task_def["schedule"],
        )
        await scheduler.add_task(task)
        print(f"  ADD   {name}")
        created += 1

    print(f"\nDone: {created} created, {skipped} skipped, {created + skipped} total")


if __name__ == "__main__":
    asyncio.run(main())
