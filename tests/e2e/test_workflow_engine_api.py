"""E2E tests for the workflow engine API endpoints.

Covers workflow listing, dashboard retrieval, run history, and error handling
for missing parameters.
"""

import urllib.error

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_workflow_list(app_server, auth_cookies):
    """POST workflow_engine_api with action list_workflows returns success and workflows."""
    data = api_post(app_server, auth_cookies, "workflow_engine_api", {"action": "list_workflows"})
    assert "success" in data or "ok" in data, f"Expected 'success' or 'ok' key in response: {data}"
    assert "workflows" in data, f"Expected 'workflows' key in response: {data}"
    assert isinstance(data["workflows"], list), f"Expected 'workflows' to be a list, got: {type(data['workflows'])}"


@pytest.mark.e2e
def test_workflow_dashboard(app_server, auth_cookies):
    """POST workflow_dashboard with empty body returns success and stats."""
    data = api_post(app_server, auth_cookies, "workflow_dashboard", {})
    assert "success" in data or "ok" in data, f"Expected 'success' or 'ok' key in response: {data}"
    assert "stats" in data or "dashboard" in data, f"Expected 'stats' or 'dashboard' key in response: {data}"


@pytest.mark.e2e
def test_workflow_get(app_server, auth_cookies):
    """POST workflow_get with empty body returns a runs key."""
    data = api_post(app_server, auth_cookies, "workflow_get", {})
    assert "runs" in data or "workflows" in data, f"Expected 'runs' or 'workflows' key in response: {data}"


@pytest.mark.e2e
def test_workflow_get_status_missing_id(app_server, auth_cookies):
    """POST workflow_engine_api with action get_status but no execution_id returns an error."""
    try:
        data = api_post(app_server, auth_cookies, "workflow_engine_api", {"action": "get_status"})
        # If the server returns 200, it should indicate failure due to missing execution_id
        assert data.get("success") is False or data.get("ok") is False or "error" in data, (
            f"Expected error for missing execution_id, got: {data}"
        )
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 422, 500), f"Unexpected HTTP status {exc.code}: {getattr(exc, '_response_body', '')}"
