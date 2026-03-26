"""E2E tests for the MCP (Model Context Protocol) server management API endpoints.

Covers server status, detail retrieval, log access, and tool cache reloading.
"""

import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_mcp_status_returns_structure(app_server, auth_cookies):
    """POST mcp_servers_status with empty body returns success and status keys."""
    data = api_post(app_server, auth_cookies, "mcp_servers_status", {})
    assert "success" in data or "ok" in data, f"Expected 'success' or 'ok' key in response: {data}"
    assert "status" in data or "servers" in data, f"Expected 'status' or 'servers' key in response: {data}"


@pytest.mark.e2e
def test_mcp_detail_missing_name(app_server, auth_cookies):
    """POST mcp_server_get_detail without server_name returns an error."""
    try:
        data = api_post(app_server, auth_cookies, "mcp_server_get_detail", {})
        # If the server returns 200, it should indicate failure
        assert data.get("success") is False or data.get("ok") is False or "error" in data, (
            f"Expected error for missing server_name, got: {data}"
        )
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 422, 500), f"Unexpected HTTP status {exc.code}: {getattr(exc, '_response_body', '')}"


@pytest.mark.e2e
def test_mcp_detail_unknown_server(app_server, auth_cookies):
    """POST mcp_server_get_detail with a nonexistent server_name handles gracefully."""
    try:
        data = api_post(app_server, auth_cookies, "mcp_server_get_detail", {"server_name": "nonexistent_xyz"})
        # Either an error dict or an empty/null detail is acceptable
        assert isinstance(data, dict), f"Expected a JSON object response, got: {data!r}"
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 404, 422, 500), (
            f"Unexpected HTTP status {exc.code}: {getattr(exc, '_response_body', '')}"
        )


@pytest.mark.e2e
def test_mcp_log_missing_name(app_server, auth_cookies):
    """POST mcp_server_get_log without server_name returns an error."""
    try:
        data = api_post(app_server, auth_cookies, "mcp_server_get_log", {})
        assert data.get("success") is False or data.get("ok") is False or "error" in data, (
            f"Expected error for missing server_name, got: {data}"
        )
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 422, 500), f"Unexpected HTTP status {exc.code}: {getattr(exc, '_response_body', '')}"


@pytest.mark.e2e
def test_mcp_tools_reload(app_server, auth_cookies):
    """POST mcp_tools_reload with empty body returns success and cache keys."""
    data = api_post(app_server, auth_cookies, "mcp_tools_reload", {})
    assert "success" in data or "ok" in data, f"Expected 'success' or 'ok' key in response: {data}"
    assert "cache" in data or "tools" in data, f"Expected 'cache' or 'tools' key in response: {data}"
