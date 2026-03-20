import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_ralph_loop_dashboard(app_server, auth_cookies):
    """POST to ralph_loop_dashboard with empty body.

    The handler wraps everything in try/except, returning a zero-stats dict on
    failure. Assert success key exists; if True check for dashboard-related
    keys; if False check error key exists.
    """
    try:
        result = api_post(app_server, auth_cookies, "ralph_loop_dashboard", {})
        assert "success" in result
        if result["success"]:
            # At least one dashboard-related key should be present
            dashboard_keys = {"stats", "dashboard", "data", "loop", "status", "runs"}
            assert any(k in result for k in dashboard_keys), (
                f"Expected at least one dashboard key in response, got: {list(result.keys())}"
            )
        else:
            assert "error" in result
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 500), f"Unexpected HTTP error code: {exc.code}"


def test_ralph_loop_control_missing_action(app_server, auth_cookies):
    """POST to ralph_loop_control with empty body (no action key).

    The handler reads action = input.get("action", ""). An unknown/empty
    action should return an error with a valid action list, or raise 400/500.
    """
    try:
        result = api_post(app_server, auth_cookies, "ralph_loop_control", {})
        # Handler should return success=False or include an error key
        assert result.get("success") is False or "error" in result, (
            f"Expected error response for missing action, got: {result}"
        )
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 500), f"Unexpected HTTP error code: {exc.code}"


def test_workflow_training_unknown_action(app_server, auth_cookies):
    """POST to workflow_training_api with an unrecognised action.

    Expected response: {"success": False, "error": "Unknown action: unknown_xyz"}.
    """
    try:
        result = api_post(
            app_server,
            auth_cookies,
            "workflow_training_api",
            {"action": "unknown_xyz"},
        )
        assert result.get("success") is False, f"Expected success=False for unknown action, got: {result}"
        assert "error" in result, f"Expected error key in response, got: {list(result.keys())}"
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 500), f"Unexpected HTTP error code: {exc.code}"


def test_scheduler_task_run_missing_id(app_server, auth_cookies):
    """POST to scheduler_task_run with empty body (no task_id).

    The handler checks for task_id and returns
    {"error": "Missing required field: task_id"} when it is absent.
    """
    try:
        result = api_post(app_server, auth_cookies, "scheduler_task_run", {})
        assert "error" in result or result.get("success") is False, (
            f"Expected error response for missing task_id, got: {result}"
        )
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 500), f"Unexpected HTTP error code: {exc.code}"


def test_linear_dashboard_unknown_action(app_server, auth_cookies):
    """POST to linear_dashboard with an unrecognised action.

    Expected response: {"success": False, "error": "Unknown action: unknown_xyz"}.
    """
    try:
        result = api_post(
            app_server,
            auth_cookies,
            "linear_dashboard",
            {"action": "unknown_xyz"},
        )
        assert result.get("success") is False, f"Expected success=False for unknown action, got: {result}"
        assert "error" in result, f"Expected error key in response, got: {list(result.keys())}"
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 500), f"Unexpected HTTP error code: {exc.code}"
