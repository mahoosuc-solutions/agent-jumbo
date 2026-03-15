"""Page object for the login page."""


class LoginPage:
    def __init__(self, page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self):
        self.page.goto(f"{self.base_url}/login", wait_until="domcontentloaded")

    def login(self, username: str, password: str):
        self.page.fill('input[name="username"], input[type="text"]', username)
        self.page.fill('input[name="password"], input[type="password"]', password)
        self.page.click('button[type="submit"]')

    def get_error_message(self) -> str | None:
        el = self.page.query_selector('[role="alert"], .error-message, .text-danger')
        return el.inner_text() if el else None

    def get_rate_limit_message(self) -> str | None:
        el = self.page.query_selector('[data-testid="rate-limit"], .rate-limit-message, .text-danger')
        return el.inner_text() if el else None
