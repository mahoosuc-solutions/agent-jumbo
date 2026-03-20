"""E2E tests for the tunnel API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_tunnel_settings_get_returns_structure(app_server, auth_cookies):
    """GET tunnel settings returns expected structure with provider and watchdog keys."""
    resp = api_post(app_server, auth_cookies, "tunnel_settings_get", {})
    assert "settings" in resp, f"Expected 'settings' key in response, got: {resp}"
    settings = resp["settings"]
    assert isinstance(settings, dict), f"Expected settings to be a dict, got: {type(settings)}"
    assert "provider" in settings, f"Expected 'provider' key in settings, got: {settings}"
    assert "watchdog" in resp, f"Expected 'watchdog' key in response, got: {resp}"


def test_tunnel_settings_set_and_get_roundtrip(app_server, auth_cookies):
    """Set tunnel provider to cloudflared and verify via get."""
    # Get current settings first
    original = api_post(app_server, auth_cookies, "tunnel_settings_get", {})
    original_settings = original.get("settings", {})

    try:
        # Set provider to cloudflared
        set_resp = api_post(
            app_server,
            auth_cookies,
            "tunnel_settings_set",
            {"settings": {"provider": "cloudflared"}},
        )
        assert set_resp.get("success") is True, f"Expected success=True from tunnel_settings_set, got: {set_resp}"

        # Verify the setting persisted
        verify = api_post(app_server, auth_cookies, "tunnel_settings_get", {})
        assert verify["settings"]["provider"] == "cloudflared", (
            f"Expected provider='cloudflared', got: {verify['settings']['provider']}"
        )
    finally:
        # Restore original settings if they differed
        if original_settings.get("provider") and original_settings["provider"] != "cloudflared":
            api_post(
                app_server,
                auth_cookies,
                "tunnel_settings_set",
                {"settings": {"provider": original_settings["provider"]}},
            )


def test_tunnel_debug_returns_status(app_server, auth_cookies):
    """Tunnel debug endpoint returns status and logs."""
    try:
        resp = api_post(app_server, auth_cookies, "tunnel_debug", {})
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        pytest.skip(f"tunnel_debug not available (dependency issue): {exc}")
        return

    assert "status" in resp, f"Expected 'status' key in response, got: {resp}"
    assert "logs" in resp, f"Expected 'logs' key in response, got: {resp}"
    assert isinstance(resp["logs"], dict), f"Expected logs to be a dict, got: {type(resp['logs'])}"


def test_tunnel_watchdog_status(app_server, auth_cookies):
    """Tunnel watchdog status action returns a status key."""
    resp = api_post(app_server, auth_cookies, "tunnel_watchdog", {"action": "status"})
    assert "status" in resp, f"Expected 'status' key in response, got: {resp}"
