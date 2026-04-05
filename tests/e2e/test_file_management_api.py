import urllib.error

import pytest

from tests.e2e.helpers import api_get_tolerant as api_get, api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


def test_get_work_dir_files(app_server, auth_cookies):
    response = api_get(app_server, auth_cookies, "get_work_dir_files?path=$WORK_DIR")
    assert "data" in response


def test_chat_files_path_get_missing_context(app_server, auth_cookies):
    try:
        api_post(app_server, auth_cookies, "chat_files_path_get", {})
        pytest.fail("Expected HTTPError 500 but no exception was raised")
    except urllib.error.HTTPError as e:
        assert e.code == 500


def test_delete_work_dir_file_nonexistent(app_server, auth_cookies):
    try:
        api_post(app_server, auth_cookies, "delete_work_dir_file", {"path": "/nonexistent_file_xyz_999.txt"})
        pytest.fail("Expected HTTPError 500 but no exception was raised")
    except urllib.error.HTTPError as e:
        assert e.code == 500


def test_file_info_nonexistent(app_server, auth_cookies):
    response = api_post(app_server, auth_cookies, "file_info", {"path": "/nonexistent_file_xyz_999.txt"})
    assert "exists" in response
    assert response["exists"] is False


def test_platform_documentation_get(app_server, auth_cookies):
    response = api_post(app_server, auth_cookies, "platform_documentation_get", {})
    assert "success" in response
    if response["success"]:
        assert "content" in response
        assert isinstance(response["content"], str)
    else:
        assert "error" in response
