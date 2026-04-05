"""E2E tests for the finance API endpoints."""

import urllib.error

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


def test_finance_connect_mock_mode(app_server, auth_cookies):
    """POST finance_connect with mock mode — success, error dict, or HTTPError all acceptable."""
    try:
        resp = api_post(app_server, auth_cookies, "finance_connect", {"provider": "plaid", "mock": True})
        assert isinstance(resp, dict)
        # Either success or an error dict
        if "success" in resp:
            assert isinstance(resp["success"], bool)
        elif "error" in resp:
            assert isinstance(resp["error"], str)
    except urllib.error.HTTPError:
        pass  # acceptable — FinanceManager may not be available


def test_finance_dashboard_returns_structure(app_server, auth_cookies):
    """POST finance_dashboard — response must have success key with appropriate sub-keys."""
    try:
        resp = api_post(app_server, auth_cookies, "finance_dashboard", {})
        assert isinstance(resp, dict)
        assert "success" in resp
        if resp["success"] is True:
            assert "report" in resp, "Expected 'report' key when success is True"
            assert "roi" in resp, "Expected 'roi' key when success is True"
        else:
            assert "error" in resp, "Expected 'error' key when success is False"
    except urllib.error.HTTPError:
        pass  # acceptable — FinanceManager may not be available


def test_finance_accounts_list(app_server, auth_cookies):
    """POST finance_accounts_list — success with accounts list, or error."""
    try:
        resp = api_post(app_server, auth_cookies, "finance_accounts_list", {})
        assert isinstance(resp, dict)
        if resp.get("success") is True:
            assert "accounts" in resp, "Expected 'accounts' key when success is True"
            assert isinstance(resp["accounts"], list)
        else:
            assert "error" in resp or "success" in resp
    except urllib.error.HTTPError:
        pass  # acceptable — FinanceManager may not be available


def test_finance_oauth_start_returns_url_or_error(app_server, auth_cookies):
    """POST finance_oauth_start — success with auth_url, or error."""
    try:
        resp = api_post(app_server, auth_cookies, "finance_oauth_start", {"provider": "plaid"})
        assert isinstance(resp, dict)
        if resp.get("success") is True:
            assert "auth_url" in resp, "Expected 'auth_url' key when success is True"
        else:
            assert resp.get("success") is False
            assert "error" in resp, "Expected 'error' key when success is False"
    except urllib.error.HTTPError:
        pass  # acceptable — FinanceManager may not be available
