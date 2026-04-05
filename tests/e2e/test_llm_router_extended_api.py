import urllib.error

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


def test_llm_router_discover(app_server, auth_cookies):
    data = api_post(app_server, auth_cookies, "llm_router_discover", {})
    assert data["success"] is True
    assert isinstance(data["models"], list)
    assert isinstance(data["count"], int)
    assert isinstance(data["providers"], list)


def test_llm_router_select(app_server, auth_cookies):
    data = api_post(app_server, auth_cookies, "llm_router_select", {"role": "chat"})
    assert "success" in data
    if data["success"] is True:
        assert "model" in data
        assert isinstance(data["model"], dict)
        assert "selectionCriteria" in data["model"]
    else:
        assert "error" in data


def test_llm_router_fallback_missing_params(app_server, auth_cookies):
    try:
        data = api_post(app_server, auth_cookies, "llm_router_fallback", {})
        assert data["success"] is False
        assert "error" in data
    except urllib.error.HTTPError as e:
        assert e.code in (400, 422)


def test_llm_router_rules_list(app_server, auth_cookies):
    data = api_post(app_server, auth_cookies, "llm_router_rules", {"action": "list"})
    assert data["success"] is True
    assert isinstance(data["rules"], list)


def test_llm_router_auto_configure(app_server, auth_cookies):
    data = api_post(app_server, auth_cookies, "llm_router_auto_configure", {})
    assert "success" in data
    if data["success"] is True:
        assert "discoveredModels" in data
    else:
        assert "error" in data
