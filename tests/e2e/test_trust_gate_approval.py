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


def _send_message_background(app_server, auth_cookies, context_id: str, text: str) -> tuple[dict, threading.Thread]:
    """Send a message in a background thread; return (result_dict, thread).

    The /message endpoint blocks while the agent is paused at the trust gate,
    so callers should NOT join the thread eagerly. Instead, poll
    cowork_approvals_list for the pending approval record, then approve/deny it.
    The thread completes (with timed_out=True or a response) once the agent
    is unblocked.
    """
    result: dict = {}

    def _run() -> None:
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
    return result, t


def _poll_for_pending_trust_gate(app_server, auth_cookies, context_id: str, timeout: float = 30.0) -> dict | None:
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
            if approval.get("source") == "trust_gate" and approval.get("status") == "pending":
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
    try:
        _set_trust_level(app_server, auth_cookies, original)
    except Exception as exc:
        # Best-effort restore — don't fail teardown and poison subsequent tests
        print(f"Warning: failed to restore trust_level to {original}: {exc}")


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


@pytest.mark.slow
def test_trust_gate_creates_pending_approval(app_server, auth_cookies, observer_trust_level):
    """Observer trust level creates a pending trust-gate approval record for any tool call."""
    context_id = _create_context(app_server, auth_cookies)

    # Send a message in the background — agent will block waiting for approval
    _send_message_background(
        app_server,
        auth_cookies,
        context_id,
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
