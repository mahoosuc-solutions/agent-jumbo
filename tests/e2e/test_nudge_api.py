"""E2E tests for the nudge and prompt enhance API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_nudge_requires_ctxid(app_server, auth_cookies):
    """POST nudge with no ctxid raises an HTTPError (500)."""
    try:
        api_post(app_server, auth_cookies, "nudge", {})
        pytest.fail("Expected HTTPError for nudge with no ctxid")
    except urllib.error.HTTPError as exc:
        assert exc.code == 500, f"Expected HTTP 500 for missing ctxid, got {exc.code}"


@pytest.mark.e2e
def test_nudge_with_valid_context(app_server, auth_cookies):
    """Create a context, then POST nudge with that ctxid."""
    create_data = api_post(app_server, auth_cookies, "chat_create", {})
    ctxid = create_data["ctxid"]
    data = api_post(app_server, auth_cookies, "nudge", {"ctxid": ctxid})
    assert "message" in data, f"Expected 'message' key in response: {data}"
    assert "ctxid" in data, f"Expected 'ctxid' key in response: {data}"


@pytest.mark.e2e
def test_prompt_enhance_get_no_context(app_server, auth_cookies):
    """POST prompt_enhance_get with a nonexistent context returns data=None."""
    data = api_post(app_server, auth_cookies, "prompt_enhance_get", {"context": "nonexistent_ctx_prompt_e2e"})
    assert "data" in data, f"Expected 'data' key in response: {data}"
