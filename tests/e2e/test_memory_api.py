"""E2E tests for memory dashboard API endpoints."""

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_memory_dashboard_get_subdirs(app_server, auth_cookies):
    """POST memory_dashboard with action=get_memory_subdirs returns subdirectory list."""
    data = api_post(
        app_server,
        auth_cookies,
        "memory_dashboard",
        {
            "action": "get_memory_subdirs",
        },
    )
    assert data.get("success") is True, f"Expected success=True: {data}"
    assert "subdirs" in data, f"Expected 'subdirs' key in response: {data}"
    assert isinstance(data["subdirs"], list), f"Expected 'subdirs' to be a list, got: {type(data['subdirs'])}"


@pytest.mark.e2e
def test_memory_dashboard_get_current_subdir(app_server, auth_cookies):
    """POST memory_dashboard with action=get_current_memory_subdir returns a subdir string."""
    data = api_post(
        app_server,
        auth_cookies,
        "memory_dashboard",
        {
            "action": "get_current_memory_subdir",
        },
    )
    assert data.get("success") is True, f"Expected success=True: {data}"
    assert "memory_subdir" in data, f"Expected 'memory_subdir' key: {data}"
    assert isinstance(data["memory_subdir"], str), (
        f"Expected memory_subdir to be a string, got: {type(data['memory_subdir'])}"
    )


@pytest.mark.e2e
def test_memory_dashboard_search_default(app_server, auth_cookies):
    """POST memory_dashboard with action=search returns memory list and counts."""
    data = api_post(
        app_server,
        auth_cookies,
        "memory_dashboard",
        {
            "action": "search",
            "memory_subdir": "default",
        },
    )
    assert data.get("success") is True, f"Expected success=True: {data}"
    assert "memories" in data, f"Expected 'memories' key: {data}"
    assert isinstance(data["memories"], list), f"Expected 'memories' to be a list, got: {type(data['memories'])}"
    assert "total_count" in data, f"Expected 'total_count' key: {data}"
    assert isinstance(data["total_count"], int), f"Expected total_count to be int, got: {type(data['total_count'])}"


@pytest.mark.e2e
def test_memory_dashboard_unknown_action(app_server, auth_cookies):
    """POST memory_dashboard with an unknown action returns a failure response."""
    data = api_post(
        app_server,
        auth_cookies,
        "memory_dashboard",
        {
            "action": "__nonexistent_action__",
        },
    )
    assert data.get("success") is False, f"Expected success=False for unknown action: {data}"
    assert "error" in data, f"Expected 'error' key in failure response: {data}"
