# Manual Smoke Record — 2026-03-24

- Environment: local Docker target `agent-jumbo`
- Base URL: `http://localhost:50080`
- Tester: Codex
- Timezone: `America/New_York`

## Scope

This smoke record covers the current core GA runtime plus the newly integrated beta slice for ideas and projects.

## Live Runtime Checks

1. `GET /health`
   Result: passed
   Evidence:
   - `ok=true`
   - `status=healthy`
   - runtime metrics present under `checks.runtime_metrics`

2. `GET /chat_readiness`
   Result: passed
   Evidence:
   - `ready=true`
   - provider `google`
   - model `gemini-2.5-flash`
   - backend `native`

3. Chat create/message/poll roundtrip
   Result: passed
   Evidence:
   - created context `Z7lYS6yw`
   - `message_async` returned `ok=true`
   - poll settled with `log_progress_active=false`
   - final `log_version=54`
   - completed on poll attempt `12`

## Beta Slice Checks

1. Ideas backend/API coverage
   Result: passed
   Command:
   - `python3.11 -m pytest tests/test_ideas_manager.py tests/test_ideas_api.py -q`

2. Ideas to project/workflow/queue promotion coverage
   Result: passed
   Evidence:
   - promotion tests create a project
   - starter workflow created
   - three queue items seeded for promoted idea

3. Projects and navigation build safety
   Result: passed
   Command:
   - `npm run type-check` in `web/`

## Notes

- Ideas, Projects, and idea promotion remain classified as `beta` in the launch inventory.
- This record is local evidence. Re-run within the final 72-hour launch window for GA decision use.
