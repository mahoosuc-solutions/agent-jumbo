import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_download_work_dir_file_missing_path(app_server, auth_cookies):
    """POST to download_work_dir_file with no path — handler raises ValueError, expect 500."""
    try:
        data = api_post(app_server, auth_cookies, "download_work_dir_file", {})
        assert data.get("success") is False or "error" in data, f"Expected error, got: {data}"
    except urllib.error.HTTPError as exc:
        assert exc.code == 500, f"Expected error code 500, got {exc.code}"


def test_image_get_missing_path(app_server, auth_cookies):
    """POST to image_get with no path — handler raises ValueError, expect 500."""
    try:
        data = api_post(app_server, auth_cookies, "image_get", {})
        assert data.get("success") is False or "error" in data, f"Expected error, got: {data}"
    except urllib.error.HTTPError as exc:
        assert exc.code == 500, f"Expected error code 500, got {exc.code}"


def test_chat_load_missing_chats(app_server, auth_cookies):
    """POST to chat_load with no chats key — handler raises Exception, expect 500."""
    try:
        data = api_post(app_server, auth_cookies, "chat_load", {})
        assert data.get("success") is False or "error" in data, f"Expected error, got: {data}"
    except urllib.error.HTTPError as exc:
        assert exc.code == 500, f"Expected error code 500, got {exc.code}"


def test_api_log_get_missing_context(app_server, auth_cookies):
    """POST to api_log_get with no context_id — handler returns 400 with message, expect 400."""
    try:
        data = api_post(app_server, auth_cookies, "api_log_get", {})
        assert data.get("success") is False or "error" in data, f"Expected error, got: {data}"
    except urllib.error.HTTPError as exc:
        assert exc.code == 400, f"Expected error code 400, got {exc.code}"


def test_profile_sync_unknown_action(app_server, auth_cookies):
    """POST to profile_sync with unknown action — handler should return error."""
    try:
        data = api_post(app_server, auth_cookies, "profile_sync", {"action": "unknown_action_xyz"})
        assert data.get("success") is False or "error" in data, f"Expected error, got: {data}"
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 500), f"Expected error code 400 or 500, got {exc.code}"
