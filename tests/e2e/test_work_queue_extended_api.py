import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_work_queue_item_update_missing_id(app_server, auth_cookies):
    try:
        result = api_post(app_server, auth_cookies, "work_queue_item_update", {})
    except urllib.error.HTTPError as e:
        pytest.fail(f"Unexpected HTTP error: {e}")
    assert result["success"] is False
    assert "item_id" in result["error"]


def test_work_queue_item_bulk_empty_ids(app_server, auth_cookies):
    try:
        result = api_post(
            app_server,
            auth_cookies,
            "work_queue_item_bulk",
            {"action": "queue", "item_ids": []},
        )
    except urllib.error.HTTPError as e:
        pytest.fail(f"Unexpected HTTP error: {e}")
    assert result["success"] is False
    assert "error" in result


def test_work_queue_item_execute_missing_id(app_server, auth_cookies):
    try:
        result = api_post(app_server, auth_cookies, "work_queue_item_execute", {})
    except urllib.error.HTTPError as e:
        pytest.fail(f"Unexpected HTTP error: {e}")
    assert result["success"] is False
    assert "item_id" in result["error"]
