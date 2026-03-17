# E2E Testing Automation Design

**Date:** 2026-03-17
**Status:** Approved
**Goal:** Fully automated E2E test suite covering functional, security, performance, and accessibility — integrated into CI/CD with tiered gate logic.

## Context

The project has 1800+ unit tests but E2E coverage is fragmented: 6 small test files with selector mismatches, no CI integration, no security probes against a live server, no performance baselines, no accessibility audits. The pre-existing E2E tests use Playwright but are not wired into any pipeline.

## Approach

**Single tool:** Playwright for functional, security (browser-context), and accessibility tests. Raw HTTP via `aiohttp` for protocol-level security probes, performance timing, and concurrency tests. Everything runs in one `pytest` invocation.

**CI target:** Self-hosted runner first, designed to move to GitHub Actions later (only `runs-on:` changes). Runner prerequisites: Python 3.12, uv, Node.js, Chromium.

**Gate tiers:**
- Security + Functional: hard block, never overridable
- Performance: soft block (20% tolerance), overridable with `[force-merge]` label
- Accessibility: advisory, reported in PR comment

## Test Architecture

```
tests/e2e/
├── conftest.py              # Server lifecycle, browser, auth fixtures, gate reporting
├── test_functional.py       # Login, chat, upload, settings, logout, SSE
├── test_security.py         # OWASP probes against live server
├── test_performance.py      # SLAs, memory, concurrency
├── test_accessibility.py    # axe-core WCAG 2.1 AA audit
├── pages/                   # Page object models (existing)
│   ├── login_page.py
│   ├── chat_page.py
│   └── settings_page.py
└── reports/                 # Generated: a11y violations, perf timings
```

**Server lifecycle:** One Flask server per session. Conftest spawns `run_ui.py` with `AUTH_LOGIN=testuser`, `AUTH_PASSWORD=testpass`, dynamic port. 90-second startup timeout. Conftest also sets `TMPDIR` for uploads to an isolated temp directory cleaned up at session teardown.

**Browser lifecycle:** One headless Chromium per session, fresh page per test. Screenshot on failure to `tests/e2e/screenshots/`.

**Marker registration:** Add `security`, `performance`, and `a11y` markers to `pyproject.toml [tool.pytest.ini_options] markers` alongside the existing `e2e` marker.

## Functional Tests (`test_functional.py`)

Consolidates existing 6 test files into one module. Markers: `@pytest.mark.e2e`.

| Test | Validates |
|------|-----------|
| `test_login_valid_credentials` | POST login redirects to app, session cookie set |
| `test_login_invalid_credentials` | Wrong password stays on login page, error shown |
| `test_login_rate_limiting` | 6+ POST attempts returns 429 |
| `test_protected_route_redirects` | `/chat`, `/settings` without auth redirect to `/login` |
| `test_logout_invalidates_session` | `/logout` then protected route requires re-auth |
| `test_chat_send_message` | Fill `#chat-input`, click `#send-button`, message appears |
| `test_chat_accessibility_attrs` | `role="log"`, `aria-live="polite"`, `aria-label` on chat container |
| `test_upload_allowed_file` | Upload .txt via `#file-input` succeeds |
| `test_upload_blocked_file` | Upload .exe rejected (expect HTTP 500 with `{"error": "Internal server error"}`) |
| `test_settings_page_renders` | `/settings` has content and section headings |
| `test_sse_connection` | GET `/sse` returns `text/event-stream` Content-Type and `data:` lines (note: without active chat context, response will be `{"error": "no_context"}` — test validates transport, not content) |

SSE test uses raw HTTP (not Playwright) since SSE is server-side streaming.

**Upload cleanup:** Conftest sets a session-scoped `tmp/upload/` under a temp directory. Session teardown removes it.

## Security Tests (`test_security.py` — E2E)

OWASP-style probes against the live server. Markers: `@pytest.mark.security`. Gate: **hard block, never overridable**.

| Test | Category | Method | Validates |
|------|----------|--------|-----------|
| `test_security_headers_present` | Headers | HTTP | CSP, X-Frame-Options, HSTS, X-XSS-Protection, X-Content-Type-Options all present |
| `test_csp_no_unsafe_eval` | Headers | HTTP | No `unsafe-eval` in CSP (note: `unsafe-inline` is intentionally present for Alpine.js; CDN hosts like `cdn.jsdelivr.net` are intentionally whitelisted) |
| `test_csrf_token_required` | CSRF | HTTP | POST without `X-CSRF-Token` returns 403 (on endpoints where `requires_csrf()` returns True — i.e., when auth is enabled) |
| `test_csrf_token_rotation` | CSRF | HTTP | Token changes after login |
| `test_session_cookie_flags` | Session | HTTP | `session_*` cookie (not `mcp_token_*`) has HttpOnly and SameSite=Strict. Target the cookie whose name starts with `session_`. |
| `test_session_invalidated_on_logout` | Session | HTTP | Session cookie rejected after `/logout` |
| `test_error_no_stack_trace` | Errors | HTTP | 500 response has `request_id`, no traceback |
| `test_error_404_sanitized` | Errors | HTTP | Clean 404, no path disclosure |
| `test_sql_injection_chat` | Injection | HTTP | `'; DROP TABLE--` treated as text, no DB error |
| `test_xss_payload_chat` | Injection | Playwright | `<script>alert(1)</script>` rendered escaped, no execution |
| `test_path_traversal_upload` | Traversal | HTTP | `../../etc/passwd` filename rejected or sanitized |
| `test_upload_magic_bytes` | Upload | HTTP | .exe renamed to .png → HTTP 500 with generic error (current upload handler raises Exception, which api.py catches and returns 500 with sanitized message). Assert: status 500, response contains `"error"`, response does NOT contain a Python traceback. |
| `test_rate_limit_login` | DoS | HTTP | 6 rapid POSTs to `/login` returns 429 |
| `test_rate_limit_upload` | DoS | HTTP | 11 rapid uploads returns 429 |
| `test_cors_not_wildcard` | CORS | HTTP | If `Access-Control-Allow-Origin` header is present, it must not be `*`. If absent, test passes (server currently does not set CORS headers — this test guards against future regressions). |
| `test_request_id_present` | Observability | HTTP | Every response has `X-Request-ID` header |

## Performance Tests (`test_performance.py`)

Concrete SLAs measured against the live server. Markers: `@pytest.mark.performance`. Gate: **soft block** (20% tolerance, overridable with `[force-merge]`).

### SLA Tests

| Test | SLA | Method |
|------|-----|--------|
| `test_login_page_load` | < 2s | Playwright `page.goto` timing |
| `test_spa_index_load` | < 3s | Playwright `page.goto` timing (authenticated) |
| `test_static_asset_response` | < 500ms | HTTP GET for CSS/JS |
| `test_health_endpoint` | < 200ms | HTTP GET `/health` |
| `test_chat_api_response` | < 1s | HTTP POST `/message` (short message) |
| `test_upload_1mb` | < 3s | HTTP POST `/upload` with 1MB .txt |
| `test_sse_connection_time` | < 2s | HTTP GET `/sse` time to first `data:` line (measures first-byte latency; in clean test server this delivers a `no_context` error immediately, which is fine — we're measuring transport latency, not business logic) |
| `test_settings_save_roundtrip` | < 1s | HTTP POST settings, GET verify |

### Resource Tests

| Test | SLA | Method |
|------|-----|--------|
| `test_memory_no_leak` | < 50MB growth over 50 requests | Warmup phase: 10 requests to `/health` and `/` to trigger lazy imports. Then GET `/debug_metrics` for baseline `rss_bytes`. Then 50 requests to various endpoints. Then GET `/debug_metrics` for final `rss_bytes`. Assert delta < 50MB. |
| `test_concurrent_connections` | 10 simultaneous, 0 errors | `asyncio.gather` with 10 `aiohttp` GET `/health` |

### Lighthouse (Advisory)

| Test | Target | Method |
|------|--------|--------|
| `test_lighthouse_score` | Performance > 70 | Chrome DevTools Protocol performance metrics via Playwright |

**Total: 11 performance tests.** All marked `@pytest.mark.performance`.

## Accessibility Tests (`test_accessibility.py`)

WCAG 2.1 AA audits via axe-core injected through Playwright. Markers: `@pytest.mark.a11y`. Gate: **advisory** (reported, never blocks).

| Test | Page | Validates |
|------|------|-----------|
| `test_a11y_login_page` | `/login` | Form labels, focus order, color contrast, button names |
| `test_a11y_chat_page` | `/` (authenticated) | Chat landmarks, input labels, send button |
| `test_a11y_settings_page` | `/settings` (authenticated) | Form controls, heading hierarchy, focusable elements |

**Mechanism:** Inject axe-core JS via `page.evaluate()`, run `axe.run()` with WCAG 2.1 AA ruleset. Assert zero `critical` or `serious` violations. Report `moderate` and `minor` as warnings.

**Output:** `tests/e2e/reports/a11y-violations.json` attached as CI artifact.

## `/debug_metrics` Endpoint

New API handler for server-side resource measurement in tests.

**File:** `python/api/debug_metrics.py`

**Route:** `GET /debug_metrics`

**Guards:** `requires_auth` + `requires_loopback` (localhost only, auth required — test mode only)

**Response:**
```json
{
  "rss_bytes": 142606336,
  "cpu_percent": 2.1,
  "open_files": 23,
  "uptime_seconds": 45.2
}
```

**Implementation:** `psutil.Process()` for all metrics. `psutil` is already a production dependency. No persistent storage, no Prometheus, no dashboards.

## CI Integration

### Self-hosted runner prerequisites

The runner must have: Python 3.12 (matching existing CI jobs), uv, Node.js (for frontend build in other jobs), Chromium (installed via `playwright install chromium`). A setup script or runner image provisions these. Ensure `uv` is in `$PATH`.

### New job in `.github/workflows/ci.yml`

```yaml
e2e-tests:
  runs-on: self-hosted
  needs: [lint, test]
  steps:
    - Checkout
    - Setup Python 3.12 + uv sync --extra dev
    - Install Playwright Chromium
    - Run: pytest tests/e2e/ -v --json-report --json-report-file=e2e-results.json
    - Run gate script (pass PR labels via github.event.pull_request.labels)
    - Post PR comment with summary
    - Upload artifacts (screenshots, a11y report, perf timings)
```

**Python version:** 3.12 to match existing CI jobs (`PYTHON_VERSION: "3.12"` in ci.yml). The local dev environment uses 3.11 — this is acceptable since the project declares `requires-python = ">=3.11"`.

### Gate Script (`scripts/ci/e2e_gate.py`)

Reads pytest JSON report, applies tiered logic:

| Category | Marker | Gate | Override |
|----------|--------|------|----------|
| Security | `security` | Hard block | Never |
| Functional | `e2e` | Hard block | Never |
| Performance | `performance` | Soft block (20% tolerance) | `[force-merge]` label |
| Accessibility | `a11y` | Advisory | Always passes |

**`[force-merge]` override mechanism:** The CI workflow step passes PR labels to the gate script as a CLI argument:

```yaml
- name: Apply gate logic
  run: |
    LABELS=$(echo '${{ toJSON(github.event.pull_request.labels.*.name) }}')
    python scripts/ci/e2e_gate.py e2e-results.json --labels "$LABELS"
```

The gate script checks if `"force-merge"` is in the labels list. If so, performance soft-blocks become warnings instead of failures.

**Non-PR contexts:** On direct pushes to `main` (not PRs), there are no labels. The gate script treats this as "no override" — performance soft-blocks are enforced. On `workflow_dispatch`, same behavior.

### PR Comment Format

```
## E2E Test Results
[check] Security: 16/16 passed
[check] Functional: 11/11 passed
[warn] Performance: 10/11 passed (test_spa_index_load: 3.4s, SLA 3.0s — within 20%)
[info] Accessibility: 2 moderate violations on /settings (see report)

Gate: PASS
```

### Artifacts

- `tests/e2e/screenshots/` — failure screenshots
- `tests/e2e/reports/a11y-violations.json` — accessibility violations
- `tests/e2e/reports/perf-timings.json` — performance measurements

## Files Created/Modified

| Action | File | Purpose |
|--------|------|---------|
| Create | `tests/e2e/test_functional.py` | Consolidated functional E2E tests |
| Create | `tests/e2e/test_security.py` (E2E) | OWASP security probes |
| Create | `tests/e2e/test_performance.py` | SLA and resource tests |
| Create | `tests/e2e/test_accessibility.py` | axe-core WCAG audits |
| Create | `python/api/debug_metrics.py` | Test-only metrics endpoint |
| Create | `scripts/ci/e2e_gate.py` | CI gate logic |
| Modify | `tests/e2e/conftest.py` | Enhanced fixtures, upload cleanup, warmup, JSON reporting |
| Modify | `.github/workflows/ci.yml` | Add e2e-tests job |
| Modify | `pyproject.toml` | Add pytest markers, dev deps |
| Delete | `tests/e2e/test_login_flow.py` | Consolidated into test_functional.py |
| Delete | `tests/e2e/test_logout.py` | Consolidated into test_functional.py |
| Delete | `tests/e2e/test_protected_routes.py` | Consolidated into test_functional.py |
| Delete | `tests/e2e/test_chat_interaction.py` | Consolidated into test_functional.py |
| Delete | `tests/e2e/test_file_upload.py` | Consolidated into test_functional.py |
| Delete | `tests/e2e/test_settings.py` | Consolidated into test_functional.py |

## Dependencies

Add to `pyproject.toml [dev]`:
- `pytest-json-report>=1.5.0` — JSON test output for gate script

axe-core will be injected as inline JS via Playwright's `page.evaluate()` — no extra Python dependency needed.

## Marker Registration

Add to `pyproject.toml [tool.pytest.ini_options] markers`:
```
"security: marks tests as security probes (hard block in CI)",
"performance: marks tests as performance SLA checks (soft block in CI)",
"a11y: marks tests as accessibility audits (advisory in CI)",
```

## Success Criteria

- All 11 functional tests pass
- All 16 security tests pass
- All 11 performance tests pass (within SLA or 20% tolerance)
- Accessibility audit runs and reports violations
- CI job runs on self-hosted runner, posts PR comment
- Gate script correctly blocks on security/functional failures
- Gate script allows override on performance soft-blocks via `[force-merge]` label
- Existing 1800+ unit tests unaffected

## Sources

- [Playwright Python docs](https://playwright.dev/python/)
- [axe-core rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)
- [OWASP Testing Guide](https://owasp.org/www-project-web-security-testing-guide/)
- [pytest-json-report](https://github.com/numirias/pytest-json-report)
