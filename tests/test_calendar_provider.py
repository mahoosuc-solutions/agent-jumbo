import json
import os
from unittest.mock import MagicMock, patch

import pytest

from instruments.custom.calendar_hub.calendar_manager import CalendarHubManager
from instruments.custom.calendar_hub.providers.google_provider import GoogleCalendarProvider


def test_calendar_connect_returns_auth_url_key(tmp_path, monkeypatch):
    db_path = os.path.join(tmp_path, "calendar_hub.db")
    manager = CalendarHubManager(db_path)

    monkeypatch.delenv("GOOGLE_CALENDAR_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CALENDAR_REDIRECT_URI", raising=False)

    account = manager.connect_account(provider="google", mock=False)
    assert account["auth_state"] == "pending"
    assert "auth_url" in account


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def google_provider(monkeypatch):
    """Create a GoogleCalendarProvider with fake credentials."""
    fake_settings = {
        "calendar_google_client_id": "fake-client-id",
        "calendar_google_redirect_uri": "http://localhost/callback",
        "calendar_google_client_secret": "fake-client-secret",  # pragma: allowlist secret
    }
    with patch("instruments.custom.calendar_hub.providers.google_provider.settings_helper") as mock_settings:
        mock_settings.get_settings.return_value = fake_settings
        provider = GoogleCalendarProvider()
    return provider


def _make_account(token_data=None):
    """Create an account dict, optionally with token_ref."""
    account = {"id": 1}
    if token_data is not None:
        account["token_ref"] = json.dumps(token_data)
    return account


def _token_data():
    return {
        "access_token": "ya29.fake-access-token",
        "refresh_token": "1//fake-refresh-token",
    }


# ---------------------------------------------------------------------------
# _build_credentials tests
# ---------------------------------------------------------------------------


class TestBuildCredentials:
    def test_returns_none_when_no_token_ref(self, google_provider):
        account = _make_account()
        assert google_provider._build_credentials(account) is None

    def test_returns_none_for_invalid_json(self, google_provider):
        account = {"id": 1, "token_ref": "not-json"}
        assert google_provider._build_credentials(account) is None

    def test_returns_none_when_no_tokens(self, google_provider):
        account = {"id": 1, "token_ref": json.dumps({"some_key": "value"})}
        assert google_provider._build_credentials(account) is None

    def test_returns_credentials_with_valid_token(self, google_provider):
        account = _make_account(_token_data())
        creds = google_provider._build_credentials(account)
        assert creds is not None
        assert creds.token == "ya29.fake-access-token"
        assert creds.refresh_token == "1//fake-refresh-token"


# ---------------------------------------------------------------------------
# list_calendars tests
# ---------------------------------------------------------------------------


class TestListCalendars:
    def test_returns_empty_when_no_credentials(self, google_provider):
        account = _make_account()
        result = google_provider.list_calendars(account)
        assert result == []

    @patch("instruments.custom.calendar_hub.providers.google_provider.build")
    def test_returns_calendars_from_api(self, mock_build, google_provider):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.calendarList.return_value.list.return_value.execute.return_value = {
            "items": [
                {"id": "primary", "summary": "My Calendar", "backgroundColor": "#4285f4"},
                {"id": "work@example.com", "summary": "Work"},
            ]
        }
        account = _make_account(_token_data())
        result = google_provider.list_calendars(account)

        assert len(result) == 2
        assert result[0] == {"external_id": "primary", "name": "My Calendar", "color": "#4285f4"}
        assert result[1] == {"external_id": "work@example.com", "name": "Work", "color": None}

    @patch("instruments.custom.calendar_hub.providers.google_provider.build")
    def test_returns_empty_on_api_error(self, mock_build, google_provider):
        from googleapiclient.errors import HttpError

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.calendarList.return_value.list.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=403), content=b"Forbidden"
        )
        account = _make_account(_token_data())
        result = google_provider.list_calendars(account)
        assert result == []

    @patch("instruments.custom.calendar_hub.providers.google_provider.build")
    def test_calendar_uses_id_as_fallback_name(self, mock_build, google_provider):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.calendarList.return_value.list.return_value.execute.return_value = {"items": [{"id": "cal123"}]}
        account = _make_account(_token_data())
        result = google_provider.list_calendars(account)
        assert result[0]["name"] == "cal123"


# ---------------------------------------------------------------------------
# list_events tests
# ---------------------------------------------------------------------------


class TestListEvents:
    def test_returns_empty_when_no_credentials(self, google_provider):
        account = _make_account()
        result = google_provider.list_events(account, calendar_id=None, limit=10)
        assert result == []

    @patch("instruments.custom.calendar_hub.providers.google_provider.build")
    def test_returns_events_from_api(self, mock_build, google_provider):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": "evt1",
                    "summary": "Team Standup",
                    "start": {"dateTime": "2026-03-22T09:00:00Z"},
                    "end": {"dateTime": "2026-03-22T09:30:00Z"},
                    "attendees": [
                        {"email": "alice@example.com"},
                        {"email": "bob@example.com"},
                    ],
                    "location": "Room 42",
                    "status": "confirmed",
                },
                {
                    "id": "evt2",
                    "summary": "Lunch",
                    "start": {"date": "2026-03-22"},
                    "end": {"date": "2026-03-22"},
                    "status": "tentative",
                },
            ]
        }
        account = _make_account(_token_data())
        result = google_provider.list_events(account, calendar_id="primary", limit=10)

        assert len(result) == 2

        assert result[0]["external_id"] == "evt1"
        assert result[0]["title"] == "Team Standup"
        assert result[0]["start"] == "2026-03-22T09:00:00Z"
        assert result[0]["end"] == "2026-03-22T09:30:00Z"
        assert result[0]["attendees"] == ["alice@example.com", "bob@example.com"]
        assert result[0]["location"] == "Room 42"
        assert result[0]["status"] == "confirmed"

        # All-day event uses date instead of dateTime
        assert result[1]["start"] == "2026-03-22"
        assert result[1]["attendees"] == []
        assert result[1]["location"] is None

    @patch("instruments.custom.calendar_hub.providers.google_provider.build")
    def test_uses_primary_when_calendar_id_is_none(self, mock_build, google_provider):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.list.return_value.execute.return_value = {"items": []}

        account = _make_account(_token_data())
        google_provider.list_events(account, calendar_id=None, limit=5)

        call_kwargs = mock_service.events.return_value.list.call_args
        assert call_kwargs.kwargs.get("calendarId") == "primary" or call_kwargs[1].get("calendarId") == "primary"

    @patch("instruments.custom.calendar_hub.providers.google_provider.build")
    def test_returns_empty_on_api_error(self, mock_build, google_provider):
        from googleapiclient.errors import HttpError

        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.list.return_value.execute.side_effect = HttpError(
            resp=MagicMock(status=404), content=b"Not Found"
        )
        account = _make_account(_token_data())
        result = google_provider.list_events(account, calendar_id="nonexistent", limit=10)
        assert result == []

    @patch("instruments.custom.calendar_hub.providers.google_provider.build")
    def test_event_without_summary_gets_placeholder(self, mock_build, google_provider):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_service.events.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "id": "evt-no-title",
                    "start": {"dateTime": "2026-03-22T10:00:00Z"},
                    "end": {"dateTime": "2026-03-22T11:00:00Z"},
                }
            ]
        }
        account = _make_account(_token_data())
        result = google_provider.list_events(account, calendar_id=None, limit=5)
        assert result[0]["title"] == "(No title)"


# ---------------------------------------------------------------------------
# complete_oauth tests
# ---------------------------------------------------------------------------


class TestCompleteOAuth:
    @patch("instruments.custom.calendar_hub.providers.google_provider.settings_helper")
    def test_returns_none_when_missing_config(self, mock_settings):
        mock_settings.get_settings.return_value = {}
        provider = GoogleCalendarProvider()
        result = provider.complete_oauth("auth-code-123")
        assert result is None

    def test_returns_token_data_on_success(self, google_provider):
        mock_creds = MagicMock()
        mock_creds.token = "ya29.new-access-token"
        mock_creds.refresh_token = "1//new-refresh-token"
        mock_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_creds.client_id = "fake-client-id"
        mock_creds.client_secret = "fake-client-secret"  # pragma: allowlist secret
        mock_creds.scopes = {"https://www.googleapis.com/auth/calendar"}

        mock_flow = MagicMock()
        mock_flow.credentials = mock_creds

        with patch(
            "google_auth_oauthlib.flow.Flow.from_client_config",
            return_value=mock_flow,
        ):
            result = google_provider.complete_oauth("auth-code-123")

        assert result is not None
        assert result["access_token"] == "ya29.new-access-token"
        assert result["refresh_token"] == "1//new-refresh-token"

    def test_returns_none_on_exchange_failure(self, google_provider):
        with patch(
            "google_auth_oauthlib.flow.Flow.from_client_config",
            side_effect=Exception("network error"),
        ):
            result = google_provider.complete_oauth("bad-code")
        assert result is None
