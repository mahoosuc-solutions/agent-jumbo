from typing import Any

from instruments.custom.finance_manager.providers.base import FinanceProvider


class MockFinanceProvider(FinanceProvider):
    def get_auth_url(self) -> str | None:
        return None

    def sync_transactions(self, account: dict[str, Any], start: str, end: str) -> list[dict[str, Any]]:
        return [
            {"date": start, "amount": 2500.00, "merchant": "Client Payment", "category": "income"},
            {"date": end, "amount": -125.50, "merchant": "Cloud Hosting", "category": "expense"},
        ]
