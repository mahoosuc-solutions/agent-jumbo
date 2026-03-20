"""E2E tests for the LLM router API endpoints.

Covers model listing, defaults management, dashboard, and usage statistics.
"""

import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_llm_router_models_list(app_server, auth_cookies):
    """POST llm_router_models with empty body returns success and a models list."""
    data = api_post(app_server, auth_cookies, "llm_router_models", {})
    assert "success" in data or "ok" in data, f"Expected 'success' or 'ok' key in response: {data}"
    assert "models" in data, f"Expected 'models' key in response: {data}"
    assert isinstance(data["models"], list), f"Expected 'models' to be a list, got: {type(data['models'])}"


@pytest.mark.e2e
def test_llm_router_get_defaults(app_server, auth_cookies):
    """POST llm_router_get_defaults with empty body returns success and a defaults dict."""
    data = api_post(app_server, auth_cookies, "llm_router_get_defaults", {})
    assert "success" in data or "ok" in data, f"Expected 'success' or 'ok' key in response: {data}"
    assert "defaults" in data, f"Expected 'defaults' key in response: {data}"
    assert isinstance(data["defaults"], dict), (
        f"Expected 'defaults' to be a dict, got: {type(data['defaults'])}"
    )


@pytest.mark.e2e
def test_llm_router_dashboard(app_server, auth_cookies):
    """POST llm_router_dashboard with empty body returns success and models data."""
    data = api_post(app_server, auth_cookies, "llm_router_dashboard", {})
    assert "success" in data or "ok" in data, f"Expected 'success' or 'ok' key in response: {data}"
    assert "models" in data, f"Expected 'models' key in response: {data}"


@pytest.mark.e2e
def test_llm_router_usage(app_server, auth_cookies):
    """POST llm_router_usage with empty body returns success and stats."""
    data = api_post(app_server, auth_cookies, "llm_router_usage", {})
    assert "success" in data or "ok" in data, f"Expected 'success' or 'ok' key in response: {data}"
    assert "stats" in data or "usage" in data, (
        f"Expected 'stats' or 'usage' key in response: {data}"
    )


@pytest.mark.e2e
def test_llm_router_set_invalid_model(app_server, auth_cookies):
    """POST llm_router_set_default with a fake model name returns an error."""
    body = {
        "role": "chat",
        "provider": "fake_provider",
        "model": "nonexistent-model-xyz-999",
    }
    try:
        data = api_post(app_server, auth_cookies, "llm_router_set_default", body)
        # If the server returns 200, it should indicate failure
        assert (
            data.get("success") is False
            or data.get("ok") is False
            or "error" in data
        ), f"Expected error for invalid model, got: {data}"
    except urllib.error.HTTPError as exc:
        assert exc.code in (400, 404, 422, 500), (
            f"Unexpected HTTP status {exc.code}: {getattr(exc, '_response_body', '')}"
        )
