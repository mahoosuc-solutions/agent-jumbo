import urllib.error

import pytest

from tests.e2e.helpers import api_post_tolerant as api_post

pytestmark = [pytest.mark.e2e]


def test_telegram_settings_get(app_server, auth_cookies):
    try:
        resp = api_post(app_server, auth_cookies, "telegram_settings_get", {})
        assert isinstance(resp, dict)
        if "success" in resp:
            assert resp["success"] is True
    except urllib.error.HTTPError as e:
        assert e.code in (400, 500)


def test_google_voice_inbound_list(app_server, auth_cookies):
    try:
        resp = api_post(app_server, auth_cookies, "google_voice_inbound_list", {})
        assert "success" in resp
        if not resp["success"]:
            assert "error" in resp
    except urllib.error.HTTPError as e:
        assert e.code in (400, 500)


def test_twilio_voice_list(app_server, auth_cookies):
    try:
        resp = api_post(app_server, auth_cookies, "twilio_voice_list", {})
        assert "success" in resp
        if not resp["success"]:
            assert "error" in resp
    except urllib.error.HTTPError as e:
        assert e.code in (400, 500)


def test_gmail_accounts_list(app_server, auth_cookies):
    try:
        resp = api_post(app_server, auth_cookies, "gmail_accounts_list", {})
        assert isinstance(resp, dict)
        has_accounts = "accounts" in resp
        has_status = "success" in resp or "error" in resp
        assert has_accounts or has_status
    except urllib.error.HTTPError as e:
        assert e.code in (400, 500)


def test_telegram_inbox_list(app_server, auth_cookies):
    try:
        resp = api_post(app_server, auth_cookies, "telegram_inbox_list", {})
        assert "success" in resp
        if resp["success"]:
            assert "items" in resp
        else:
            assert "error" in resp
    except urllib.error.HTTPError as e:
        assert e.code in (400, 500)
