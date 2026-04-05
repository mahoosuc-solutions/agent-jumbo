"""E2E tests for notification API endpoints."""

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_notifications_history_returns_list(app_server, auth_cookies):
    """POST notifications_history returns a response with notifications list and count."""
    data = api_post(app_server, auth_cookies, "notifications_history", {})
    assert "notifications" in data, f"Expected 'notifications' key in response: {data}"
    assert isinstance(data["notifications"], list), (
        f"Expected 'notifications' to be a list, got: {type(data['notifications'])}"
    )
    assert "count" in data, f"Expected 'count' key in response: {data}"
    assert isinstance(data["count"], int), f"Expected 'count' to be an int, got: {type(data['count'])}"


@pytest.mark.e2e
def test_notification_create_with_message(app_server, auth_cookies):
    """POST notification_create with a valid message returns success and notification_id."""
    data = api_post(
        app_server,
        auth_cookies,
        "notification_create",
        {
            "message": "E2E test notification",
            "title": "Test",
            "type": "info",
            "priority": "normal",
        },
    )
    assert data.get("success") is True, f"Expected success=True, got: {data}"
    assert "notification_id" in data, f"Expected 'notification_id' key in response: {data}"


@pytest.mark.e2e
def test_notification_create_missing_message(app_server, auth_cookies):
    """POST notification_create without a message returns a failure response."""
    data = api_post(
        app_server,
        auth_cookies,
        "notification_create",
        {
            "title": "No message provided",
        },
    )
    assert data.get("success") is False, f"Expected success=False for missing message: {data}"
    assert "error" in data, f"Expected 'error' key in failure response: {data}"


@pytest.mark.e2e
def test_notifications_clear(app_server, auth_cookies):
    """POST notifications_clear returns success and clears all notifications."""
    data = api_post(app_server, auth_cookies, "notifications_clear", {})
    assert data.get("success") is True, f"Expected success=True from notifications_clear: {data}"

    # Verify history is now empty
    history = api_post(app_server, auth_cookies, "notifications_history", {})
    assert history["count"] == 0, f"Expected 0 notifications after clear, got {history['count']}"


@pytest.mark.e2e
def test_notifications_mark_read_all(app_server, auth_cookies):
    """POST notifications_mark_read with mark_all=True returns success."""
    data = api_post(
        app_server,
        auth_cookies,
        "notifications_mark_read",
        {
            "mark_all": True,
        },
    )
    assert data.get("success") is True, f"Expected success=True: {data}"
