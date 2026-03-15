"""E2E tests for the settings page."""

import pytest


@pytest.mark.e2e
def test_settings_sections_render(authenticated_page, app_server):
    """Settings page should load and render section headings."""
    page = authenticated_page
    page.goto(f"{app_server}/settings", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # Settings page should have rendered sections or tabs
    body_text = page.inner_text("body")

    # At minimum, the page should not be empty and should have some settings content
    has_content = len(body_text.strip()) > 50 and (
        "settings" in body_text.lower()
        or page.query_selector("section, [data-section], .settings-section, form") is not None
    )
    assert has_content, "Settings page should render with section content"


@pytest.mark.e2e
def test_settings_save_persists(authenticated_page, app_server):
    """Changing a setting and saving should persist the value."""
    page = authenticated_page
    page.goto(f"{app_server}/settings", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # Find a text input to modify
    text_input = page.locator('input[type="text"]:visible').first
    if text_input.count() == 0:
        pytest.skip("No visible text input found on settings page")

    original_value = text_input.input_value()
    test_value = f"{original_value}_e2e_test"

    text_input.fill(test_value)

    # Save
    save_btn = page.locator('button:has-text("Save"), button[type="submit"]').first
    if save_btn.count() == 0:
        pytest.skip("No save button found on settings page")
    save_btn.click()

    page.wait_for_timeout(2000)

    # Reload and verify
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    new_value = page.locator('input[type="text"]:visible').first.input_value()

    # Restore original value
    page.locator('input[type="text"]:visible').first.fill(original_value)
    page.locator('button:has-text("Save"), button[type="submit"]').first.click()
    page.wait_for_timeout(1000)

    assert new_value == test_value, f"Setting should persist after save: expected '{test_value}', got '{new_value}'"
