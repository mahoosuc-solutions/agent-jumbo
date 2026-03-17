# E2E Testing Automation Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully automated E2E test suite (41 tests: 11 functional, 16 security, 11 performance, 3 accessibility) with CI integration and tiered gate logic.

**Architecture:** Playwright + aiohttp in a single pytest session against a live Flask server. Four test modules share one server and browser instance. Gate script reads JSON report and applies hard/soft/advisory blocks. CI runs on self-hosted runner.

**Tech Stack:** Playwright, pytest, aiohttp, axe-core (inline JS), psutil, pytest-json-report

**Spec:** `docs/superpowers/specs/2026-03-17-e2e-testing-automation-design.md`

---

## Chunk 1: Infrastructure

### Task 1: Register markers and add dev dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add pytest markers to pyproject.toml**

Add `security`, `performance`, and `a11y` markers to the existing `[tool.pytest.ini_options] markers` list. Also add `pytest-json-report>=1.5.0` to `[project.optional-dependencies] dev`.

- [ ] **Step 2: Install and verify**

Run `uv lock && uv sync --extra dev`, then `pytest --markers | grep -E "security|performance|a11y"` — all three should appear.

- [ ] **Step 3: Commit**

### Task 2: Create `/debug_metrics` API endpoint

**Files:**
- Create: `python/api/debug_metrics.py`

- [ ] **Step 1: Create the handler**

A GET endpoint guarded by `requires_auth + requires_loopback` that returns `{"rss_bytes", "cpu_percent", "open_files", "uptime_seconds"}` via `psutil.Process()`.

- [ ] **Step 2: Verify import**

`python -c "from python.api.debug_metrics import DebugMetrics; print('OK')"`

- [ ] **Step 3: Commit**

### Task 3: Enhance conftest.py

**Files:**
- Modify: `tests/e2e/conftest.py`

- [ ] **Step 1: Rewrite conftest**

Key additions over existing version:
- `upload_dir` fixture (session): temp directory for uploads, cleaned at teardown
- `auth_cookies` fixture (session): HTTP login to get session cookies for non-browser tests
- `warmup` fixture (session): 10 requests to trigger lazy imports before perf tests
- Keep existing: `app_server`, `browser`, `page`, `authenticated_page`, screenshot hook

- [ ] **Step 2: Create reports gitignore**

`mkdir -p tests/e2e/reports && echo '*.json' > tests/e2e/reports/.gitignore`

- [ ] **Step 3: Commit**

---

## Chunk 2: Functional Tests

### Task 4: Create consolidated functional test module

**Files:**
- Create: `tests/e2e/test_functional.py`
- Delete: 6 existing test files

- [ ] **Step 1: Write test_functional.py with 11 tests**

Tests: `test_login_valid_credentials`, `test_login_invalid_credentials`, `test_login_rate_limiting`, `test_protected_route_redirects`, `test_logout_invalidates_session`, `test_chat_send_message`, `test_chat_accessibility_attrs`, `test_upload_allowed_file`, `test_upload_blocked_file`, `test_settings_page_renders`, `test_sse_connection`.

All marked `@pytest.mark.e2e`. Use selectors: `#chat-input`, `#send-button`, `#file-input`. SSE test uses raw HTTP, not Playwright. Upload tests use `page.locator('#file-input').set_input_files()`.

- [ ] **Step 2: Delete old files**

`git rm tests/e2e/test_login_flow.py tests/e2e/test_logout.py tests/e2e/test_protected_routes.py tests/e2e/test_chat_interaction.py tests/e2e/test_file_upload.py tests/e2e/test_settings.py`

- [ ] **Step 3: Verify 11 tests collect**

- [ ] **Step 4: Commit**

---

## Chunk 3: Security Tests

### Task 5: Create security test module

**Files:**
- Create: `tests/e2e/test_security.py`

- [ ] **Step 1: Write 16 security tests**

All marked `@pytest.mark.security`. Use raw HTTP helpers (`_get`, `_post`) for protocol-level probes, Playwright for XSS.

Key implementation notes:
- `test_csp_no_unsafe_eval`: assert `unsafe-eval` not in CSP (CDN hosts and `unsafe-inline` are intentionally allowed)
- `test_session_cookie_flags`: target `session_*` cookie specifically (not `mcp_token_*`), verify via raw `Set-Cookie` header parsing with `http.client`
- `test_upload_magic_bytes`: expect HTTP 500 (current upload handler behavior), assert no traceback in response
- `test_cors_not_wildcard`: if `Access-Control-Allow-Origin` header present, must not be `*`; if absent, pass
- `test_csrf_token_required`: test against endpoints where `requires_csrf()` returns True
- `test_csrf_token_rotation`: use `http.cookiejar` to get token before/after login via `/csrf_token`
- Rate limit tests: loop POST requests until 429 or max attempts

- [ ] **Step 2: Verify 16 tests collect**

- [ ] **Step 3: Commit**

---

## Chunk 4: Performance and Accessibility Tests

### Task 6: Create performance test module

**Files:**
- Create: `tests/e2e/test_performance.py`

- [ ] **Step 1: Write 11 performance tests**

All marked `@pytest.mark.performance`. Use `time.monotonic()` for timing.

Key implementation notes:
- Page load tests use Playwright `page.goto` timing
- API SLA tests use raw HTTP with `_timed_get` helper
- `test_memory_no_leak`: depends on `warmup` fixture; GET `/debug_metrics` before/after 50 requests, assert < 50MB growth
- `test_concurrent_connections`: `asyncio.gather` with 10 `aiohttp.ClientSession.get("/health")`
- `test_lighthouse_score`: advisory — use Chrome DevTools `performance.getEntriesByType('navigation')` via `page.evaluate()`, rough heuristic scoring
- `test_sse_connection_time`: measures first-byte latency (will get `no_context` error in clean server — that's fine, we're testing transport)
- `test_settings_save_roundtrip`: soft — skip if settings API endpoint doesn't exist

- [ ] **Step 2: Verify 11 tests collect**

- [ ] **Step 3: Commit**

### Task 7: Create accessibility test module

**Files:**
- Create: `tests/e2e/test_accessibility.py`

- [ ] **Step 1: Write 3 accessibility tests**

All marked `@pytest.mark.a11y`. Mechanism: fetch axe-core JS from CDN (cached), inject via `page.evaluate()`, run `axe.run()` with WCAG 2.1 AA ruleset, save violations to `tests/e2e/reports/a11y-*.json`.

Assert: zero `critical` or `serious` violations. Report `moderate`/`minor` as warnings.

Pages tested: `/login`, `/chat` (authenticated), `/settings` (authenticated).

- [ ] **Step 2: Verify 3 tests collect**

- [ ] **Step 3: Commit**

---

## Chunk 5: CI Integration

### Task 8: Create gate script

**Files:**
- Create: `scripts/ci/e2e_gate.py`

- [ ] **Step 1: Write the gate script**

Reads pytest-json-report output, categorizes tests by marker, applies tiered logic:
- `security` + `e2e`: hard block (exit 1), never overridable
- `performance`: soft block (exit 1), overridable if `"force-merge"` in `--labels` arg
- `a11y`: advisory (exit 0 always), reports violations

Accepts `--labels` as JSON array (from `github.event.pull_request.labels.*.name`). On non-PR contexts (push, workflow_dispatch), labels are empty → no override available.

Prints PR-comment-friendly summary.

- [ ] **Step 2: Make executable, commit**

### Task 9: Add E2E job to CI workflow

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add e2e-tests job**

```yaml
e2e-tests:
  runs-on: self-hosted
  needs: [lint, test]
```

Steps: checkout, setup Python 3.12, install uv, `uv sync --extra dev`, `playwright install chromium`, run pytest with `--json-report`, run gate script with PR labels, upload artifacts.

- [ ] **Step 2: Fix security job**

Update the existing `security` job to use `uv export` instead of `pip-audit -r requirements.txt` (file was deleted in Wave 1).

- [ ] **Step 3: Commit**

### Task 10: Final verification

- [ ] **Step 1: Verify all 41 tests collect** (`--collect-only`)
- [ ] **Step 2: Run full E2E suite** (some may fail due to server startup — debug live)
- [ ] **Step 3: Test gate script** against the results JSON
- [ ] **Step 4: Verify existing 1799+ unit tests unaffected**
- [ ] **Step 5: Push**
