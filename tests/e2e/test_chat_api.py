"""E2E tests for the chat API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_chat_create_returns_ctxid(app_server, auth_cookies):
    """POST chat_create with empty body returns a response with 'ok' and 'ctxid' keys."""
    data = api_post(app_server, auth_cookies, "chat_create", {})
    assert "ok" in data, f"Expected 'ok' key in response: {data}"
    assert "ctxid" in data, f"Expected 'ctxid' key in response: {data}"


@pytest.mark.e2e
def test_chat_create_with_new_context(app_server, auth_cookies):
    """POST chat_create with a specific new_context returns that context id."""
    data = api_post(app_server, auth_cookies, "chat_create", {"new_context": "test_ctx_e2e_001"})
    assert "ctxid" in data, f"Expected 'ctxid' key in response: {data}"
    assert data["ctxid"] == "test_ctx_e2e_001", f"Expected ctxid to be 'test_ctx_e2e_001', got {data['ctxid']!r}"


@pytest.mark.e2e
def test_chat_readiness_returns_checks(app_server, auth_cookies):
    """POST chat_readiness returns ready status, checks list, provider, model, and backend."""
    data = api_post(app_server, auth_cookies, "chat_readiness", {})
    assert "ready" in data, f"Expected 'ready' key in response: {data}"
    assert isinstance(data["ready"], bool), f"Expected 'ready' to be a bool, got: {type(data['ready'])}"
    assert "checks" in data, f"Expected 'checks' key in response: {data}"
    assert isinstance(data["checks"], list), f"Expected 'checks' to be a list, got: {type(data['checks'])}"
    assert "provider" in data, f"Expected 'provider' key in response: {data}"
    assert "model" in data, f"Expected 'model' key in response: {data}"
    assert "backend" in data, f"Expected 'backend' key in response: {data}"


@pytest.mark.e2e
def test_chat_reset_succeeds(app_server, auth_cookies):
    """Create a context, then POST chat_reset to reset it."""
    create_data = api_post(app_server, auth_cookies, "chat_create", {})
    ctxid = create_data["ctxid"]
    data = api_post(app_server, auth_cookies, "chat_reset", {"context": ctxid})
    assert "message" in data, f"Expected 'message' key in response: {data}"


@pytest.mark.e2e
def test_chat_export_requires_ctxid(app_server, auth_cookies):
    """POST chat_export with no ctxid raises an HTTPError (500)."""
    try:
        api_post(app_server, auth_cookies, "chat_export", {})
        pytest.fail("Expected HTTPError for chat_export with no ctxid")
    except urllib.error.HTTPError as exc:
        assert exc.code == 500, f"Expected HTTP 500 for missing ctxid, got {exc.code}"


@pytest.mark.e2e
def test_chat_export_with_valid_context(app_server, auth_cookies):
    """Create a context, then POST chat_export with that ctxid."""
    create_data = api_post(app_server, auth_cookies, "chat_create", {})
    ctxid = create_data["ctxid"]
    data = api_post(app_server, auth_cookies, "chat_export", {"ctxid": ctxid})
    assert "content" in data, f"Expected 'content' key in response: {data}"
    assert "ctxid" in data, f"Expected 'ctxid' key in response: {data}"


@pytest.mark.e2e
def test_chat_remove_succeeds(app_server, auth_cookies):
    """Create a context, then POST chat_remove to remove it."""
    create_data = api_post(app_server, auth_cookies, "chat_create", {})
    ctxid = create_data["ctxid"]
    data = api_post(app_server, auth_cookies, "chat_remove", {"context": ctxid})
    assert "message" in data, f"Expected 'message' key in response: {data}"
