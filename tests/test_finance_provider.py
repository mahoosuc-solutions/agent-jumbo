import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from instruments.custom.finance_manager.finance_manager import FinanceManager
from instruments.custom.finance_manager.providers.plaid_provider import PlaidFinanceProvider


def test_finance_connect_returns_auth_url_key(tmp_path, monkeypatch):
    db_path = os.path.join(tmp_path, "finance.db")
    manager = FinanceManager(db_path)

    monkeypatch.delenv("PLAID_CLIENT_ID", raising=False)
    monkeypatch.delenv("PLAID_REDIRECT_URI", raising=False)

    account = manager.connect_account(provider="plaid", mock=False)
    assert account["status"] == "pending"
    assert "auth_url" in account


# ---------------------------------------------------------------------------
# PlaidFinanceProvider unit tests
# ---------------------------------------------------------------------------


@pytest.fixture
def plaid_provider():
    """Create a PlaidFinanceProvider with test credentials (bypasses settings)."""
    with patch("instruments.custom.finance_manager.providers.plaid_provider.settings_helper") as mock_settings:
        mock_settings.get_settings.return_value = {
            "finance_plaid_client_id": "test_client_id",
            "finance_plaid_secret": "test_secret",  # pragma: allowlist secret
            "finance_plaid_redirect_uri": "http://localhost/callback",
            "finance_plaid_env": "sandbox",
        }
        provider = PlaidFinanceProvider()
    return provider


@pytest.fixture
def plaid_provider_no_creds():
    """Create a PlaidFinanceProvider without credentials."""
    with patch("instruments.custom.finance_manager.providers.plaid_provider.settings_helper") as mock_settings:
        mock_settings.get_settings.return_value = {}
        provider = PlaidFinanceProvider()
    return provider


class TestPlaidSyncTransactions:
    def test_returns_empty_when_no_access_token(self, plaid_provider):
        result = plaid_provider.sync_transactions({"id": 1}, "2026-01-01", "2026-01-31")
        assert result == []

    def test_returns_empty_when_no_credentials(self, plaid_provider_no_creds):
        result = plaid_provider_no_creds.sync_transactions(
            {"id": 1, "access_token": "test-token"}, "2026-01-01", "2026-01-31"
        )
        assert result == []

    @patch("instruments.custom.finance_manager.providers.plaid_provider.httpx.post")
    def test_returns_parsed_transactions(self, mock_post, plaid_provider):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "transactions": [
                {
                    "date": "2026-01-15",
                    "amount": 42.50,
                    "merchant_name": "Acme Corp",
                    "category": ["Shopping", "Electronics"],
                },
                {
                    "date": "2026-01-20",
                    "amount": -100.00,
                    "name": "Payroll Deposit",
                    "merchant_name": None,
                    "category": ["Transfer", "Payroll"],
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = plaid_provider.sync_transactions(
            {"id": 1, "access_token": "access-sandbox-test"}, "2026-01-01", "2026-01-31"
        )

        assert len(result) == 2
        assert result[0]["date"] == "2026-01-15"
        assert result[0]["amount"] == 42.50
        assert result[0]["merchant"] == "Acme Corp"
        assert result[0]["category"] == "Shopping"

        # Falls back to "name" when merchant_name is None
        assert result[1]["merchant"] == "Payroll Deposit"

    @patch("instruments.custom.finance_manager.providers.plaid_provider.httpx.post")
    def test_returns_empty_on_api_error(self, mock_post, plaid_provider):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        result = plaid_provider.sync_transactions(
            {"id": 1, "access_token": "access-sandbox-test"}, "2026-01-01", "2026-01-31"
        )
        assert result == []

    @patch("instruments.custom.finance_manager.providers.plaid_provider.httpx.post")
    def test_returns_empty_on_network_error(self, mock_post, plaid_provider):
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        result = plaid_provider.sync_transactions(
            {"id": 1, "access_token": "access-sandbox-test"}, "2026-01-01", "2026-01-31"
        )
        assert result == []

    @patch("instruments.custom.finance_manager.providers.plaid_provider.httpx.post")
    def test_sends_correct_payload(self, mock_post, plaid_provider):
        mock_response = MagicMock()
        mock_response.json.return_value = {"transactions": []}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        plaid_provider.sync_transactions({"id": 1, "access_token": "access-sandbox-test"}, "2026-01-01", "2026-01-31")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == "https://sandbox.plaid.com/transactions/get"
        payload = call_kwargs[1]["json"]
        assert payload["access_token"] == "access-sandbox-test"
        assert payload["start_date"] == "2026-01-01"
        assert payload["end_date"] == "2026-01-31"
        assert payload["client_id"] == "test_client_id"
        assert payload["secret"] == "test_secret"  # pragma: allowlist secret


class TestPlaidCreateLinkToken:
    @patch("instruments.custom.finance_manager.providers.plaid_provider.httpx.post")
    def test_returns_link_token(self, mock_post, plaid_provider):
        mock_response = MagicMock()
        mock_response.json.return_value = {"link_token": "link-sandbox-abc123"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        token = plaid_provider.create_link_token("user-42")
        assert token == "link-sandbox-abc123"

        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"]
        assert payload["user"]["client_user_id"] == "user-42"
        assert payload["products"] == ["transactions"]

    def test_returns_none_when_no_credentials(self, plaid_provider_no_creds):
        result = plaid_provider_no_creds.create_link_token("user-42")
        assert result is None

    @patch("instruments.custom.finance_manager.providers.plaid_provider.httpx.post")
    def test_returns_none_on_api_error(self, mock_post, plaid_provider):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        result = plaid_provider.create_link_token("user-42")
        assert result is None


class TestPlaidExchangePublicToken:
    @patch("instruments.custom.finance_manager.providers.plaid_provider.httpx.post")
    def test_returns_access_token(self, mock_post, plaid_provider):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "access-sandbox-xyz789",
            "item_id": "item-abc",
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        token = plaid_provider.exchange_public_token("public-sandbox-token123")
        assert token == "access-sandbox-xyz789"

        call_kwargs = mock_post.call_args
        assert call_kwargs[0][0] == "https://sandbox.plaid.com/item/public_token/exchange"
        payload = call_kwargs[1]["json"]
        assert payload["public_token"] == "public-sandbox-token123"

    def test_returns_none_when_no_credentials(self, plaid_provider_no_creds):
        result = plaid_provider_no_creds.exchange_public_token("public-token")
        assert result is None

    @patch("instruments.custom.finance_manager.providers.plaid_provider.httpx.post")
    def test_returns_none_on_api_error(self, mock_post, plaid_provider):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response

        result = plaid_provider.exchange_public_token("bad-token")
        assert result is None


class TestPlaidBaseUrl:
    def test_sandbox_is_default(self, plaid_provider):
        assert plaid_provider._get_base_url() == "https://sandbox.plaid.com"

    def test_production_url(self, plaid_provider):
        plaid_provider.environment = "production"
        assert plaid_provider._get_base_url() == "https://production.plaid.com"

    def test_development_url(self, plaid_provider):
        plaid_provider.environment = "development"
        assert plaid_provider._get_base_url() == "https://development.plaid.com"


class TestFinanceManagerProviderSelection:
    """Test that finance_manager selects the correct provider based on account status."""

    def test_uses_real_provider_for_connected_account(self, tmp_path):
        db_path = os.path.join(tmp_path, "finance.db")
        manager = FinanceManager(db_path)

        # Create a connected plaid account
        account_id = manager.db.add_account("plaid", "connected")
        account = manager.db.get_account(account_id)
        assert account["provider"] == "plaid"
        assert account["status"] == "connected"

    def test_uses_mock_provider_for_pending_account(self, tmp_path):
        db_path = os.path.join(tmp_path, "finance.db")
        manager = FinanceManager(db_path)

        # Create a pending account — should fall back to mock
        account_id = manager.db.add_account("plaid", "pending")

        # Mock provider returns 2 sample transactions
        txns = manager.sync_transactions(account_id, "2026-01-01", "2026-01-31")
        assert len(txns) == 2

    def test_get_account_returns_none_for_missing_id(self, tmp_path):
        db_path = os.path.join(tmp_path, "finance.db")
        manager = FinanceManager(db_path)
        assert manager.db.get_account(9999) is None
