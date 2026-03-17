"""E2E security tests — OWASP-style probes for Agent Zero web UI."""

import http.client
import json
import urllib.parse
import urllib.request

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.security]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cookie_header(auth_cookies: dict) -> str:
    return "; ".join(f"{k}={v}" for k, v in auth_cookies.items())


def _get(url: str, headers: dict | None = None, timeout: int = 10):
    """Build a GET request, open it, return (status, headers, body)."""
    req = urllib.request.Request(url, method="GET")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, dict(resp.headers), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", errors="replace")


def _post(url: str, data: bytes | None = None, headers: dict | None = None, timeout: int = 10):
    """Build a POST request, open it, return (status, headers, body)."""
    req = urllib.request.Request(url, data=data, method="POST")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, dict(resp.headers), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode("utf-8", errors="replace")


def _get_csrf_token(base_url: str, cookies: dict) -> str:
    """Fetch a CSRF token from /csrf_token endpoint."""
    status, _hdrs, body = _get(
        f"{base_url}/csrf_token",
        headers={"Cookie": _cookie_header(cookies)},
    )
    assert status == 200, f"Expected 200 from /csrf_token, got {status}: {body}"
    data = json.loads(body)
    assert data.get("ok"), f"CSRF endpoint returned ok=false: {data}"
    return data["token"]


def _login_and_get_cookies(base_url: str) -> dict:
    """Login with default credentials and return cookies as a dict."""
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    data = urllib.parse.urlencode({"username": "testuser", "password": "testpass"}).encode()
    req = urllib.request.Request(f"{base_url}/login", data=data, method="POST")
    opener.open(req)
    return {c.name: c.value for c in cj}


# ---------------------------------------------------------------------------
# 1. Security headers present
# ---------------------------------------------------------------------------


def test_security_headers_present(app_server):
    """GET / must include CSP, X-Frame-Options, HSTS, X-XSS-Protection, X-Content-Type-Options."""
    status, hdrs, _body = _get(app_server)
    # Even if redirected to /login the after_request hook adds headers.
    required = [
        "Content-Security-Policy",
        "X-Frame-Options",
        "Strict-Transport-Security",
        "X-XSS-Protection",
        "X-Content-Type-Options",
    ]
    for header in required:
        assert header in hdrs, f"Missing security header: {header}"


# ---------------------------------------------------------------------------
# 2. CSP must not contain unsafe-eval
# ---------------------------------------------------------------------------


def test_csp_no_unsafe_eval(app_server):
    """CSP header must NOT contain 'unsafe-eval'. 'unsafe-inline' is intentional (Alpine.js)."""
    _status, hdrs, _body = _get(app_server)
    csp = hdrs.get("Content-Security-Policy", "")
    assert "unsafe-eval" not in csp, f"CSP contains unsafe-eval: {csp}"
    # Verify expected intentional entries are present
    assert "unsafe-inline" in csp, "CSP should contain unsafe-inline for Alpine.js"
    assert "cdn.jsdelivr.net" in csp, "CSP should whitelist cdn.jsdelivr.net"


# ---------------------------------------------------------------------------
# 3. CSRF token required
# ---------------------------------------------------------------------------


def test_csrf_token_required(app_server, auth_cookies):
    """POST to a CSRF-protected endpoint without X-CSRF-Token header must return 403."""
    status, _hdrs, body = _post(
        f"{app_server}/chat_create",
        data=json.dumps({}).encode(),
        headers={
            "Cookie": _cookie_header(auth_cookies),
            "Content-Type": "application/json",
        },
    )
    assert status == 403, f"Expected 403 without CSRF token, got {status}: {body}"
    assert "CSRF" in body or "csrf" in body.lower(), f"Expected CSRF error message, got: {body}"


# ---------------------------------------------------------------------------
# 4. CSRF token rotation on login
# ---------------------------------------------------------------------------


def test_csrf_token_rotation(app_server):
    """Get CSRF token before login, login, get new token — they must differ."""
    import http.cookiejar

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # Get a CSRF token before login (unauthenticated session)
    req1 = urllib.request.Request(f"{app_server}/csrf_token", method="GET")
    resp1 = opener.open(req1)
    token_before = json.loads(resp1.read().decode())["token"]

    # Login
    data = urllib.parse.urlencode({"username": "testuser", "password": "testpass"}).encode()
    req2 = urllib.request.Request(f"{app_server}/login", data=data, method="POST")
    opener.open(req2)

    # Get a new CSRF token after login (new session)
    req3 = urllib.request.Request(f"{app_server}/csrf_token", method="GET")
    resp3 = opener.open(req3)
    token_after = json.loads(resp3.read().decode())["token"]

    # Tokens should differ because login creates a new session
    assert token_before != token_after, "CSRF token should rotate after login"


# ---------------------------------------------------------------------------
# 5. Session cookie flags
# ---------------------------------------------------------------------------


def test_session_cookie_flags(app_server, server_port):
    """After login, session_* cookie must have HttpOnly and SameSite=Strict flags."""
    # Use http.client for raw Set-Cookie header access (urllib normalizes cookies)
    conn = http.client.HTTPConnection("127.0.0.1", server_port)
    body = urllib.parse.urlencode({"username": "testuser", "password": "testpass"})
    conn.request(
        "POST",
        "/login",
        body=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp = conn.getresponse()
    # Collect all Set-Cookie headers
    set_cookies = resp.headers.get_all("Set-Cookie") or []
    conn.close()

    session_cookies = [sc for sc in set_cookies if sc.startswith("session_")]
    assert session_cookies, f"No session_* cookie found in Set-Cookie headers: {set_cookies}"

    for sc in session_cookies:
        sc_lower = sc.lower()
        assert "httponly" in sc_lower, f"session cookie missing HttpOnly: {sc}"
        assert "samesite=strict" in sc_lower, f"session cookie missing SameSite=Strict: {sc}"


# ---------------------------------------------------------------------------
# 6. Session invalidated on logout
# ---------------------------------------------------------------------------


def test_session_invalidated_on_logout(app_server):
    """Login, get session cookie, POST /logout, reuse old session — must be rejected."""
    # Login and capture cookies
    cookies = _login_and_get_cookies(app_server)
    cookie_header = _cookie_header(cookies)

    # Verify we're authenticated (should get 200 for / with content)
    status1, _h, _b = _get(app_server, headers={"Cookie": cookie_header})
    assert status1 == 200, f"Expected 200 after login, got {status1}"

    # Logout
    _get(f"{app_server}/logout", headers={"Cookie": cookie_header})

    # Try using the old session to access a protected endpoint
    status2, _h, body2 = _get(app_server, headers={"Cookie": cookie_header})
    # After logout, / should redirect to /login (302) or serve the login page
    # urllib follows redirects, so we may get the login page as 200
    assert "login" in body2.lower() or status2 == 302, (
        f"Old session should be rejected after logout, got status {status2}"
    )


# ---------------------------------------------------------------------------
# 7. Error response has no stack trace
# ---------------------------------------------------------------------------


def test_error_no_stack_trace(app_server, auth_cookies):
    """Trigger a 500 error, verify response has request_id but NO Python traceback."""
    # POST to upload without a file to trigger an error
    csrf = _get_csrf_token(app_server, auth_cookies)
    status, hdrs, body = _post(
        f"{app_server}/upload",
        data=b"not-multipart-data",
        headers={
            "Cookie": _cookie_header(auth_cookies),
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf,
        },
    )
    assert status == 500, f"Expected 500, got {status}: {body}"
    # Should have request_id
    assert "request_id" in body, f"Expected request_id in error response: {body}"
    # Must NOT contain Python traceback indicators
    assert "Traceback" not in body, f"Error response leaks traceback: {body}"
    assert 'File "' not in body, f"Error response leaks file paths: {body}"


# ---------------------------------------------------------------------------
# 8. 404 error sanitized
# ---------------------------------------------------------------------------


def test_error_404_sanitized(app_server):
    """GET /nonexistent must return 404 with no path disclosure."""
    status, _hdrs, body = _get(f"{app_server}/nonexistent_path_12345")
    assert status == 404, f"Expected 404, got {status}"
    # Must not disclose filesystem paths
    assert "/mnt/" not in body, f"404 response discloses filesystem path: {body}"
    assert "\\mnt\\" not in body, f"404 response discloses filesystem path: {body}"


# ---------------------------------------------------------------------------
# 9. SQL injection in chat
# ---------------------------------------------------------------------------


def test_sql_injection_chat(app_server, auth_cookies):
    """POST /chat_create with SQL injection payload — must be treated as normal text."""
    csrf = _get_csrf_token(app_server, auth_cookies)
    payload = json.dumps(
        {
            "current_context": "'; DROP TABLE users;--",
            "new_context": "test_sqli_ctx",
        }
    ).encode()
    status, _hdrs, body = _post(
        f"{app_server}/chat_create",
        data=payload,
        headers={
            "Cookie": _cookie_header(auth_cookies),
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf,
        },
    )
    # Should succeed or fail gracefully — no DB error
    assert status in (200, 400, 404, 500), f"Unexpected status: {status}"
    body_lower = body.lower()
    assert "drop table" not in body_lower, f"SQL injection payload reflected: {body}"


# ---------------------------------------------------------------------------
# 10. XSS payload in chat (Playwright)
# ---------------------------------------------------------------------------


def test_xss_payload_chat(authenticated_page, app_server):
    """Send <script>alert(1)</script> in chat, verify it's escaped (no script execution)."""
    page = authenticated_page
    xss_payload = "<script>alert('xss')</script>"

    # Set up a flag to detect if alert fires.
    # Playwright page.evaluate is the standard API for running JS in the page context.
    page.evaluate("() => { window.__xss_triggered = false }")
    page.evaluate("() => { window.alert = function() { window.__xss_triggered = true; } }")

    # Navigate to the main page (SPA)
    page.goto(app_server, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Try to find a chat input and send the XSS payload
    chat_input = page.query_selector('textarea, input[type="text"], [contenteditable="true"], #visual-input')
    if chat_input:
        chat_input.fill(xss_payload)
        # Try to submit
        page.keyboard.press("Enter")
        page.wait_for_timeout(2000)

    # Check that alert was never triggered
    xss_fired = page.evaluate("() => window.__xss_triggered")
    assert not xss_fired, "XSS payload triggered an alert — input not properly escaped"

    # Verify the payload is rendered as text (escaped) if present in DOM
    page_content = page.content()
    if "alert" in page_content:
        # The script tag should be escaped, not rendered as actual HTML
        assert "&lt;script&gt;" in page_content or "<script>alert" not in page_content, (
            "XSS payload rendered as unescaped HTML"
        )


# ---------------------------------------------------------------------------
# 11. Path traversal upload
# ---------------------------------------------------------------------------


def test_path_traversal_upload(app_server, auth_cookies):
    """Upload file with name ../../etc/passwd — must be rejected or sanitized."""
    csrf = _get_csrf_token(app_server, auth_cookies)
    filename = "../../etc/passwd"
    body = (
        "------E2EBoundary\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: text/plain\r\n\r\n"
        "root:x:0:0:root:/root:/bin/bash\r\n"
        "------E2EBoundary--\r\n"
    ).encode()

    status, _hdrs, resp_body = _post(
        f"{app_server}/upload",
        data=body,
        headers={
            "Cookie": _cookie_header(auth_cookies),
            "Content-Type": "multipart/form-data; boundary=----E2EBoundary",
            "X-CSRF-Token": csrf,
        },
    )
    # Either rejected (400/403/500) or sanitized (filename cleaned by secure_filename)
    if status == 200:
        data = json.loads(resp_body)
        filenames = data.get("filenames", [])
        for fn in filenames:
            assert ".." not in fn, f"Path traversal not sanitized: {fn}"
            assert "/" not in fn, f"Directory separator in filename: {fn}"
    else:
        # Rejected — that's acceptable too
        assert status in (400, 403, 500), f"Unexpected status for path traversal: {status}"


# ---------------------------------------------------------------------------
# 12. Upload magic bytes mismatch
# ---------------------------------------------------------------------------


def test_upload_magic_bytes(app_server, auth_cookies):
    """Upload .exe content renamed to .png — must be rejected (HTTP 500 with generic error)."""
    csrf = _get_csrf_token(app_server, auth_cookies)
    # MZ header (PE executable magic bytes) in a file named .png
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    body = (
        (
            b"------E2EBoundaryMagic\r\n"
            b'Content-Disposition: form-data; name="file"; filename="malicious.png"\r\n'
            b"Content-Type: image/png\r\n\r\n"
        )
        + exe_content
        + b"\r\n------E2EBoundaryMagic--\r\n"
    )

    status, _hdrs, resp_body = _post(
        f"{app_server}/upload",
        data=body,
        headers={
            "Cookie": _cookie_header(auth_cookies),
            "Content-Type": "multipart/form-data; boundary=----E2EBoundaryMagic",
            "X-CSRF-Token": csrf,
        },
    )
    assert status == 500, f"Expected 500 for magic-bytes mismatch, got {status}: {resp_body}"
    resp_lower = resp_body.lower()
    assert "error" in resp_lower, f"Expected error in response: {resp_body}"
    assert "Traceback" not in resp_body, f"Response leaks Python traceback: {resp_body}"


# ---------------------------------------------------------------------------
# 13. Rate limit login
# ---------------------------------------------------------------------------


def test_rate_limit_login(app_server):
    """6 rapid POST /login attempts must trigger 429 (limit is 5 per minute)."""
    got_429 = False
    for _i in range(6):
        data = urllib.parse.urlencode({"username": "baduser", "password": "badpass"}).encode()
        status, _hdrs, _body = _post(
            f"{app_server}/login",
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if status == 429:
            got_429 = True
            break
    assert got_429, "Expected 429 after rapid login attempts"


# ---------------------------------------------------------------------------
# 14. Rate limit upload
# ---------------------------------------------------------------------------


def test_rate_limit_upload(app_server, auth_cookies):
    """11 rapid uploads must trigger 429 (limit is 10 per minute)."""
    csrf = _get_csrf_token(app_server, auth_cookies)
    # A minimal valid .txt upload
    body = (
        b"------E2EBoundaryRate\r\n"
        b'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
        b"Content-Type: text/plain\r\n\r\n"
        b"hello\r\n"
        b"------E2EBoundaryRate--\r\n"
    )

    got_429 = False
    for _i in range(11):
        status, _hdrs, _body = _post(
            f"{app_server}/upload",
            data=body,
            headers={
                "Cookie": _cookie_header(auth_cookies),
                "Content-Type": "multipart/form-data; boundary=----E2EBoundaryRate",
                "X-CSRF-Token": csrf,
            },
        )
        if status == 429:
            got_429 = True
            break
    assert got_429, "Expected 429 after 11 rapid upload attempts"


# ---------------------------------------------------------------------------
# 15. CORS not wildcard
# ---------------------------------------------------------------------------


def test_cors_not_wildcard(app_server):
    """If Access-Control-Allow-Origin is present, it must NOT be '*'."""
    status, hdrs, _body = _get(app_server)
    acao = hdrs.get("Access-Control-Allow-Origin")
    if acao is not None:
        assert acao != "*", "CORS Access-Control-Allow-Origin is wildcard '*'"
    # If header is absent, test passes (guards against future regressions)


# ---------------------------------------------------------------------------
# 16. X-Request-ID present
# ---------------------------------------------------------------------------


def test_request_id_present(app_server, auth_cookies):
    """Every API response must include X-Request-ID header."""
    csrf = _get_csrf_token(app_server, auth_cookies)
    # Test on an API endpoint that returns JSON
    status, hdrs, body = _post(
        f"{app_server}/chat_create",
        data=json.dumps({"new_context": "reqid_test"}).encode(),
        headers={
            "Cookie": _cookie_header(auth_cookies),
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf,
        },
    )
    hdrs_lower = {k.lower(): v for k, v in hdrs.items()}
    assert "x-request-id" in hdrs_lower, f"Missing X-Request-ID header in response (status={status})"
