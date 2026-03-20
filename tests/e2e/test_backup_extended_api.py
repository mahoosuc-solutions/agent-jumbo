import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_backup_inspect_missing_file(app_server, auth_cookies):
    result = api_post(app_server, auth_cookies, "backup_inspect", {})
    assert result.get("success") is False
    error = result.get("error", "")
    assert "backup" in error.lower() or "file" in error.lower()


def test_backup_restore_preview_missing_file(app_server, auth_cookies):
    result = api_post(app_server, auth_cookies, "backup_restore_preview", {})
    assert result.get("success") is False
    assert "error" in result


def test_security_ops_unknown_action(app_server, auth_cookies):
    result = api_post(app_server, auth_cookies, "security_ops", {"action": "unknown_op"})
    assert result.get("success") is False
    assert "error" in result


def test_security_tool_action_missing_params(app_server, auth_cookies):
    result = api_post(app_server, auth_cookies, "security_tool_action", {})
    assert result.get("success") is False
    error = result.get("error", "")
    assert "Missing" in error


def test_project_validation_missing_name(app_server, auth_cookies):
    result = api_post(app_server, auth_cookies, "project_validation", {})
    assert result.get("ok") is False or result.get("success") is False
    error = result.get("error", "")
    assert "project_name" in error
