"""Page object for the chat interface."""


class ChatPage:
    def __init__(self, page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self):
        self.page.goto(f"{self.base_url}/chat", wait_until="domcontentloaded")

    def send_message(self, text: str):
        textarea = self.page.locator(
            'textarea[placeholder*="message"], textarea[name="message"], #message-input, textarea'
        ).first
        textarea.fill(text)
        self.page.click('button[type="submit"], button:has-text("Send"), button[aria-label*="Send"]')

    def wait_for_response(self, timeout: int = 30000):
        self.page.wait_for_selector(
            '[role="log"] > div:last-child, .chat-message:last-child',
            timeout=timeout,
        )

    def get_messages(self) -> list[str]:
        elements = self.page.query_selector_all('[role="log"] > div, .chat-message')
        return [el.inner_text() for el in elements]

    def create_new_chat(self):
        self.page.click('button:has-text("New"), button[aria-label*="New chat"], button[aria-label*="new"]')

    def delete_chat(self):
        self.page.click('button:has-text("Delete"), button[aria-label*="Delete"]')
