# RC Next Steps — Post-Merge Status

**Date:** 2026-03-15 (updated)
**Branch:** `main` (RC merged)
**Local tests:** 1767 passed, 0 failed, 6 skipped

---

## Priority 1: Fix CI (Blocking Merge) — DONE

All CI blockers resolved and merged to main:

- **pyproject.toml:** license `{text = "..."}` → SPDX string `"Apache-2.0"`, target-version py312 → py310
- **ruff:** 102 auto-fixes + 207 files reformatted, `ruff check .` and `ruff format --check .` both pass
- **pre-commit:** upgraded ruff v0.4.4 → v0.14.10, bandit/markdownlint properly configured
- **docs workflow:** fixed bash syntax error (`2>/dev/null` in for-loop → `shopt -s nullglob`)
- **tests:** fixed 5 failures (hardcoded paths, stale doc refs, registry isolation)
- **Local result:** 1767 passed, 0 failed, 6 skipped

### Docker backup dirs — DONE

Root-owned `docker/run-bak-*` and `docker/run-old-*` dirs removed.

---

## Priority 2: Go-Live Validation — DONE

MOS integration validated with real API keys. Linear/Motion/Notion sync pipeline confirmed working.

---

## Priority 3: UI Polish (Post-Validation)

### 3a. Sync progress feedback

- Add spinner/progress bar during sync operations in MOS dashboard
- Show "Syncing 12/45 issues..." status messages
- Disable sync buttons while sync is in progress

### 3b. Error state display

- Show clear error messages when API keys are invalid or expired
- Display per-platform connection status (green/yellow/red indicators)
- Add "Test Connection" button per platform in settings

### 3c. Sync history / audit log

- Show last 10 sync operations with timestamp, items synced, errors
- Add a "Sync History" tab to the MOS dashboard
- Include conflict resolution details (skipped duplicates, updated items)

### 3d. Real-time data refresh

- Auto-refresh dashboard data on configurable interval (default 60s)
- Show "Last updated: X minutes ago" timestamp
- WebSocket or polling-based live update for sync status

---

## Priority 4: Technical Debt — DONE

### 4a. Pre-commit config cleanup — DONE

- Bandit: replaced global `--skip B103,B108,B301,B310,B324,B507` with targeted `# nosec` comments
- Markdownlint: 17 → 5 disabled rules, moved from inline `--disable` args to `.markdownlintrc`
- Re-enabled 10 markdownlint rules with violations fixed across 105 files

### 4b. Secrets baseline maintenance

The `.secrets.baseline` was regenerated with 2037 lines. Many entries are legitimate false positives (example API keys in docs, test mock values). Review periodically:

- Audit entries for any real secrets that slipped through
- Add `pragma: allowlist secret` inline comments for documented false positives
- Remove baseline entries as files are cleaned up

### 4c. Test coverage gaps

Current MOS tests are all mocked. Consider adding:

- Integration tests that hit a local mock server (not real APIs)
- Rate limiter stress tests for Motion (verify 30 req/min cap under load)
- Orchestrator event ordering tests (verify sync sequence correctness)

---

## Quick Reference

| Task | Effort | Status |
| ---- | ------ | ------ |
| ~~Fix pyproject.toml license~~ | 5 min | DONE |
| ~~Fix CI ruff lint~~ | 10 min | DONE |
| ~~Fix docs check~~ | 15 min | DONE |
| ~~Fix test failures~~ | 20 min | DONE |
| ~~Remove docker backup dirs~~ | 2 min | DONE |
| ~~Linear go-live test~~ | 30 min | DONE |
| ~~Motion go-live test~~ | 30 min | DONE |
| ~~Notion go-live test~~ | 30 min | DONE |
| ~~Orchestrator event flow~~ | 20 min | DONE |
| ~~Pre-commit cleanup~~ | 2-3 hrs | DONE |
| UI polish (all items) | 2-4 hrs | Backlog |
