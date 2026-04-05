"""E2E tests for the heartbeat API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_get_tolerant as api_get, api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


def test_heartbeat_config_get(app_server, auth_cookies):
    """GET heartbeat config by posting empty body."""
    resp = api_post(app_server, auth_cookies, "heartbeat_config", {})
    assert "enabled" in resp, f"Expected 'enabled' key in response: {resp}"
    assert "running" in resp, f"Expected 'running' key in response: {resp}"


def test_heartbeat_log_returns_list(app_server, auth_cookies):
    """POST heartbeat_log returns a list of log entries."""
    resp = api_post(app_server, auth_cookies, "heartbeat_log", {"limit": 10})
    assert "log" in resp, f"Expected 'log' key in response: {resp}"
    assert isinstance(resp["log"], list), f"Expected 'log' to be a list: {resp}"
    assert "count" in resp, f"Expected 'count' key in response: {resp}"
    assert isinstance(resp["count"], int), f"Expected 'count' to be an int: {resp}"


def test_heartbeat_event_emit_requires_type(app_server, auth_cookies):
    """POST heartbeat_event_emit without event_type should return 400."""
    try:
        api_post(app_server, auth_cookies, "heartbeat_event_emit", {})
        pytest.fail("Expected 400 HTTPError but request succeeded")
    except urllib.error.HTTPError as e:
        assert e.code == 400, f"Expected 400 but got {e.code}"


def test_heartbeat_event_emit_valid(app_server, auth_cookies):
    """POST heartbeat_event_emit with valid event_type succeeds."""
    resp = api_post(
        app_server,
        auth_cookies,
        "heartbeat_event_emit",
        {"event_type": "test_e2e_event", "payload": {"key": "value"}},
    )
    assert resp["status"] == "emitted", f"Expected status 'emitted': {resp}"
    assert "event" in resp, f"Expected 'event' key in response: {resp}"
    assert isinstance(resp["event"], dict), f"Expected 'event' to be a dict: {resp}"


def test_heartbeat_triggers_list(app_server, auth_cookies):
    """GET heartbeat_triggers_list returns a list of triggers."""
    resp = api_get(app_server, auth_cookies, "heartbeat_triggers_list")
    assert "triggers" in resp, f"Expected 'triggers' key in response: {resp}"
    assert isinstance(resp["triggers"], list), f"Expected 'triggers' to be a list: {resp}"


def test_heartbeat_trigger_crud_lifecycle(app_server, auth_cookies):
    """Full CRUD lifecycle: create, update, delete a heartbeat trigger."""
    # Create
    create_resp = api_post(
        app_server,
        auth_cookies,
        "heartbeat_trigger_create",
        {
            "type": "event",
            "config": {"event_type": "e2e_test"},
            "items": [],
            "enabled": True,
        },
    )
    assert create_resp["status"] == "created", f"Expected status 'created': {create_resp}"
    assert "trigger" in create_resp, f"Expected 'trigger' key in response: {create_resp}"
    assert isinstance(create_resp["trigger"], dict), f"Expected 'trigger' to be a dict: {create_resp}"
    trigger_id = create_resp["trigger"]["id"]

    # Update
    update_resp = api_post(
        app_server,
        auth_cookies,
        "heartbeat_trigger_update",
        {"id": trigger_id, "enabled": False},
    )
    assert update_resp["status"] == "updated", f"Expected status 'updated': {update_resp}"

    # Delete
    delete_resp = api_post(
        app_server,
        auth_cookies,
        "heartbeat_trigger_delete",
        {"id": trigger_id},
    )
    assert delete_resp["status"] == "deleted", f"Expected status 'deleted': {delete_resp}"


def test_heartbeat_trigger_create_invalid_type(app_server, auth_cookies):
    """POST heartbeat_trigger_create with invalid type should return 400."""
    try:
        api_post(
            app_server,
            auth_cookies,
            "heartbeat_trigger_create",
            {"type": "invalid_type_xyz"},
        )
        pytest.fail("Expected 400 HTTPError but request succeeded")
    except urllib.error.HTTPError as e:
        assert e.code == 400, f"Expected 400 but got {e.code}"
