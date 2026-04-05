"""E2E tests for the telemetry API endpoints."""

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_telemetry_get_no_context(app_server, auth_cookies):
    """POST telemetry_get with a nonexistent context returns empty events and stats."""
    data = api_post(app_server, auth_cookies, "telemetry_get", {"context": "nonexistent_ctx_telemetry_e2e"})
    assert "events" in data, f"Expected 'events' key in response: {data}"
    assert isinstance(data["events"], list), f"Expected 'events' to be a list, got: {type(data['events'])}"
    assert "stats" in data, f"Expected 'stats' key in response: {data}"
    assert isinstance(data["stats"], dict), f"Expected 'stats' to be a dict, got: {type(data['stats'])}"


@pytest.mark.e2e
def test_telemetry_clear_no_context(app_server, auth_cookies):
    """POST telemetry_clear with a nonexistent context returns empty events and stats."""
    data = api_post(app_server, auth_cookies, "telemetry_clear", {"context": "nonexistent_ctx_telemetry_e2e"})
    assert "events" in data, f"Expected 'events' key in response: {data}"
    assert isinstance(data["events"], list), f"Expected 'events' to be a list, got: {type(data['events'])}"
    assert "stats" in data, f"Expected 'stats' key in response: {data}"
    assert isinstance(data["stats"], dict), f"Expected 'stats' to be a dict, got: {type(data['stats'])}"
