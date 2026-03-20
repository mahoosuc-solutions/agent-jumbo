import urllib.error

import pytest

from tests.e2e.helpers import api_get, api_post

pytestmark = [pytest.mark.e2e]


def test_life_os_dashboard(app_server, auth_cookies):
    data = api_post(app_server, auth_cookies, "life_os_dashboard", {})
    assert "success" in data
    if data["success"]:
        assert "dashboard" in data
    else:
        assert "error" in data


def test_observability_usage_estimate(app_server, auth_cookies):
    data = api_post(app_server, auth_cookies, "observability_usage_estimate", {})
    assert data["success"] is True
    assert "estimate" in data


def test_security_audit_get(app_server, auth_cookies):
    data = api_post(app_server, auth_cookies, "security_audit_get", {})
    assert "success" in data
    if data["success"]:
        assert "logs" in data
        assert isinstance(data["logs"], list)
    else:
        assert "error" in data


def test_history_get_missing_context(app_server, auth_cookies):
    try:
        data = api_post(app_server, auth_cookies, "history_get", {})
        assert "history" in data
    except urllib.error.HTTPError as e:
        assert e.code in (400, 404, 500)


def test_health_check(app_server, auth_cookies):
    data = api_get(app_server, {}, "health")
    assert "ok" in data
    assert isinstance(data["ok"], bool)
    assert "status" in data
    assert data["status"] in ("healthy", "degraded")
    assert "checks" in data
    assert isinstance(data["checks"], dict)


def test_pause_missing_context(app_server, auth_cookies):
    try:
        data = api_post(app_server, auth_cookies, "pause", {"paused": True})
        assert "message" in data
        assert data["pause"] is True
    except urllib.error.HTTPError as e:
        assert e.code in (400, 404, 500)


def test_model_selector_quick_switch_missing_params(app_server, auth_cookies):
    data = api_post(app_server, auth_cookies, "model_selector_quick_switch", {})
    assert data["success"] is False
    assert "error" in data


def test_restart_endpoint(app_server, auth_cookies):
    try:
        api_post(app_server, auth_cookies, "restart", {})
    except urllib.error.HTTPError as e:
        assert e.code in (500, 502, 503)
