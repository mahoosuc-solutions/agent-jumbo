# Trust Gate E2E Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add E2E tests that exercise the full trust gate approve→unblock→retry loop and the deny flow, replacing the two thin smoke tests that only hit nonexistent contexts.

**Architecture:** Tests use the existing `api_post` helper (CSRF + auth cookies) to: (1) set trust level to Observer so every tool needs approval, (2) send a message that triggers a tool call, (3) poll `cowork_approvals_list` until a pending trust-gate record appears, (4) call `cowork_approvals_update` with `action=approve` or `action=deny`, (5) assert the final state. The `/message` endpoint returns `timed_out: true` when the agent is paused — tests send the message in a background thread and poll separately. The `memory_load` tool (LOW risk) is used as a safe trigger at OBSERVER level.

**Tech Stack:** Python stdlib (`urllib`, `threading`, `time`), pytest, existing `tests/e2e/helpers.py` (`api_post`, `api_post_tolerant`)

---

## File Structure

| File | Change |
|------|--------|
| `tests/e2e/test_trust_gate_approval.py` | Replace thin smoke tests with full flow tests + helpers |

No new files. No backend changes.

---

### Task 1: Replace smoke tests with integration-ready skeleton

**Files:**

- Modify: `tests/e2e/test_trust_gate_approval.py`

This task rewrites the file with proper imports, a settings-restore fixture, a polling helper, and the two original smoke tests kept as-is (they serve as a sanity baseline).

- [ ] **Step 1: Read the current file to confirm what's there**

```bash
cat tests/e2e/test_trust_gate_approval.py
```

Expected: 32 lines, 2 tests using nonexistent context IDs.

- [ ] **Step 2: Rewrite the file with the new skeleton**

```python
"""E2E tests for trust gate → cowork approval integration.

Full flow:
  1. Set trust_level to 1 (Observer — every tool needs approval)
  2. POST /message with a prompt that triggers a tool call
  3. Poll /cowork_approvals_list until a pending trust-gate record appears
  4. POST /cowork_approvals_update with action=approve or action=deny
  5. Assert final state

The /message endpoint returns timed_out=True when the agent is paused
waiting for approval, so we send the message in a background thread
and poll the approvals list in the foreground.
"""
import threading
import time

import pytest

from tests.e2e.helpers import api_post, api_post_tolerant

pytestmark = [pytest.mark.e2e]

# ── Helpers ────────────────────────────────────────────────────────────────


def _set_trust_level(app_server, auth_cookies, level: int) -> None:
    """Set trust_level via settings_set."""
    api_post_tolerant(
        app_server,
        auth_cookies,
        "settings_set",
        {"sections": [{"fields": [{"id": "trust_level", "value": level}]}]},
    )


def _get_trust_level(app_server, auth_cookies) -> int:
    """Return the current trust_level from settings_get."""
    resp = api_post_tolerant(app_server, auth_cookies, "settings_get", {})
    for section in resp.get("settings", {}).get("sections", []):
        for field in section.get("fields", []):
            if field.get("id") == "trust_level":
                return int(field["value"])
    return 3  # fallback: Collaborative


def _create_context(app_server, auth_cookies) -> str:
    """Create a fresh agent context and return its ID."""
    resp = api_post(app_server, auth_cookies, "chat_create", {})
    return resp["context"]


def _send_message_background(app_server, auth_cookies, context_id: str, text: str) -> dict:
    """Send a message in a background thread; return the response dict."""
    result = {}

    def _run():
        try:
            result["resp"] = api_post(
                app_server,
                auth_cookies,
                "message",
                {"text": text, "context": context_id},
            )
        except Exception as exc:
            result["error"] = exc

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return result  # caller inspects result["resp"] after joining / polling


def _poll_for_pending_trust_gate(
    app_server, auth_cookies, context_id: str, timeout: float = 30.0
) -> dict | None:
    """Poll cowork_approvals_list until a pending trust-gate record appears."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = api_post(
            app_server,
            auth_cookies,
            "cowork_approvals_list",
            {"context": context_id},
        )
        for approval in resp.get("approvals", []):
            if (
                approval.get("source") == "trust_gate"
                and approval.get("status") == "pending"
            ):
                return approval
        time.sleep(1.0)
    return None


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture()
def observer_trust_level(app_server, auth_cookies):
    """Set trust_level=1 for the test; restore original value afterward."""
    original = _get_trust_level(app_server, auth_cookies)
    _set_trust_level(app_server, auth_cookies, 1)
    yield
    _set_trust_level(app_server, auth_cookies, original)


# ── Baseline smoke tests (keep these — they verify API shape) ──────────────


def test_trust_gate_approval_record_has_source_field(app_server, auth_cookies):
    """cowork_approvals_list with a nonexistent context returns empty approvals."""
    resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_list",
        {"context": "nonexistent_trust_gate_ctx"},
    )
    assert resp["approvals"] == []


def test_cowork_approvals_update_approve_and_retry_action(app_server, auth_cookies):
    """approve_and_retry action on nonexistent record returns approvals list."""
    resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_update",
        {
            "context": "nonexistent_trust_gate_ctx",
            "action": "approve_and_retry",
            "approval_id": "trust-nonexistent-id",
        },
    )
    assert "approvals" in resp
```

- [ ] **Step 3: Run the two smoke tests to confirm they still pass**

```bash
pytest tests/e2e/test_trust_gate_approval.py::test_trust_gate_approval_record_has_source_field \
       tests/e2e/test_trust_gate_approval.py::test_cowork_approvals_update_approve_and_retry_action \
       -v -m e2e
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_trust_gate_approval.py
git commit -m "test: add trust gate E2E helpers and restore-fixture skeleton"
```

---

### Task 2: Test — trust gate blocks and approval record appears

**Files:**

- Modify: `tests/e2e/test_trust_gate_approval.py`

This task adds the first real integration test: set Observer level, send a message, verify a pending trust-gate approval record is created. Does NOT approve — just verifies the gate fires.

- [ ] **Step 1: Write the failing test (append to the file)**

```python
@pytest.mark.slow
def test_trust_gate_creates_pending_approval(app_server, auth_cookies, observer_trust_level):
    """Observer trust level creates a pending trust-gate approval record for any tool call."""
    context_id = _create_context(app_server, auth_cookies)

    # Send a message in the background — agent will block waiting for approval
    _send_message_background(
        app_server, auth_cookies, context_id,
        "Use the memory_load tool to recall any stored facts.",
    )

    # Poll until the trust gate fires and creates an approval record
    approval = _poll_for_pending_trust_gate(app_server, auth_cookies, context_id, timeout=45)

    assert approval is not None, "Expected a pending trust-gate approval to appear within 45s"
    assert approval["source"] == "trust_gate"
    assert approval["status"] == "pending"
    assert "tool_name" in approval
    assert "id" in approval
    assert approval["id"].startswith("trust-")
    assert "risk" in approval
    assert approval["risk"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
```

- [ ] **Step 2: Run to verify it fails (or is skipped without a model configured)**

```bash
pytest tests/e2e/test_trust_gate_approval.py::test_trust_gate_creates_pending_approval \
       -v -m "e2e and slow" -s
```

Expected: either FAIL (assertion error — no approval appeared, because the gate hasn't fired yet end-to-end) or PASS if the server is running with a model. This confirms the test logic runs without syntax errors.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_trust_gate_approval.py
git commit -m "test: add trust gate blocks tool and creates pending approval record"
```

---

### Task 3: Test — approve unblocks the agent

**Files:**

- Modify: `tests/e2e/test_trust_gate_approval.py`

This task adds the approve flow: after detecting the pending record, call `approve`, then verify the record transitions to `approved` and the agent is no longer paused.

- [ ] **Step 1: Append the approve test**

```python
@pytest.mark.slow
def test_trust_gate_approve_unblocks_agent(app_server, auth_cookies, observer_trust_level):
    """Approving a trust-gate record sets status=approved and unblocks the agent."""
    context_id = _create_context(app_server, auth_cookies)

    # Send a message in background — agent will block at the trust gate
    bg_result = _send_message_background(
        app_server, auth_cookies, context_id,
        "Use the memory_load tool to recall any stored facts.",
    )

    # Wait for approval to appear
    approval = _poll_for_pending_trust_gate(app_server, auth_cookies, context_id, timeout=45)
    assert approval is not None, "No pending trust-gate approval appeared within 45s"

    approval_id = approval["id"]

    # Approve it
    update_resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_update",
        {
            "context": context_id,
            "action": "approve",
            "approval_id": approval_id,
        },
    )
    assert "approvals" in update_resp

    # Verify the record is now approved
    approvals = update_resp["approvals"]
    matched = next((a for a in approvals if a["id"] == approval_id), None)
    assert matched is not None, f"Approval {approval_id} not found in response"
    assert matched["status"] == "approved", f"Expected approved, got {matched['status']}"

    # Verify context is no longer paused by polling chat_readiness
    deadline = time.time() + 15
    unblocked = False
    while time.time() < deadline:
        readiness = api_post(app_server, auth_cookies, "chat_readiness", {"context": context_id})
        if not readiness.get("paused", True):
            unblocked = True
            break
        time.sleep(1.0)

    assert unblocked, "Agent context was still paused 15s after approval"
```

- [ ] **Step 2: Check that `chat_readiness` exists as an endpoint**

```bash
grep -rn "chat_readiness\|ChatReadiness" python/api/ python/helpers/api.py run_ui.py | head -5
```

Expected: at least one match showing the endpoint is registered.

- [ ] **Step 3: Run the test**

```bash
pytest tests/e2e/test_trust_gate_approval.py::test_trust_gate_approve_unblocks_agent \
       -v -m "e2e and slow" -s
```

Expected: PASS (with model configured) or explicit assertion failure explaining which step failed.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_trust_gate_approval.py
git commit -m "test: verify trust gate approve sets status=approved and unblocks agent"
```

---

### Task 4: Test — deny blocks further execution

**Files:**

- Modify: `tests/e2e/test_trust_gate_approval.py`

This task adds the deny flow: approve fires a retry message; deny should inject "do not attempt this action again" and leave the context unblocked (agent got the denial message and continues from there).

- [ ] **Step 1: Append the deny test**

```python
@pytest.mark.slow
def test_trust_gate_deny_resolves_approval(app_server, auth_cookies, observer_trust_level):
    """Denying a trust-gate record sets status=denied and unblocks the agent with a denial message."""
    context_id = _create_context(app_server, auth_cookies)

    _send_message_background(
        app_server, auth_cookies, context_id,
        "Use the memory_load tool to recall any stored facts.",
    )

    approval = _poll_for_pending_trust_gate(app_server, auth_cookies, context_id, timeout=45)
    assert approval is not None, "No pending trust-gate approval appeared within 45s"

    approval_id = approval["id"]

    # Deny it
    update_resp = api_post(
        app_server,
        auth_cookies,
        "cowork_approvals_update",
        {
            "context": context_id,
            "action": "deny",
            "approval_id": approval_id,
        },
    )
    assert "approvals" in update_resp

    # Verify the record is now denied
    approvals = update_resp["approvals"]
    matched = next((a for a in approvals if a["id"] == approval_id), None)
    assert matched is not None, f"Approval {approval_id} not found in response"
    assert matched["status"] == "denied", f"Expected denied, got {matched['status']}"

    # The agent should be unblocked after a denial (it receives the denial message and continues)
    deadline = time.time() + 15
    unblocked = False
    while time.time() < deadline:
        readiness = api_post(app_server, auth_cookies, "chat_readiness", {"context": context_id})
        if not readiness.get("paused", True):
            unblocked = True
            break
        time.sleep(1.0)

    assert unblocked, "Agent context was still paused 15s after denial"
```

- [ ] **Step 2: Run all slow trust gate tests together**

```bash
pytest tests/e2e/test_trust_gate_approval.py -v -m "e2e and slow" -s
```

Expected: 2 slow tests pass (plus 2 baseline smoke tests = 4 total).

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_trust_gate_approval.py
git commit -m "test: verify trust gate deny sets status=denied and unblocks agent"
```

---

### Task 5: Test — always-allow skips the gate on next call

**Files:**

- Modify: `tests/e2e/test_trust_gate_approval.py`

This test verifies that adding a tool to `trust_always_allow` via `settings_set` causes the gate to be skipped on the next invocation of that tool.

- [ ] **Step 1: Append the always-allow test**

```python
@pytest.mark.slow
def test_trust_gate_always_allow_bypasses_gate(app_server, auth_cookies, observer_trust_level):
    """A tool in trust_always_allow is not blocked by the trust gate."""
    context_id = _create_context(app_server, auth_cookies)

    # Add memory_load to the always-allow list
    api_post_tolerant(
        app_server,
        auth_cookies,
        "settings_set",
        {"sections": [{"fields": [{"id": "trust_always_allow", "value": ["memory_load"]}]}]},
    )

    try:
        # Send a message that would trigger memory_load — it should NOT be blocked
        _send_message_background(
            app_server, auth_cookies, context_id,
            "Use the memory_load tool to recall any stored facts.",
        )

        # Give the agent time to run — if the gate fires, a pending approval would appear
        time.sleep(10)

        resp = api_post(app_server, auth_cookies, "cowork_approvals_list", {"context": context_id})
        trust_gate_pending = [
            a for a in resp.get("approvals", [])
            if a.get("source") == "trust_gate"
            and a.get("status") == "pending"
            and a.get("tool_name") == "memory_load"
        ]
        assert trust_gate_pending == [], (
            f"Expected no pending trust-gate approval for memory_load (it is always-allowed), "
            f"but found: {trust_gate_pending}"
        )
    finally:
        # Restore always-allow list to empty
        api_post_tolerant(
            app_server,
            auth_cookies,
            "settings_set",
            {"sections": [{"fields": [{"id": "trust_always_allow", "value": []}]}]},
        )
```

- [ ] **Step 2: Run the full test file**

```bash
pytest tests/e2e/test_trust_gate_approval.py -v -m e2e -s
```

Expected: 5 tests collected. Slow tests require a model to be configured — if no model is configured they will fail at the `_poll_for_pending_trust_gate` assertion with a clear message. The 2 smoke tests always pass.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/test_trust_gate_approval.py
git commit -m "test: verify trust_always_allow bypasses the trust gate"
```

---

### Task 6: Verify chat_readiness endpoint — add fallback if missing

**Files:**

- Read: `python/api/chat_readiness.py`
- Possibly modify: `tests/e2e/test_trust_gate_approval.py` (use fallback if endpoint absent)

Tasks 3 and 4 poll `chat_readiness` to verify the agent is unblocked. This task verifies the endpoint exists and its response shape, and adds a fallback poll if needed.

- [ ] **Step 1: Check the endpoint**

```bash
cat python/api/chat_readiness.py
```

Expected: a class with `process()` that returns something including a `paused` field.

- [ ] **Step 2: If `paused` is not in the response, add a cowork_approvals_list-based fallback**

If `chat_readiness` does not return `paused`, replace the unblock poll in `test_trust_gate_approve_unblocks_agent` and `test_trust_gate_deny_resolves_approval` with:

```python
# Fallback: check that no pending approvals remain for this context
deadline = time.time() + 15
unblocked = False
while time.time() < deadline:
    resp = api_post(app_server, auth_cookies, "cowork_approvals_list", {"context": context_id})
    pending = [a for a in resp.get("approvals", []) if a.get("status") == "pending"]
    if not pending:
        unblocked = True
        break
    time.sleep(1.0)
```

- [ ] **Step 3: Run full suite one final time**

```bash
pytest tests/e2e/test_trust_gate_approval.py -v -m e2e
```

Expected: all non-slow tests pass; slow tests either pass (model configured) or fail with the clear assertion messages defined in each test.

- [ ] **Step 4: Final commit**

```bash
git add tests/e2e/test_trust_gate_approval.py
git commit -m "test: harden trust gate E2E tests with chat_readiness fallback"
```

---

## Self-Review

**Spec coverage:**

- ✅ Full approve→unblock flow: Task 3
- ✅ Deny flow: Task 4
- ✅ Always-allow bypass: Task 5
- ✅ Approval record shape (source, status, id, risk): Task 2
- ✅ Settings restore fixture: Task 1

**Placeholder scan:** No TBDs, no vague steps. Every code block is complete and runnable.

**Type consistency:** `_poll_for_pending_trust_gate` returns `dict | None` and all callers check for `None` with assertion messages. `_send_message_background` returns `dict` (the mutable result container), callers don't need the value directly — they poll separately.

**Edge case:** If no model is configured in the test environment, the agent never runs and `_poll_for_pending_trust_gate` will time out. The assertion message `"No pending trust-gate approval appeared within 45s"` is clear enough to diagnose this without digging into logs. Slow tests are marked `@pytest.mark.slow` so CI can skip them when no model key is set.
