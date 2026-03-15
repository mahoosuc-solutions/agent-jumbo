"""E2E tests for protected route access control."""

import pytest


@pytest.mark.e2e
def test_unauthenticated_chat_redirects(page, app_server):
    """Accessing /chat without auth should redirect to login."""
    page.goto(f"{app_server}/chat", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    # Should be redirected to login or shown auth challenge
    current_url = page.url
    assert (
        "/login" in current_url
        or current_url.rstrip("/") == app_server.rstrip("/")
        or page.query_selector('input[type="password"]') is not None
    ), f"Expected redirect to login, got: {current_url}"


@pytest.mark.e2e
def test_unauthenticated_settings_redirects(page, app_server):
    """Accessing /settings without auth should redirect to login."""
    page.goto(f"{app_server}/settings", wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    current_url = page.url
    assert (
        "/login" in current_url
        or current_url.rstrip("/") == app_server.rstrip("/")
        or page.query_selector('input[type="password"]') is not None
    ), f"Expected redirect to login, got: {current_url}"
