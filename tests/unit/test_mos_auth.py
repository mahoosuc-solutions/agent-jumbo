"""Tests for MOS authentication bridge — fail-closed + circuit breaker."""

import time
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset module state between tests."""
    import python.helpers.mos_auth as m

    m._entitlement_cache.clear()
    m._consecutive_failures = 0
    yield
    m._entitlement_cache.clear()
    m._consecutive_failures = 0


@pytest.fixture
def _mos_enabled(monkeypatch):
    """Enable MOS auth mode for tests."""
    monkeypatch.setattr(
        "python.helpers.mos_auth.dotenv.get_dotenv_value",
        lambda key: {
            "MOS_JWT_SECRET": "test-secret",  # pragma: allowlist secret
            "AIOS_BASE_URL": "http://localhost:3012",
            "ENTITLEMENT_FAIL_MODE": "closed",
            "SERVICE_MESH_SECRET": "",
        }.get(key, ""),
    )


class TestCheckEntitlement:
    """Tests for check_entitlement() — fail-closed behavior."""

    def test_returns_true_when_mos_disabled(self, monkeypatch):
        """Standalone mode skips entitlement check entirely."""
        monkeypatch.setattr("python.helpers.mos_auth.is_mos_auth_enabled", lambda: False)
        from python.helpers.mos_auth import check_entitlement

        assert check_entitlement("org-1") is True

    def test_returns_cached_value_within_ttl(self, _mos_enabled):
        """Cache hit returns stored value without API call."""
        import python.helpers.mos_auth as m

        m._entitlement_cache["org-1:agent-mahoo"] = (True, time.time())

        assert m.check_entitlement("org-1") is True

    @patch("python.helpers.mos_auth.http_requests.get")
    def test_returns_true_on_api_entitled(self, mock_get, _mos_enabled):
        """API returns entitled=True → access granted."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"entitled": True}
        mock_get.return_value = mock_resp

        from python.helpers.mos_auth import check_entitlement

        assert check_entitlement("org-1") is True

    @patch("python.helpers.mos_auth.http_requests.get")
    def test_returns_false_on_api_not_entitled(self, mock_get, _mos_enabled):
        """API returns entitled=False → access denied."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"entitled": False}
        mock_get.return_value = mock_resp

        from python.helpers.mos_auth import check_entitlement

        assert check_entitlement("org-2") is False

    @patch("python.helpers.mos_auth.http_requests.get")
    def test_fail_closed_on_api_error(self, mock_get, _mos_enabled):
        """API returns 500 → fail-closed denies access."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_get.return_value = mock_resp

        from python.helpers.mos_auth import check_entitlement

        assert check_entitlement("org-3") is False

    @patch("python.helpers.mos_auth.http_requests.get")
    def test_fail_closed_on_network_error(self, mock_get, _mos_enabled):
        """Network timeout → fail-closed denies access."""
        mock_get.side_effect = ConnectionError("timeout")

        from python.helpers.mos_auth import check_entitlement

        assert check_entitlement("org-4") is False

    @patch("python.helpers.mos_auth.http_requests.get")
    def test_fail_open_mode(self, mock_get, monkeypatch):
        """ENTITLEMENT_FAIL_MODE=open → grants access on error."""
        monkeypatch.setattr(
            "python.helpers.mos_auth.dotenv.get_dotenv_value",
            lambda key: {
                "MOS_JWT_SECRET": "test-secret",  # pragma: allowlist secret
                "AIOS_BASE_URL": "http://localhost:3012",
                "ENTITLEMENT_FAIL_MODE": "open",
                "SERVICE_MESH_SECRET": "",
            }.get(key, ""),
        )
        mock_get.side_effect = ConnectionError("timeout")

        from python.helpers.mos_auth import check_entitlement

        assert check_entitlement("org-5") is True

    @patch("python.helpers.mos_auth.http_requests.get")
    def test_circuit_breaker_uses_stale_cache(self, mock_get, _mos_enabled):
        """After 5 failures with stale cache → uses cached value."""
        import python.helpers.mos_auth as m

        # Seed stale cache (expired TTL)
        m._entitlement_cache["org-6:agent-mahoo"] = (True, time.time() - 600)
        mock_get.side_effect = ConnectionError("timeout")

        # First 4 failures: fail-closed (no circuit breaker yet)
        for _ in range(4):
            m._entitlement_cache.pop("org-6:agent-mahoo", None)  # Clear fresh cache entry
            result = m.check_entitlement("org-6")

        # After 5+ failures: circuit breaker kicks in, uses stale value
        m._consecutive_failures = 5
        m._entitlement_cache["org-6:agent-mahoo"] = (True, time.time() - 600)
        result = m.check_entitlement("org-6")
        # Should use stale cached True value
        assert result is True


class TestVerifyToken:
    """Tests for verify_token() — JWT validation."""

    def test_returns_none_without_secret(self, monkeypatch):
        monkeypatch.setattr("python.helpers.mos_auth.dotenv.get_dotenv_value", lambda key: "")
        from python.helpers.mos_auth import verify_token

        assert verify_token("some-token") is None

    def test_verifies_valid_jwt(self, monkeypatch):
        import jwt as pyjwt

        secret = "test-jwt-secret"  # pragma: allowlist secret
        monkeypatch.setattr(
            "python.helpers.mos_auth.dotenv.get_dotenv_value",
            lambda key: secret if key == "MOS_JWT_SECRET" else "",
        )
        token = pyjwt.encode(
            {"userId": "u1", "email": "test@test.com", "organization_id": "org-1"},
            secret,
            algorithm="HS256",
        )

        from python.helpers.mos_auth import verify_token

        payload = verify_token(token)
        assert payload is not None
        assert payload["email"] == "test@test.com"
        assert payload["organization_id"] == "org-1"

    def test_returns_none_for_expired_jwt(self, monkeypatch):
        import jwt as pyjwt

        secret = "test-jwt-secret"  # pragma: allowlist secret
        monkeypatch.setattr(
            "python.helpers.mos_auth.dotenv.get_dotenv_value",
            lambda key: secret if key == "MOS_JWT_SECRET" else "",
        )
        token = pyjwt.encode(
            {"userId": "u1", "exp": int(time.time()) - 100},
            secret,
            algorithm="HS256",
        )

        from python.helpers.mos_auth import verify_token

        assert verify_token(token) is None
