import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from instruments.custom.finance_manager.providers.base import FinanceProvider
from python.helpers import settings as settings_helper

logger = logging.getLogger(__name__)


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

    def _get_base_url(self) -> str:
        env = self.environment.lower()
        if env == "production":
            return "https://production.plaid.com"
        if env == "development":
            return "https://development.plaid.com"
        return "https://sandbox.plaid.com"

    def _get_auth_endpoint(self) -> str:
        return f"{self._get_base_url()}/link"

    def _plaid_request(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Make an authenticated request to the Plaid API.

        Returns the parsed JSON response dict, or None on any error.
        """
        url = f"{self._get_base_url()}{endpoint}"
        payload.setdefault("client_id", self.client_id)
        payload.setdefault("secret", self.secret)
        try:
            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Plaid API error %s for %s: %s", exc.response.status_code, endpoint, exc.response.text)
            return None
        except httpx.RequestError as exc:
            logger.error("Plaid request error for %s: %s", endpoint, exc)
            return None
        except Exception as exc:
            logger.error("Unexpected error calling Plaid %s: %s", endpoint, exc)
            return None

    def get_auth_url(self) -> str | None:
        if not self.client_id or not self.redirect_uri:
            return None
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
        }
        return f"{self._get_auth_endpoint()}?{urlencode(params)}"

    def create_link_token(self, user_id: str) -> str | None:
        """Create a Plaid Link token for the frontend to initiate bank connection.

        Returns the link_token string, or None on failure.
        """
        if not self.client_id or not self.secret:
            logger.warning("Plaid credentials not configured; cannot create link token")
            return None

        payload = {
            "user": {"client_user_id": user_id},
            "client_name": "AgentJumbo Finance",
            "products": ["transactions"],
            "country_codes": ["US"],
            "language": "en",
        }
        if self.redirect_uri:
            payload["redirect_uri"] = self.redirect_uri

        data = self._plaid_request("/link/token/create", payload)
        if data is None:
            return None
        return data.get("link_token")

    def exchange_public_token(self, public_token: str) -> str | None:
        """Exchange a Plaid Link public_token for a permanent access_token.

        Returns the access_token string, or None on failure.
        """
        if not self.client_id or not self.secret:
            logger.warning("Plaid credentials not configured; cannot exchange token")
            return None

        data = self._plaid_request("/item/public_token/exchange", {"public_token": public_token})
        if data is None:
            return None
        return data.get("access_token")

    def sync_transactions(self, account: dict[str, Any], start: str, end: str) -> list[dict[str, Any]]:
        """Fetch transactions from Plaid for the given account and date range.

        Returns a list of dicts with keys: date, amount, merchant, category.
        Returns an empty list on any error or when the access token is missing.
        """
        access_token = account.get("access_token")
        if not access_token:
            logger.warning("No access_token for account %s; returning empty transactions", account.get("id"))
            return []

        if not self.client_id or not self.secret:
            logger.warning("Plaid credentials not configured; cannot sync transactions")
            return []

        payload = {
            "access_token": access_token,
            "start_date": start,
            "end_date": end,
        }

        data = self._plaid_request("/transactions/get", payload)
        if data is None:
            return []

        raw_transactions = data.get("transactions", [])
        results: list[dict[str, Any]] = []
        for txn in raw_transactions:
            category_list = txn.get("category") or []
            category = category_list[0] if isinstance(category_list, list) and category_list else None
            results.append(
                {
                    "date": txn.get("date", start),
                    "amount": float(txn.get("amount", 0)),
                    "merchant": txn.get("merchant_name") or txn.get("name", "Unknown"),
                    "category": category,
                }
            )

        logger.info("Synced %d transactions for account %s", len(results), account.get("id"))
        return results
