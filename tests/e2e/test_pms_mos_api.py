import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


def test_pms_settings_set_missing_action(app_server, auth_cookies):
    """POST pms_settings_set with empty body — handler returns error listing valid_actions."""
    resp = api_post(app_server, auth_cookies, "pms_settings_set", {})
    assert resp.get("success") is False or "error" in resp


def test_pms_settings_set_add_missing_provider_id(app_server, auth_cookies):
    """POST pms_settings_set with action=add but no provider_id — handler returns error."""
    resp = api_post(app_server, auth_cookies, "pms_settings_set", {"action": "add"})
    has_error = "error" in resp or resp.get("status") not in (None, "success")
    assert has_error


def test_mos_test_connection_unknown_integration(app_server, auth_cookies):
    """POST mos_test_connection with unknown integration — returns success=False and error."""
    resp = api_post(app_server, auth_cookies, "mos_test_connection", {"integration": "badintegration"})
    assert resp.get("success") is False
    assert "error" in resp


def test_mos_sync_history_unknown_integration(app_server, auth_cookies):
    """POST mos_sync_history with unknown integration — returns success=False and error."""
    resp = api_post(app_server, auth_cookies, "mos_sync_history", {"integration": "badintegration"})
    assert resp.get("success") is False
    assert "error" in resp


def test_mos_sync_status(app_server, auth_cookies):
    """POST mos_sync_status with empty body — always returns a success key."""
    resp = api_post(app_server, auth_cookies, "mos_sync_status", {})
    assert "success" in resp
    if resp["success"]:
        assert "syncs" in resp
    else:
        assert "error" in resp
