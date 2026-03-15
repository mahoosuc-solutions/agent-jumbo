"""E2E tests for the logout flow."""

import pytest


@pytest.mark.e2e
def test_logout_redirects_and_requires_reauth(authenticated_page, app_server):
    """Logging out should redirect to login and require re-authentication."""
    page = authenticated_page

    # Find and click logout
    logout_btn = page.query_selector(
        'button:has-text("Logout"), button:has-text("Log out"), '
        'a:has-text("Logout"), a:has-text("Log out"), '
        'button[aria-label*="logout" i], a[href*="logout"]'
    )

    if logout_btn is None:
        # Try opening a user menu first
        user_menu = page.query_selector(
            'button[aria-label*="user" i], button[aria-label*="menu" i], '
            'button[aria-label*="account" i], .user-menu-trigger'
        )
        if user_menu:
            user_menu.click()
            page.wait_for_timeout(1000)
            logout_btn = page.query_selector(
                'button:has-text("Logout"), button:has-text("Log out"), '
                'a:has-text("Logout"), a:has-text("Log out"), a[href*="logout"]'
            )

    if logout_btn is None:
        # Try navigating to logout URL directly
        page.goto(f"{app_server}/logout", wait_until="domcontentloaded")
    else:
        logout_btn.click()

    page.wait_for_timeout(3000)

    # After logout, accessing a protected route should require re-auth
    page.goto(f"{app_server}/chat", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    current_url = page.url
    assert (
        "/login" in current_url
        or current_url.rstrip("/") == app_server.rstrip("/")
        or page.query_selector('input[type="password"]') is not None
    ), f"After logout, accessing /chat should require re-auth, got: {current_url}"
