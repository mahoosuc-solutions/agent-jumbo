# Manual Smoke Record — 2026-04-05

- Environment: production Docker target `agent-jumbo-production`
- Base URL: `http://localhost:6274`
- Browser URL: `http://127.0.0.1:80`
- Tester: Codex
- Timezone: `America/New_York`

## Scope

This smoke record covers the current GA runtime, dashboard routing, trust UX, and persisted scheduler state after the scheduler persistence and work-context fixes.

## Runtime Checks

1. `GET /health`
   Result: passed
   Evidence:
   - `ok=true`
   - `status=healthy`

2. Scheduler persistence
   Result: passed
   Evidence:
   - `/aj/data/scheduler/tasks.json` present in the container
   - `scheduler_tasks_list` returned `29` tasks before restart
   - `scheduler_tasks_list` returned `29` tasks after restart

3. Dashboard and chat browser smoke
   Result: passed
   Evidence:
   - Work Queue heading: `Work Queue`
   - Workflows dashboard: `workflows`
   - Workflows stats: `23 / 14 / 22 / 2`
   - Tasks cards: `29`
   - Trust level cards: `4`
   - Trust posture items: `6`
   - New chat changed immediately and left `1` selected chat

## Notes

- This record reflects the validated production runtime after restart.
- Re-run in the final 72-hour launch window for the final GA decision packet.
