from typing import Any

from instruments.custom.calendar_hub.providers.base import CalendarProvider


class MockCalendarProvider(CalendarProvider):
    def get_auth_url(self) -> str | None:
        return None

    def list_calendars(self, account: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"external_id": "mock-primary", "name": "Primary", "color": "#3b82f6"}]

    def list_events(self, account: dict[str, Any], calendar_id: str | None, limit: int) -> list[dict[str, Any]]:
        return []
