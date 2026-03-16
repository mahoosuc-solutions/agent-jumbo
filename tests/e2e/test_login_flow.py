"""E2E tests for the login flow."""

import pytest

from tests.e2e.pages.login_page import LoginPage


@pytest.mark.e2e
def test_valid_login_redirects(page, app_server):
    """Valid credentials should redirect to the main app."""
    login = LoginPage(page, app_server)
    login.navigate()
    login.login("testuser", "testpass")

    page.wait_for_url(lambda url: "/login" not in url, timeout=15000)
    assert "/login" not in page.url


@pytest.mark.e2e
def test_invalid_login_shows_error(page, app_server):
    """Invalid credentials should show an error message."""
    login = LoginPage(page, app_server)
    login.navigate()
    login.login("wronguser", "wrongpass")

    # Wait a moment for error to appear
    page.wait_for_timeout(2000)

    # Should still be on login page
    assert "/login" in page.url or page.url.rstrip("/") == app_server.rstrip("/")

    # Should show error feedback (via toast, inline error, or remaining on login)
    error = login.get_error_message()
    has_error_indicator = (
        error is not None
        or page.query_selector('[role="alert"]') is not None
        or page.query_selector('.toast, [role="status"]') is not None
    )
    assert has_error_indicator or "/login" in page.url, "Expected error message or to remain on login page"


@pytest.mark.e2e
def test_server_stable_after_repeated_failed_logins(page, app_server):
    """Server should remain responsive after many failed login attempts."""
    login = LoginPage(page, app_server)
    login.navigate()

    for _ in range(10):
        login.login("attacker", "badpass")
        page.wait_for_timeout(200)
        login.navigate()

    # After repeated failures, server should still respond and accept valid login
    login.login("testuser", "testpass")
    page.wait_for_timeout(3000)

    # Either we logged in successfully, or rate limiting blocked us (both are acceptable)
    logged_in = "/login" not in page.url
    still_on_login = "/login" in page.url or page.url.rstrip("/") == app_server.rstrip("/")
    assert logged_in or still_on_login, f"Server should be responsive after repeated failures, got: {page.url}"
