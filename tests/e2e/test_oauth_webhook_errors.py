"""E2E tests for OAuth callback and webhook error paths.

These tests cover error paths only — no external OAuth providers or webhook
sources are required. Every endpoint tested here is expected to return a
well-formed error response (4xx/5xx) rather than succeed.
"""

import urllib.error
import urllib.request

import pytest

from tests.e2e.helpers import api_post, cookie_header

pytestmark = [pytest.mark.e2e]


def test_calendar_oauth_callback_missing_account_id(app_server, auth_cookies):
    """POST /calendar_oauth_callback with empty body — expects error, not a crash.

    The endpoint requires at minimum an account_id to process an OAuth callback.
    Sending an empty body must yield a structured error response, not a traceback.
    """
    try:
        result = api_post(app_server, auth_cookies, "calendar_oauth_callback", {})
        # If the endpoint returns 200, it must be a structured error dict
        assert "error" in result or result.get("success") is False, (
            f"Expected error key or success=False in response: {result}"
        )
        body = str(result)
        assert "Traceback" not in body, "Response must not contain a Python traceback"
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode(errors="replace")
        assert status in (400, 403, 404, 422, 500), f"Expected a reasonable error status code, got {status}"
        assert "Traceback" not in body, "Error response must not expose a Python traceback"


def test_gmail_oauth_callback_missing_code(app_server, auth_cookies):
    """GET /gmail_oauth_callback with no query params — expects 400 or error mentioning code/state.

    A real OAuth callback would include 'code' and 'state' query parameters.
    Hitting the endpoint bare must produce a well-formed error, not a server crash.
    """
    req = urllib.request.Request(f"{app_server}/gmail_oauth_callback")
    req.add_header("Cookie", cookie_header(auth_cookies))
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        status = resp.status
        body = resp.read().decode(errors="replace")
        # A 200 response to a bare callback is unusual but must not be a traceback
        assert "Traceback" not in body, "Response must not contain a Python traceback"
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode(errors="replace")
        assert status in (400, 403, 404, 422, 500), f"Expected a reasonable error status code, got {status}"
        assert "Traceback" not in body, "Error response must not expose a Python traceback"
        # The error body should hint at what was missing (code or state) when possible
        lower_body = body.lower()
        # Acceptable if it mentions the missing param or is a generic auth/not-found error
        acceptable = any(
            token in lower_body
            for token in ("code", "state", "error", "invalid", "missing", "unauthorized", "not found", "oauth")
        )
        assert acceptable or status in (403, 404), (
            f"Error body did not mention expected tokens for status {status}: {body[:300]}"
        )


def test_finance_oauth_callback_missing_account_id(app_server, auth_cookies):
    """POST /finance_oauth_callback with empty body — expects error response.

    The finance OAuth callback requires provider context / account_id.
    An empty body must produce a structured error, not a traceback or unhandled exception.
    """
    try:
        result = api_post(app_server, auth_cookies, "finance_oauth_callback", {})
        assert "error" in result or result.get("success") is False, (
            f"Expected error key or success=False in response: {result}"
        )
        body = str(result)
        assert "Traceback" not in body, "Response must not contain a Python traceback"
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode(errors="replace")
        assert status in (400, 403, 404, 422, 500), f"Expected a reasonable error status code, got {status}"
        assert "Traceback" not in body, "Error response must not expose a Python traceback"


def test_pms_webhook_missing_provider(app_server, auth_cookies):
    """POST /pms_webhook_receive with empty body — expects error for missing provider_id/payload.

    The PMS webhook handler requires at minimum a provider_id and a payload.
    Omitting both must return a structured error rather than crashing.
    """
    try:
        result = api_post(app_server, auth_cookies, "pms_webhook_receive", {})
        assert "error" in result or result.get("success") is False or result.get("status") == "error", (
            f"Expected error indicator in response: {result}"
        )
        body = str(result)
        assert "Traceback" not in body, "Response must not contain a Python traceback"
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode(errors="replace")
        assert status in (400, 403, 404, 422, 500), f"Expected a reasonable error status code, got {status}"
        assert "Traceback" not in body, "Error response must not expose a Python traceback"


def test_webhook_router_unknown_channel(app_server, auth_cookies):
    """GET /webhook/nonexistent_channel_xyz — expects 404 or error response.

    Routing to a channel name that does not exist must yield a 404 or a structured
    error. The server must not crash or expose internal details.
    """
    req = urllib.request.Request(f"{app_server}/webhook/nonexistent_channel_xyz")
    req.add_header("Cookie", cookie_header(auth_cookies))
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        status = resp.status
        body = resp.read().decode(errors="replace")
        # A 200 here is only acceptable if the body signals the channel was not found
        lower_body = body.lower()
        assert any(token in lower_body for token in ("error", "not found", "unknown", "invalid")), (
            f"200 response for unknown channel must signal an error in the body: {body[:300]}"
        )
        assert "Traceback" not in body, "Response must not contain a Python traceback"
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode(errors="replace")
        assert status in (400, 403, 404, 405, 422, 500), (
            f"Expected a reasonable error status code for unknown channel, got {status}"
        )
        assert "Traceback" not in body, "Error response must not expose a Python traceback"
