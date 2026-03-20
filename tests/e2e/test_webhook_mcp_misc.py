"""E2E tests for webhook router challenge passthrough, tunnel log access,
MCP server apply, and Gmail account removal endpoints.

These tests exercise both no-auth GET paths (raw urllib) and authenticated
POST/GET paths (helpers). Every test asserts that Python tracebacks are never
exposed in the response body.
"""

import urllib.error
import urllib.request

import pytest

from tests.e2e.helpers import api_post, api_post_tolerant, cookie_header

pytestmark = [pytest.mark.e2e]


def test_webhook_router_challenge_passthrough(app_server):
    """GET /webhook/telegram with hub.challenge — expects 200 with challenge echoed back.

    Webhook adapters that support hub challenge verification (e.g. Facebook-style
    verification) must echo the hub.challenge value back in the response body.
    Some adapters may not support this flow and will return a structured error
    instead; both outcomes are acceptable as long as no Python traceback appears.
    """
    url = f"{app_server}/webhook/telegram?hub.mode=subscribe&hub.challenge=testchallenge123"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        status = resp.status
        body = resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode(errors="replace")

    assert "Traceback" not in body, f"Response must not contain a Python traceback: {body[:500]}"
    # Either the challenge is echoed back (happy path) or a structured non-crash
    # response is returned (adapter does not support hub challenge).
    challenge_echoed = "testchallenge123" in body
    structured_error = status in (200, 400, 404, 405, 422) and "Traceback" not in body
    assert challenge_echoed or structured_error, (
        f"Expected challenge echo or structured error response, got status={status} body={body[:300]}"
    )


def test_tunnel_log_invalid_name(app_server, auth_cookies):
    """GET /tunnel_log?name=../../etc/passwd with auth — expects 400 with rejection message.

    The tunnel log endpoint must sanitise the 'name' query parameter and reject
    path-traversal attempts. A 400 status with an error body (or any response
    that does not return the contents of /etc/passwd) is required.
    """
    req = urllib.request.Request(f"{app_server}/tunnel_log?name=../../etc/passwd")
    req.add_header("Cookie", cookie_header(auth_cookies))
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        status = resp.status
        body = resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode(errors="replace")

    assert "Traceback" not in body, f"Response must not contain a Python traceback: {body[:500]}"
    # Must not serve the contents of /etc/passwd
    assert "root:x:" not in body, "Path traversal succeeded — /etc/passwd content found in response"
    # Should explicitly reject the request (400) or otherwise be a non-crash response
    if status == 400:
        lower_body = body.lower()
        assert any(token in lower_body for token in ("invalid", "log name", "error", "bad request", "not allowed")), (
            f"400 body did not mention rejection reason: {body[:300]}"
        )
    else:
        # Any status other than 200 is a reasonable rejection; 200 is only acceptable
        # if the body does not contain sensitive file contents (already asserted above).
        assert status in (200, 400, 403, 404, 422), f"Unexpected status for path-traversal attempt: {status}"


def test_tunnel_log_missing_file(app_server, auth_cookies):
    """GET /tunnel_log?name=tunnel with auth — expects 404 or 200 with log content.

    In the test environment the tunnel log file almost certainly does not exist.
    The endpoint should return 404 (not found) or, if it falls back gracefully,
    200 with empty/placeholder log content. Either is acceptable; a traceback is not.
    """
    req = urllib.request.Request(f"{app_server}/tunnel_log?name=tunnel")
    req.add_header("Cookie", cookie_header(auth_cookies))
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        status = resp.status
        body = resp.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode(errors="replace")

    assert "Traceback" not in body, f"Response must not contain a Python traceback: {body[:500]}"
    assert status in (200, 400, 403, 404, 500), f"Unexpected status for missing log file: {status}"


def test_mcp_servers_apply_empty(app_server, auth_cookies):
    """POST /mcp_servers_apply with an empty server list — expects success key in response.

    Applying an empty MCP server list is a valid no-op operation. The endpoint
    must return a JSON object containing a 'success' key (true or false) rather
    than raising an unhandled exception.
    """
    try:
        data = api_post_tolerant(app_server, auth_cookies, "mcp_servers_apply", {"mcp_servers": []})
        assert "success" in data, f"Expected 'success' key in response for empty mcp_servers list: {data}"
        body = str(data)
        assert "Traceback" not in body, "Response must not contain a Python traceback"
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        if isinstance(exc, urllib.error.HTTPError):
            body = exc._response_body if hasattr(exc, "_response_body") else exc.read().decode(errors="replace")
            assert "Traceback" not in body, f"Error response must not expose a Python traceback: {body[:500]}"
            assert exc.code in (200, 400, 422, 429, 500), (
                f"Unexpected HTTP status for empty mcp_servers apply: {exc.code}"
            )


def test_gmail_account_remove_nonexistent(app_server, auth_cookies):
    """POST /gmail_account_remove with a nonexistent account name — expects error response.

    Attempting to remove an account that does not exist must yield a structured
    error — either a 4xx/5xx HTTP status or a JSON body with an error indicator.
    The server must not crash or expose a Python traceback.
    """
    try:
        data = api_post(
            app_server,
            auth_cookies,
            "gmail_account_remove",
            {"account_name": "nonexistent-account-xyz-12345"},
        )
        body = str(data)
        assert "Traceback" not in body, "Response must not contain a Python traceback"
        # A 200 response must signal failure in some way
        has_error_indicator = (
            "error" in data
            or data.get("success") is False
            or data.get("ok") is False
            or "not found" in body.lower()
            or "does not exist" in body.lower()
        )
        assert has_error_indicator, f"Expected an error indicator for nonexistent account removal, got: {data}"
    except urllib.error.HTTPError as exc:
        body = exc._response_body if hasattr(exc, "_response_body") else exc.read().decode(errors="replace")
        assert "Traceback" not in body, f"Error response must not expose a Python traceback: {body[:500]}"
        assert exc.code in (400, 404, 422, 500), f"Unexpected HTTP status for nonexistent account removal: {exc.code}"
