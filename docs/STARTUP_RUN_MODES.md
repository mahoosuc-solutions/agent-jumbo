# Startup Criticality And Run Modes

## Startup-Critical Subsystems

These should determine whether HTTP readiness is true.

- web server route registration
- core settings/config load
- auth/session wiring
- request handling for `/`, `/poll`, and `/health`

If these are healthy, the UI can come up.

## Optional Or Background Subsystems

These should not block readiness.

- chat history restore
- MCP client initialization
- job loop / scheduler runtime
- preload tasks
- messaging gateway adapters
- AgentMesh bridge
- local search extras such as `SearXNG`

These should surface status, not hold the server hostage.

## Current Run Modes

The runtime now recognizes:

- `full`
  Everything allowed to initialize.
- `local-lite`
  Local development mode. Equivalent to the old laptop-mode behavior.
- `research`
  Browser/search-heavy work without the full operational stack. Startup-managed operational services are skipped.

Current source of truth:

- env var: `AGENT_MAHOO_RUN_MODE`
- fallback legacy flag: `AGENT_MAHOO_LAPTOP_MODE=true` maps to `local-lite`
- helper: `python/helpers/runtime_mode.py`
- status surface: `/health` and `/poll`

## Current Explicit Skip Path

MOS schedules remain disabled by design for now because the current scheduler is model-based and the old MOS bootstrap expected callback registration.

Current behavior:

- `python/helpers/mos_scheduler_init.py` returns a structured `skipped_reason`
- `initialize.py` logs that skip explicitly during boot

This is intentionally explicit, not silent.

## Path Forward For Schedules

When we re-enable MOS schedules, use the persisted scheduler path rather than reintroducing the old callback API.

Target direction:

1. create persisted scheduled tasks with the current scheduler models
2. register them idempotently on startup or via migration/setup command
3. surface their enabled/disabled state in diagnostics

## UI Status Principle

The UI should distinguish:

- backend is ready
- optional background work is still running

That is why chat restore now has a separate startup status instead of being folded into readiness.
