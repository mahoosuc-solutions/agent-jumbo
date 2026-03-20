"""E2E tests for tunnel, workflow, and file management endpoints.

Covers tunnel health/status/invalid-action, workflow context clearing,
and work directory file listing.
"""

import urllib.error

import pytest

from tests.e2e.helpers import api_get, api_post

pytestmark = [pytest.mark.e2e]


def test_tunnel_health_action(app_server, auth_cookies):
    """POST /tunnel with action=health returns a response with a 'success' key.

    A True value indicates the tunnel is healthy; a False value (or an error
    dict) is acceptable when the tunnel module is unavailable — what matters is
    that the server returns a structured response without a traceback.
    """
    try:
        resp = api_post(app_server, auth_cookies, "tunnel", {"action": "health"})
        assert "success" in resp, f"Expected 'success' key in response, got: {resp}"
        assert "Traceback" not in str(resp), f"Unexpected traceback in response: {resp}"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        assert exc.code in (400, 500, 503), f"Unexpected HTTP error code {exc.code}: {body}"
        assert "Traceback" not in body, f"Traceback found in error response body: {body}"


def test_tunnel_get_status(app_server, auth_cookies):
    """POST /tunnel with action=get returns a structured status response.

    Expects a 'success' key and at least one of 'tunnel_url', 'is_running',
    or a graceful error dict when the tunnel backend is not configured.
    """
    try:
        resp = api_post(app_server, auth_cookies, "tunnel", {"action": "get"})
        assert "success" in resp, f"Expected 'success' key in response, got: {resp}"
        assert "Traceback" not in str(resp), f"Unexpected traceback in response: {resp}"
        if resp.get("success"):
            status_keys = {"tunnel_url", "is_running", "url", "status", "data"}
            assert any(k in resp for k in status_keys), (
                f"Expected at least one status key {status_keys} in response, got: {list(resp.keys())}"
            )
        else:
            # Graceful error path: success=False should carry an error description
            assert "error" in resp or "message" in resp or "reason" in resp, (
                f"Expected error description key in failure response, got: {resp}"
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        assert exc.code in (400, 500, 503), f"Unexpected HTTP error code {exc.code}: {body}"
        assert "Traceback" not in body, f"Traceback found in error response body: {body}"


def test_tunnel_invalid_action(app_server, auth_cookies):
    """POST /tunnel with an unrecognised action returns success=False or an error.

    The server must not raise an unhandled exception for unknown actions.
    """
    try:
        resp = api_post(app_server, auth_cookies, "tunnel", {"action": "invalid_xyz"})
        assert resp.get("success") is False or "error" in resp or "message" in resp, (
            f"Expected error response for invalid action, got: {resp}"
        )
        assert "Traceback" not in str(resp), f"Unexpected traceback in response: {resp}"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        assert exc.code in (400, 403, 422, 500), f"Unexpected HTTP error code {exc.code}: {body}"
        assert "Traceback" not in body, f"Traceback found in error response body: {body}"


def test_workflow_clear_bogus_context(app_server, auth_cookies):
    """POST /workflow_clear with a non-existent context ID returns an error response.

    The server should respond with ok=false, success=false, or an HTTP error
    status — not silently succeed on a bogus context ID.
    """
    try:
        resp = api_post(
            app_server,
            auth_cookies,
            "workflow_clear",
            {"context": "nonexistent-ctx-id-12345"},
        )
        # A non-existent context should not return a clean success
        is_error = resp.get("ok") is False or resp.get("success") is False or "error" in resp or "message" in resp
        assert is_error, f"Expected an error response for bogus context ID, got: {resp}"
        assert "Traceback" not in str(resp), f"Unexpected traceback in response: {resp}"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        assert exc.code in (400, 404, 422, 500), f"Unexpected HTTP error code {exc.code}: {body}"
        assert "Traceback" not in body, f"Traceback found in error response body: {body}"


def test_get_work_dir_files(app_server, auth_cookies):
    """GET /get_work_dir_files returns a structured file listing dict with a 'data' key."""
    try:
        resp = api_get(app_server, auth_cookies, "get_work_dir_files")
        assert isinstance(resp, dict), f"Expected dict response, got: {type(resp)}"
        assert "data" in resp or "files" in resp or "entries" in resp or "success" in resp, (
            f"Expected a structured file listing key in response, got: {list(resp.keys())}"
        )
        assert "Traceback" not in str(resp), f"Unexpected traceback in response: {resp}"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        assert exc.code in (400, 403, 500), f"Unexpected HTTP error code {exc.code}: {body}"
        assert "Traceback" not in body, f"Traceback found in error response body: {body}"
