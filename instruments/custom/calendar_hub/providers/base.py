from abc import ABC, abstractmethod
from typing import Any


class CalendarProvider(ABC):
    @abstractmethod
    def get_auth_url(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def list_calendars(self, account: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def list_events(self, account: dict[str, Any], calendar_id: str | None, limit: int) -> list[dict[str, Any]]:
        raise NotImplementedError
