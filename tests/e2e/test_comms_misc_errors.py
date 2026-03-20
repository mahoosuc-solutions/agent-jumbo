"""E2E error-path tests for Telegram, voice, and miscellaneous endpoints.

All tests exercise error or no-op paths only — no external services are required.
"""

import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


def test_telegram_webhook_empty_body(app_server, auth_cookies):
    """POST /telegram_webhook with an empty dict — handler should parse gracefully."""
    try:
        result = api_post(app_server, auth_cookies, "telegram_webhook", {})
        # A 200 response must be a well-formed dict without a bare traceback
        assert isinstance(result, dict)
        body_str = str(result)
        assert "Traceback" not in body_str
    except urllib.error.HTTPError as e:
        body = e._response_body if hasattr(e, "_response_body") else e.read().decode(errors="replace")
        assert "Traceback" not in body
        assert e.code in (200, 400, 403, 500)


def test_telegram_settings_set_invalid(app_server, auth_cookies):
    """POST /telegram_settings_set with settings as a string (not a dict)."""
    try:
        result = api_post(
            app_server,
            auth_cookies,
            "telegram_settings_set",
            {"settings": "not_a_dict"},
        )
        assert isinstance(result, dict)
        body_str = str(result)
        assert "Traceback" not in body_str
        # Expect either an explicit failure or an error message
        if "success" in result:
            assert result["success"] is False or "error" in result
    except urllib.error.HTTPError as e:
        body = e._response_body if hasattr(e, "_response_body") else e.read().decode(errors="replace")
        assert "Traceback" not in body
        assert e.code in (400, 403, 422, 500)


def test_twilio_voice_status_missing_fields(app_server, auth_cookies):
    """POST /twilio_voice_status with an empty body — missing call_sid/status."""
    try:
        result = api_post(app_server, auth_cookies, "twilio_voice_status", {})
        assert isinstance(result, dict)
        body_str = str(result)
        assert "Traceback" not in body_str
        # Must contain some indication of failure when required fields are absent
        assert "error" in result or result.get("success") is False or "message" in result
    except urllib.error.HTTPError as e:
        body = e._response_body if hasattr(e, "_response_body") else e.read().decode(errors="replace")
        assert "Traceback" not in body
        assert e.code in (400, 403, 422, 500)


def test_synthesize_no_text(app_server, auth_cookies):
    """POST /synthesize with no text field — expects a graceful error."""
    try:
        result = api_post(app_server, auth_cookies, "synthesize", {})
        assert isinstance(result, dict)
        body_str = str(result)
        assert "Traceback" not in body_str
        # Must signal failure in some way
        assert "error" in result or result.get("success") is False or "message" in result
    except urllib.error.HTTPError as e:
        body = e._response_body if hasattr(e, "_response_body") else e.read().decode(errors="replace")
        assert "Traceback" not in body
        assert e.code in (400, 403, 422, 500)


def test_passkey_auth_invalid_action(app_server, auth_cookies):
    """POST /passkey_auth with an unrecognised action value."""
    try:
        result = api_post(
            app_server,
            auth_cookies,
            "passkey_auth",
            {"action": "invalid_action_xyz"},
        )
        assert isinstance(result, dict)
        body_str = str(result)
        assert "Traceback" not in body_str
        # Must signal failure for an unknown action
        assert "error" in result or result.get("success") is False or "message" in result
    except urllib.error.HTTPError as e:
        body = e._response_body if hasattr(e, "_response_body") else e.read().decode(errors="replace")
        assert "Traceback" not in body
        assert e.code in (400, 403, 422, 500)
