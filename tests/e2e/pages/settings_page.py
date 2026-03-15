"""Page object for the settings page."""


class SettingsPage:
    def __init__(self, page, base_url: str):
        self.page = page
        self.base_url = base_url

    def navigate(self):
        self.page.goto(f"{self.base_url}/settings", wait_until="domcontentloaded")

    def get_field_value(self, field_id: str) -> str | None:
        el = self.page.query_selector(f'#{field_id}, [name="{field_id}"]')
        if el is None:
            return None
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            return el.evaluate("e => e.options[e.selectedIndex]?.value")
        return el.input_value()

    def set_field_value(self, field_id: str, value: str):
        el = self.page.locator(f'#{field_id}, [name="{field_id}"]').first
        tag = el.evaluate("e => e.tagName.toLowerCase()")
        if tag == "select":
            el.select_option(value)
        else:
            el.fill(value)

    def save(self):
        self.page.click('button:has-text("Save"), button[type="submit"]')
