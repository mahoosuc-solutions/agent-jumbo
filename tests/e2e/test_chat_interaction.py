"""E2E tests for chat interaction and accessibility."""

import pytest


@pytest.mark.e2e
def test_send_message_appears_in_log(authenticated_page, app_server):
    """Sending a message should make it appear in the chat log."""
    page = authenticated_page

    # Navigate to chat if not already there
    if "/chat" not in page.url:
        page.goto(f"{app_server}/chat", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

    # Find and fill the message input
    textarea = page.locator(
        'textarea[placeholder*="message"], textarea[name="message"], #message-input, textarea'
    ).first
    textarea.fill("Hello from e2e test")

    # Submit
    page.click('button[type="submit"], button:has-text("Send"), button[aria-label*="Send"]')

    # Wait for the message to appear in the DOM
    page.wait_for_timeout(3000)

    body_text = page.inner_text("body")
    assert "Hello from e2e test" in body_text, "Sent message should appear in the chat log"


@pytest.mark.e2e
def test_chat_accessibility_attributes(authenticated_page, app_server):
    """Chat interface should have proper a11y attributes (role=log, aria-live)."""
    page = authenticated_page

    if "/chat" not in page.url:
        page.goto(f"{app_server}/chat", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

    # Check for role="log" on the message container
    log_el = page.query_selector('[role="log"]')
    assert log_el is not None, 'Chat message list should have role="log"'

    # Check aria-live attribute
    aria_live = log_el.get_attribute("aria-live")
    assert aria_live == "polite", f'Expected aria-live="polite", got "{aria_live}"'

    # Check aria-label
    aria_label = log_el.get_attribute("aria-label")
    assert aria_label is not None, "Chat message list should have an aria-label"
