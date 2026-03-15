from abc import ABC, abstractmethod
from typing import Any


class FinanceProvider(ABC):
    @abstractmethod
    def get_auth_url(self) -> str | None:
        raise NotImplementedError

    @abstractmethod
    def sync_transactions(self, account: dict[str, Any], start: str, end: str) -> list[dict[str, Any]]:
        raise NotImplementedError
