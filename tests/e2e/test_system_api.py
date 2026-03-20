"""E2E tests for system health and status API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_get, api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_health_check_returns_status(app_server, auth_cookies):
    """GET health_check returns ok, status, and checks dict."""
    data = api_get(app_server, auth_cookies, "health_check")
    assert "ok" in data, f"Expected 'ok' key in response: {data}"
    assert isinstance(data["ok"], bool), f"Expected 'ok' to be bool, got: {type(data['ok'])}"
    assert "status" in data, f"Expected 'status' key in response: {data}"
    assert data["status"] in ("healthy", "degraded"), (
        f"Expected status to be 'healthy' or 'degraded', got: {data['status']}"
    )
    assert "checks" in data, f"Expected 'checks' key in response: {data}"
    assert isinstance(data["checks"], dict), (
        f"Expected 'checks' to be a dict, got: {type(data['checks'])}"
    )


@pytest.mark.e2e
def test_health_check_includes_disk_and_uptime(app_server, auth_cookies):
    """health_check response includes disk and uptime sub-checks."""
    data = api_get(app_server, auth_cookies, "health_check")
    checks = data["checks"]
    assert "disk" in checks, f"Expected 'disk' in checks: {checks}"
    assert "free_gb" in checks["disk"], f"Expected 'free_gb' in disk check: {checks['disk']}"
    assert isinstance(checks["disk"]["free_gb"], (int, float)), (
        f"Expected free_gb to be numeric, got: {type(checks['disk']['free_gb'])}"
    )
    assert "uptime_seconds" in checks, f"Expected 'uptime_seconds' in checks: {checks}"
    assert isinstance(checks["uptime_seconds"], (int, float)), (
        f"Expected uptime_seconds to be numeric, got: {type(checks['uptime_seconds'])}"
    )


@pytest.mark.e2e
def test_gateway_status_returns_channels(app_server, auth_cookies):
    """POST gateway_status returns channels list and gateway stats."""
    data = api_post(app_server, auth_cookies, "gateway_status", {})
    assert "channels" in data, f"Expected 'channels' key in response: {data}"
    assert isinstance(data["channels"], list), (
        f"Expected 'channels' to be a list, got: {type(data['channels'])}"
    )
    assert "gateway" in data, f"Expected 'gateway' key in response: {data}"
