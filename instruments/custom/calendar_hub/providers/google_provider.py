import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from instruments.custom.calendar_hub.providers.base import CalendarProvider
from python.helpers import settings as settings_helper

logger = logging.getLogger(__name__)

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/calendar"]


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

    def _build_credentials(self, account: dict[str, Any]) -> Credentials | None:
        """Build Google OAuth credentials from the account's token_ref field.

        The token_ref stores a JSON string containing access_token, refresh_token,
        and optionally token_uri, client_id, client_secret, and scopes.
        Returns None if credentials cannot be constructed.
        """
        token_ref = account.get("token_ref")
        if not token_ref:
            return None

        try:
            token_data = json.loads(token_ref)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid token_ref JSON for account %s", account.get("id"))
            return None

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        if not access_token and not refresh_token:
            logger.warning("No access or refresh token for account %s", account.get("id"))
            return None

        return Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri=token_data.get("token_uri", TOKEN_URI),
            client_id=token_data.get("client_id", self.client_id),
            client_secret=token_data.get("client_secret", self.client_secret),
            scopes=token_data.get("scopes", SCOPES),
        )

    def _build_service(self, account: dict[str, Any]):
        """Build a Google Calendar API service from the account credentials.

        Returns None if credentials are missing or invalid.
        """
        creds = self._build_credentials(account)
        if creds is None:
            return None
        try:
            return build("calendar", "v3", credentials=creds, cache_discovery=False)
        except Exception:
            logger.warning("Failed to build Google Calendar service for account %s", account.get("id"), exc_info=True)
            return None

    def list_calendars(self, account: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch the user's calendar list from Google Calendar API.

        Returns a list of dicts with keys: external_id, name, color.
        Returns an empty list if credentials are missing or the API call fails.
        """
        service = self._build_service(account)
        if service is None:
            if account.get("token_ref"):
                logger.warning("Cannot list calendars: failed to build service for account %s", account.get("id"))
            return []

        try:
            result = service.calendarList().list().execute()
            calendars = []
            for item in result.get("items", []):
                calendars.append(
                    {
                        "external_id": item["id"],
                        "name": item.get("summary", item["id"]),
                        "color": item.get("backgroundColor"),
                    }
                )
            return calendars
        except HttpError as e:
            logger.warning("Google Calendar API error listing calendars for account %s: %s", account.get("id"), e)
            return []
        except Exception:
            logger.warning("Unexpected error listing calendars for account %s", account.get("id"), exc_info=True)
            return []

    def list_events(self, account: dict[str, Any], calendar_id: str | None, limit: int) -> list[dict[str, Any]]:
        """Fetch upcoming events from a specific Google Calendar.

        Args:
            account: Account dict containing at least 'id' and 'token_ref'.
            calendar_id: The Google Calendar ID string, or None for the primary calendar.
            limit: Maximum number of events to return.

        Returns a list of dicts with keys matching the DB schema:
            title, start, end, attendees, location, status, external_id.
        Returns an empty list if credentials are missing or the API call fails.
        """
        service = self._build_service(account)
        if service is None:
            if account.get("token_ref"):
                logger.warning("Cannot list events: failed to build service for account %s", account.get("id"))
            return []

        cal_id = calendar_id or "primary"
        now = datetime.now(timezone.utc).isoformat()

        try:
            result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    timeMin=now,
                    maxResults=limit,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = []
            for item in result.get("items", []):
                start = item.get("start", {})
                end = item.get("end", {})
                attendees_raw = item.get("attendees", [])
                attendee_emails = [a.get("email", "") for a in attendees_raw if a.get("email")]

                events.append(
                    {
                        "external_id": item.get("id"),
                        "title": item.get("summary", "(No title)"),
                        "start": start.get("dateTime") or start.get("date", ""),
                        "end": end.get("dateTime") or end.get("date", ""),
                        "attendees": attendee_emails,
                        "location": item.get("location"),
                        "status": item.get("status", "confirmed"),
                    }
                )
            return events
        except HttpError as e:
            logger.warning("Google Calendar API error listing events for account %s: %s", account.get("id"), e)
            return []
        except Exception:
            logger.warning("Unexpected error listing events for account %s", account.get("id"), exc_info=True)
            return []

    def complete_oauth(self, code: str) -> dict[str, Any] | None:
        """Exchange an authorization code for OAuth tokens.

        Args:
            code: The authorization code received from the OAuth redirect.

        Returns a dict with access_token, refresh_token, and metadata for storage
        as the account's token_ref. Returns None if the exchange fails.
        """
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            logger.warning("Cannot complete OAuth: missing client_id, client_secret, or redirect_uri")
            return None

        try:
            from google_auth_oauthlib.flow import Flow

            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": self.AUTH_ENDPOINT,
                        "token_uri": TOKEN_URI,
                    }
                },
                scopes=SCOPES,
                redirect_uri=self.redirect_uri,
            )
            flow.fetch_token(code=code)
            creds = flow.credentials
            token_data = {
                "access_token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes) if creds.scopes else SCOPES,
            }
            return token_data
        except Exception:
            logger.warning("Failed to exchange OAuth code for tokens", exc_info=True)
            return None
