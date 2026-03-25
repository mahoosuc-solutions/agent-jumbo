"""E2E tests for project API endpoints."""

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_projects_list(app_server, auth_cookies):
    """POST projects with action=list returns ok and a data list."""
    data = api_post(
        app_server,
        auth_cookies,
        "projects",
        {
            "action": "list",
        },
    )
    assert data.get("ok") is True, f"Expected ok=True from projects list: {data}"
    assert "data" in data, f"Expected 'data' key in response: {data}"
    assert isinstance(data["data"], list), f"Expected 'data' to be a list, got: {type(data['data'])}"


@pytest.mark.e2e
def test_projects_load_missing_name(app_server, auth_cookies):
    """POST projects with action=load but no name returns an error."""
    data = api_post(
        app_server,
        auth_cookies,
        "projects",
        {
            "action": "load",
        },
    )
    assert data.get("ok") is False, f"Expected ok=False for load without name: {data}"
    assert "error" in data, f"Expected 'error' key in failure response: {data}"


@pytest.mark.e2e
def test_projects_invalid_action(app_server, auth_cookies):
    """POST projects with an invalid action returns an error gracefully."""
    data = api_post(
        app_server,
        auth_cookies,
        "projects",
        {
            "action": "__nonexistent_action__",
        },
    )
    assert data.get("ok") is False, f"Expected ok=False for invalid action: {data}"
    assert "error" in data, f"Expected 'error' key in failure response: {data}"


@pytest.mark.e2e
def test_project_lifecycle_missing_project_name(app_server, auth_cookies):
    """POST project_lifecycle without project_name returns an error."""
    data = api_post(
        app_server,
        auth_cookies,
        "project_lifecycle",
        {
            "action": "get",
        },
    )
    assert data.get("ok") is False, f"Expected ok=False when project_name missing: {data}"
    assert "error" in data, f"Expected 'error' key in failure response: {data}"
