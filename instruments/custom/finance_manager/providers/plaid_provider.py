from typing import Any
from urllib.parse import urlencode

from instruments.custom.finance_manager.providers.base import FinanceProvider
from python.helpers import settings as settings_helper


class PlaidFinanceProvider(FinanceProvider):
    def __init__(self) -> None:
        try:
            config = settings_helper.get_settings()
        except Exception:
            config = {}
        self.client_id = config.get("finance_plaid_client_id")
        self.redirect_uri = config.get("finance_plaid_redirect_uri")
        self.secret = config.get("finance_plaid_secret")
        self.environment = (config.get("finance_plaid_env") or "sandbox").strip() or "sandbox"

    def _get_auth_endpoint(self) -> str:
        env = self.environment.lower()
        if env == "production":
            return "https://production.plaid.com/link"
        if env == "development":
            return "https://development.plaid.com/link"
        return "https://sandbox.plaid.com/link"

    def get_auth_url(self) -> str | None:
        if not self.client_id or not self.redirect_uri:
            return None
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }
        return f"{self._get_auth_endpoint()}?{urlencode(params)}"

    def sync_transactions(self, account: dict[str, Any], start: str, end: str) -> list[dict[str, Any]]:
        return []
