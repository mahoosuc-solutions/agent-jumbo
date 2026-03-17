"""Consolidated E2E functional tests for Agent Zero.

Covers: authentication, chat, file upload, settings, and SSE transport.
"""

import json
import os
import tempfile
import urllib.parse
import urllib.request

import pytest

# ---------------------------------------------------------------------------
# 1. Login — valid credentials
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_login_valid_credentials(page, app_server):
    """Valid credentials redirect away from /login."""
    page.goto(f"{app_server}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"], input[type="text"]', "testuser")
    page.fill('input[name="password"], input[type="password"]', "testpass")
    page.click('button[type="submit"]')
    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
    assert "/login" not in page.url


# ---------------------------------------------------------------------------
# 2. Login — invalid credentials
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_login_invalid_credentials(page, app_server):
    """Wrong password keeps the user on /login or shows an error."""
    page.goto(f"{app_server}/login", wait_until="domcontentloaded")
    page.fill('input[name="username"], input[type="text"]', "testuser")
    page.fill('input[name="password"], input[type="password"]', "wrongpass")
    page.click('button[type="submit"]')
    page.wait_for_timeout(2000)

    on_login = "/login" in page.url
    has_error = (
        page.query_selector('[role="alert"]') is not None
        or page.query_selector(".error-message, .text-danger") is not None
        or page.query_selector('.toast, [role="status"]') is not None
    )
    assert on_login or has_error, f"Expected to stay on /login or see an error, got: {page.url}"


# ---------------------------------------------------------------------------
# 3. Login — rate limiting
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_login_rate_limiting(app_server):
    """Six rapid failed logins via raw HTTP should trigger a 429."""
    url = f"{app_server}/login"
    bad_creds = urllib.parse.urlencode({"username": "attacker", "password": "badpass"}).encode()

    got_429 = False
    for _ in range(6):
        req = urllib.request.Request(url, data=bad_creds, method="POST")
        try:
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                got_429 = True
                break

    assert got_429, "Expected HTTP 429 after rapid failed login attempts"


# ---------------------------------------------------------------------------
# 4. Protected route redirects to /login
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_protected_route_redirects(page, app_server):
    """GET / without auth should redirect to /login."""
    page.goto(app_server, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    current = page.url
    assert "/login" in current or page.query_selector('input[type="password"]') is not None, (
        f"Expected redirect to login, got: {current}"
    )


# ---------------------------------------------------------------------------
# 5. Logout invalidates the session
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_logout_invalidates_session(authenticated_page, app_server):
    """After logout, the session cookie should no longer grant access."""
    page = authenticated_page

    # Perform logout
    page.goto(f"{app_server}/logout", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Try to access a protected route
    page.goto(app_server, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    current = page.url
    assert "/login" in current or page.query_selector('input[type="password"]') is not None, (
        f"After logout, accessing / should require re-auth, got: {current}"
    )


# ---------------------------------------------------------------------------
# 6. Chat — send message
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_chat_send_message(authenticated_page, app_server):
    """Filling #chat-input and clicking #send-button shows the message."""
    page = authenticated_page

    if "/chat" not in page.url:
        page.goto(f"{app_server}/chat", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

    textarea = page.locator("#chat-input, textarea").first
    textarea.fill("Hello from e2e test")

    send_btn = page.locator("#send-button").first
    send_btn.wait_for(state="attached", timeout=10000)
    send_btn.click(force=True)

    page.wait_for_timeout(3000)

    body_text = page.inner_text("body")
    assert "Hello from e2e test" in body_text, "Sent message should appear in the chat log"


# ---------------------------------------------------------------------------
# 7. Chat — accessibility attributes
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_chat_accessibility_attrs(authenticated_page, app_server):
    """Chat container has role='log', aria-live='polite', and aria-label."""
    page = authenticated_page

    if "/chat" not in page.url:
        page.goto(f"{app_server}/chat", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

    log_el = page.query_selector('[role="log"]')
    assert log_el is not None, 'Chat container should have role="log"'

    aria_live = log_el.get_attribute("aria-live")
    assert aria_live == "polite", f'Expected aria-live="polite", got "{aria_live}"'

    aria_label = log_el.get_attribute("aria-label")
    assert aria_label is not None, "Chat container should have an aria-label"


# ---------------------------------------------------------------------------
# 8. Upload — allowed .txt file
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_upload_allowed_file(authenticated_page, app_server):
    """Uploading a .txt file via #file-input should succeed."""
    page = authenticated_page

    page.goto(f"{app_server}/chat", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    file_input = page.locator("#file-input, input[type='file']").first
    if file_input.count() == 0:
        pytest.skip("No file upload input found on chat page")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="e2e_upload_") as f:
        f.write("E2E upload test content.")
        tmp_path = f.name

    try:
        file_input.set_input_files(tmp_path)
        page.wait_for_timeout(2000)

        body_text = page.inner_text("body").lower()
        has_error = "error" in body_text and "upload" in body_text
        assert not has_error, "Upload of .txt file should not produce an error"
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# 9. Upload — blocked .exe file
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_upload_blocked_file(app_server, auth_cookies):
    """Uploading an .exe file via raw HTTP should return 500 with error JSON."""
    cookie_header = "; ".join(f"{k}={v}" for k, v in auth_cookies.items())

    boundary = "----E2ETestBoundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="malware.exe"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
        "MZ fake exe\r\n"
        f"--{boundary}--\r\n"
    ).encode()

    req = urllib.request.Request(
        f"{app_server}/upload",
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Cookie": cookie_header,
        },
    )

    try:
        resp = urllib.request.urlopen(req, timeout=10)
        # If it didn't raise, check the status anyway
        assert resp.status == 500, f"Expected 500, got {resp.status}"
    except urllib.error.HTTPError as exc:
        assert exc.code == 500, f"Expected HTTP 500, got {exc.code}"
        resp_body = json.loads(exc.read().decode())
        assert resp_body.get("error") == "Internal server error"


# ---------------------------------------------------------------------------
# 10. Settings page renders
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_settings_page_renders(authenticated_page, app_server):
    """/settings should have content and section headings."""
    page = authenticated_page
    page.goto(f"{app_server}/settings", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    body_text = page.inner_text("body")
    has_content = len(body_text.strip()) > 50 and (
        "settings" in body_text.lower()
        or page.query_selector("section, [data-section], .settings-section, form") is not None
    )
    assert has_content, "Settings page should render with section content"


# ---------------------------------------------------------------------------
# 11. SSE connection (transport-level)
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_sse_connection(app_server, auth_cookies):
    """GET /sse should return text/event-stream content type and data: lines."""
    cookie_header = "; ".join(f"{k}={v}" for k, v in auth_cookies.items())

    req = urllib.request.Request(
        f"{app_server}/sse",
        method="GET",
        headers={"Cookie": cookie_header},
    )

    try:
        resp = urllib.request.urlopen(req, timeout=10)
    except urllib.error.HTTPError as exc:
        # Even an error response can confirm the endpoint exists and
        # returns event-stream content type.
        content_type = exc.headers.get("Content-Type", "")
        assert "text/event-stream" in content_type, f"Expected text/event-stream, got: {content_type}"
        return

    content_type = resp.headers.get("Content-Type", "")
    assert "text/event-stream" in content_type, f"Expected text/event-stream Content-Type, got: {content_type}"

    # Read a small chunk to verify we get data: lines
    chunk = resp.read(4096).decode(errors="replace")
    assert "data:" in chunk, "SSE stream should contain 'data:' lines"
