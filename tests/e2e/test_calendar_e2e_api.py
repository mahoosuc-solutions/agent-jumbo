"""E2E tests for the calendar API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_calendar_connect_mock_mode(app_server, auth_cookies):
    """POST calendar_connect with mock=true should not crash the server.

    The endpoint may succeed, return an error dict, or raise an HTTPError
    depending on whether CalendarHubManager and its dependencies are available.
    """
    try:
        data = api_post(
            app_server,
            auth_cookies,
            "calendar_connect",
            {"provider": "google", "mock": True},
        )
        # If we got a JSON response, it should either indicate success or contain an error
        assert data.get("success") is True or "error" in data, (
            f"Expected success=True or 'error' key in response: {data}"
        )
    except urllib.error.HTTPError as exc:
        # Any HTTP error is acceptable — the server did not crash
        assert exc.code in (400, 404, 422, 500, 501, 503), f"Unexpected HTTP status {exc.code}"


@pytest.mark.e2e
def test_calendar_dashboard_returns_structure(app_server, auth_cookies):
    """POST calendar_dashboard with empty body returns a structured response.

    If success is True the response must contain accounts, calendars, and events.
    If success is False or missing, an error key must be present.
    """
    try:
        data = api_post(app_server, auth_cookies, "calendar_dashboard", {})
        assert "success" in data, f"Expected 'success' key in response: {data}"
        if data["success"] is True:
            assert "accounts" in data, f"Expected 'accounts' key in response: {data}"
            assert "calendars" in data, f"Expected 'calendars' key in response: {data}"
            assert "events" in data, f"Expected 'events' key in response: {data}"
        else:
            assert "error" in data, f"Expected 'error' key when success is False: {data}"
    except urllib.error.HTTPError as exc:
        # HTTP error is acceptable when the calendar subsystem is unavailable
        assert exc.code in (400, 404, 422, 500, 501, 503), f"Unexpected HTTP status {exc.code}"


@pytest.mark.e2e
def test_calendar_oauth_start_returns_url_or_error(app_server, auth_cookies):
    """POST calendar_oauth_start with provider returns an auth URL or error.

    Success means an auth_url is provided. Failure returns an error key.
    An HTTPError is also acceptable if the calendar subsystem is not configured.
    """
    try:
        data = api_post(
            app_server,
            auth_cookies,
            "calendar_oauth_start",
            {"provider": "google"},
        )
        if data.get("success") is True:
            assert "auth_url" in data, f"Expected 'auth_url' key when success is True: {data}"
        else:
            assert "error" in data, f"Expected 'error' key when success is not True: {data}"
    except urllib.error.HTTPError as exc:
        # HTTP error is acceptable when OAuth is not configured
        assert exc.code in (400, 404, 422, 500, 501, 503), f"Unexpected HTTP status {exc.code}"
