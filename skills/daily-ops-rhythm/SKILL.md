---
name: daily-ops-rhythm
version: 1.0.0
author: agent-mahoo
tier: 1
trust_level: local
categories:
  - operations
  - messaging
  - scheduling
capabilities:
  - message-formatting
  - priority-ranking
  - digest-deduplication
  - skip-silently
description: Standard Telegram message formatting, priority ranking, skip-silently pattern, and digest deduplication for daily automated operations.
---

# Daily Operations Rhythm

## Purpose

Define consistent patterns for how automated tasks communicate via Telegram, prioritize information, and avoid notification fatigue.

## Telegram message formatting

### Standard digest format

```text
[icon] TITLE — date

Section 1:
- Item with key detail
- Item with key detail

Section 2:
- Item with key detail
```

### Icons by category

| Category | Icon |
|----------|------|
| Property ops | house |
| Calendar | calendar |
| Finance | chart |
| Client/project | clipboard |
| Alert/urgent | warning |
| Success/complete | checkmark |
| BizDev/pipeline | handshake |

### Rules

- Lead with the most actionable item
- Use bullet points, never paragraphs
- Include counts: "3 check-ins, 2 check-outs" not "several check-ins"
- Timestamps in 12h format with timezone: "2:30 PM ET"
- Currency always with dollar sign and two decimals: "$1,234.56"
- Keep total message under 30 lines — operator scans on mobile

## Priority ranking

Rank items by urgency x impact:

| Urgency | Impact | Priority | Action |
|---------|--------|----------|--------|
| Today | Revenue | P0 | Always send |
| Today | Operations | P0 | Always send |
| This week | Revenue | P1 | Send in digest |
| Today | Informational | P1 | Send in digest |
| This week | Operations | P2 | Send if anomaly |
| Future | Informational | P2 | Weekly rollup only |

## Skip-silently pattern

Many scheduled tasks should NOT send a message when there's nothing to report. This prevents notification fatigue.

### When to skip silently

- No new bookings in the check window
- No upcoming deadlines
- No overdue issues
- All metrics within normal range
- No guests in mid-stay check-in window
- No outstanding proposals to follow up

### When to always send (never skip)

- Morning briefing (daily rhythm anchor)
- End-of-day status (closure signal)
- Weekly reports (periodic rhythm)
- Monday pipeline review (planning anchor)
- Any error or health check failure

### Implementation

Task prompts should include: "If no [items] found, skip silently — do not send any message."

## Digest deduplication

When multiple tasks run at similar times, avoid reporting the same information twice.

### Rules

- Morning briefing owns the "overview" — individual task reports should add detail, not repeat the summary
- If a check-in was mentioned in the morning briefing, the pre-arrival message task should reference "as noted in briefing" not re-list the details
- Weekly reports supersede daily reports for the same data — don't repeat Monday-Friday daily items in Friday's weekly
- EOD status should only cover changes since the morning standup, not re-report morning items

## Scheduling rhythm

The daily schedule is designed around the operator's day:

- 6:00-7:00: System checks, PMS scan (before operator is active)
- 7:00-7:30: Morning briefing and guest messages (operator's first look)
- 8:00-9:00: Work-related standup and cleaning dispatch
- 9:00-10:00: Deadlines and follow-ups
- 12:00: Midday triage (only if urgent)
- 14:00: Guest mid-stay (afternoon warmth)
- 17:00-17:30: EOD status and metrics
- 18:00: Reservation monitor
- 20:00-21:00: Tomorrow prep and review requests (evening wind-down)

Weekend tasks run at reduced frequency — property ops continue, client work pauses.
