"""E2E tests for dashboard and settings endpoints in empty/default state.

Covers mos_dashboard, portfolio_dashboard, pms_settings_get, and scheduler_tick
endpoints — all of which must return structured responses even without full setup.
"""

import json
import urllib.error
import urllib.request

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_mos_dashboard_empty_state(app_server, auth_cookies):
    """POST /mos_dashboard with empty body returns success and required dashboard keys."""
    data = api_post(app_server, auth_cookies, "mos_dashboard", {})
    raw = json.dumps(data)
    assert "Traceback" not in raw, f"Server traceback in response: {raw}"
    assert data.get("success") is True, f"Expected success=True, got: {data}"
    for key in ("linear", "motion", "pipeline"):
        assert key in data, f"Expected key '{key}' in response, got keys: {list(data.keys())}"


def test_portfolio_dashboard_empty_state(app_server, auth_cookies):
    """POST /portfolio_dashboard with empty body returns success and required dashboard keys."""
    data = api_post(app_server, auth_cookies, "portfolio_dashboard", {})
    raw = json.dumps(data)
    assert "Traceback" not in raw, f"Server traceback in response: {raw}"
    assert data.get("success") is True, f"Expected success=True, got: {data}"
    assert "projects" in data, f"Expected 'projects' key in response, got keys: {list(data.keys())}"
    assert isinstance(data["projects"], list), f"Expected projects to be a list, got: {type(data['projects'])}"


def test_pms_settings_get_no_provider(app_server, auth_cookies):
    """POST /pms_settings_get with empty body returns status=success and providers list."""
    data = api_post(app_server, auth_cookies, "pms_settings_get", {})
    raw = json.dumps(data)
    assert "Traceback" not in raw, f"Server traceback in response: {raw}"
    assert "status" in data, f"Expected 'status' key in response, got: {list(data.keys())}"
    assert data["status"] == "success", f"Expected status='success', got: {data['status']!r}"
    assert "providers" in data, f"Expected 'providers' key in response, got: {list(data.keys())}"
    assert isinstance(data["providers"], list), f"Expected 'providers' to be a list, got: {type(data['providers'])}"


def test_pms_settings_get_nonexistent_provider(app_server, auth_cookies):
    """POST /pms_settings_get with unknown provider_id returns error status or 4xx/5xx."""
    try:
        data = api_post(app_server, auth_cookies, "pms_settings_get", {"provider_id": "nonexistent-xyz"})
        raw = json.dumps(data)
        assert "Traceback" not in raw, f"Server traceback in response: {raw}"
        # Endpoint must signal an error — either via status field or an error key
        is_error = data.get("status") == "error" or "error" in data
        assert is_error, f"Expected error response for nonexistent provider, got: {data}"
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        assert "Traceback" not in body, f"Server traceback in HTTP error body: {body}"
        assert exc.code in (400, 404, 500), f"Unexpected HTTP status {exc.code} for nonexistent provider"


def test_scheduler_tick_empty(app_server, auth_cookies):
    """POST /scheduler_tick with empty body via raw urllib (loopback-only, no CSRF).

    Expects a structured response with a 'scheduler' key, plus either a 'tasks'
    list for healthy runs or an 'error' key for graceful failure.
    """
    req = urllib.request.Request(
        f"{app_server}/scheduler_tick",
        data=json.dumps({}).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    result = None
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        assert "Traceback" not in body, f"Server traceback in HTTP error body: {body}"
        # A 4xx/5xx with no traceback is acceptable for a restricted endpoint
        assert exc.code in (400, 403, 404, 500), f"Unexpected HTTP status {exc.code}: {body}"
        return

    raw = json.dumps(result)
    assert "Traceback" not in raw, f"Server traceback in response: {raw}"
    assert "scheduler" in result, f"Expected 'scheduler' key in scheduler_tick response, got: {list(result.keys())}"
    # Either tasks list (success) or error key (graceful failure) must be present
    has_tasks = "tasks" in result and isinstance(result["tasks"], list)
    has_error = "error" in result
    assert has_tasks or has_error, f"Expected 'tasks' list or 'error' key in response, got: {list(result.keys())}"
