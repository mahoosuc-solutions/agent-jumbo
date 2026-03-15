from typing import Any
from urllib.parse import urlencode

from instruments.custom.calendar_hub.providers.base import CalendarProvider
from python.helpers import settings as settings_helper


class GoogleCalendarProvider(CalendarProvider):
    AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"

    def __init__(self) -> None:
        config = settings_helper.get_settings()
        self.client_id = config.get("calendar_google_client_id")
        self.redirect_uri = config.get("calendar_google_redirect_uri")
        self.client_secret = config.get("calendar_google_client_secret")

    def get_auth_url(self) -> str | None:
        if not self.client_id or not self.redirect_uri:
            return None
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/calendar",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{self.AUTH_ENDPOINT}?{urlencode(params)}"

    def list_calendars(self, account: dict[str, Any]) -> list[dict[str, Any]]:
        return []

    def list_events(self, account: dict[str, Any], calendar_id: str | None, limit: int) -> list[dict[str, Any]]:
        return []
