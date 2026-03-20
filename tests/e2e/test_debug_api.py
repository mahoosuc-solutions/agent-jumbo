"""E2E tests for the debug and observability API endpoints."""

import pytest

from tests.e2e.helpers import api_get, api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_debug_metrics_returns_system_info(app_server, auth_cookies):
    """GET debug_metrics returns system info with rss_bytes, cpu_percent, open_files, uptime_seconds."""
    data = api_get(app_server, auth_cookies, "debug_metrics")
    assert "rss_bytes" in data, f"Expected 'rss_bytes' key in response: {data}"
    assert isinstance(data["rss_bytes"], int), f"Expected 'rss_bytes' to be an int, got: {type(data['rss_bytes'])}"
    assert "cpu_percent" in data, f"Expected 'cpu_percent' key in response: {data}"
    assert "open_files" in data, f"Expected 'open_files' key in response: {data}"
    assert "uptime_seconds" in data, f"Expected 'uptime_seconds' key in response: {data}"


@pytest.mark.e2e
def test_ctx_window_get_empty_context(app_server, auth_cookies):
    """POST ctx_window_get with a nonexistent context returns content and tokens keys."""
    data = api_post(app_server, auth_cookies, "ctx_window_get", {"context": "nonexistent_ctx_debug_e2e"})
    assert "content" in data, f"Expected 'content' key in response: {data}"
    assert "tokens" in data, f"Expected 'tokens' key in response: {data}"
    assert isinstance(data["tokens"], int), f"Expected 'tokens' to be an int, got: {type(data['tokens'])}"


@pytest.mark.e2e
def test_ctx_window_get_with_valid_context(app_server, auth_cookies):
    """Create a context via chat_create, then POST ctx_window_get with that ctxid."""
    create_data = api_post(app_server, auth_cookies, "chat_create", {})
    ctxid = create_data["ctxid"]
    data = api_post(app_server, auth_cookies, "ctx_window_get", {"context": ctxid})
    assert "content" in data, f"Expected 'content' key in response: {data}"
    assert "tokens" in data, f"Expected 'tokens' key in response: {data}"
    assert isinstance(data["tokens"], int), f"Expected 'tokens' to be an int, got: {type(data['tokens'])}"
