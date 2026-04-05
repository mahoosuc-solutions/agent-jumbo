"""E2E tests for gateway API endpoints: gateway_status and gateway_webhook."""

import json
import urllib.error
import urllib.request

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


def _raw_post(url: str, body: dict):
    """POST JSON to a URL without auth or CSRF headers. Returns the response object."""
    payload = json.dumps(body).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(req, timeout=15)


def test_gateway_status_returns_channels(app_server, auth_cookies):
    """POST gateway_status with empty body returns a dict with a 'channels' list."""
    data = api_post(app_server, auth_cookies, "gateway_status", {})
    assert "channels" in data, f"Expected 'channels' key in response: {data}"
    assert isinstance(data["channels"], list), f"Expected 'channels' to be a list: {data}"


def test_gateway_status_returns_gateway_info(app_server, auth_cookies):
    """POST gateway_status with empty body returns a dict with a 'gateway' key."""
    data = api_post(app_server, auth_cookies, "gateway_status", {})
    assert "gateway" in data, f"Expected 'gateway' key in response: {data}"


def test_gateway_status_unknown_channel(app_server, auth_cookies):
    """POST gateway_status with an unknown channel name returns an error key."""
    data = api_post(app_server, auth_cookies, "gateway_status", {"channel": "nonexistent_xyz_999"})
    assert "error" in data, f"Expected 'error' key in response for unknown channel: {data}"


def test_webhook_missing_channel_param(app_server, auth_cookies):
    """POST gateway_webhook without ?channel= returns 400.

    Uses raw urllib directly since this endpoint requires no auth or CSRF.
    """
    try:
        _raw_post(f"{app_server}/gateway_webhook", {})
        raise AssertionError("Expected 400 error, got 200")
    except urllib.error.HTTPError as exc:
        assert exc.code == 400, f"Expected 400, got {exc.code}"


def test_webhook_unknown_channel(app_server, auth_cookies):
    """POST gateway_webhook with an unknown channel name returns 404.

    Uses raw urllib directly since this endpoint requires no auth or CSRF.
    """
    try:
        _raw_post(f"{app_server}/gateway_webhook?channel=nonexistent_xyz_999", {"test": True})
        raise AssertionError("Expected 404 error, got 200")
    except urllib.error.HTTPError as exc:
        assert exc.code == 404, f"Expected 404, got {exc.code}"
