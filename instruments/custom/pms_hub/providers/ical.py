"""
iCal Provider Adapter
Generic iCal feed support for calendar synchronization
Provides basic calendar blocking without detailed reservation data
"""

from datetime import date, datetime
from typing import Any

from python.helpers.datetime_utils import utc_now

try:
    import httpx
    import icalendar
except ImportError:
    icalendar = None
    httpx = None

from ..canonical_models import (
    Calendar,
    Message,
    Property,
    Reservation,
    Review,
)
from ..pms_provider import PMSProvider, ProviderType


class ICalProvider(PMSProvider):
    """
    Generic iCal Provider Adapter
    Supports any platform with iCal feed support (AirBnb, VRBO, Booking.com, etc.)
    Limited to calendar synchronization - no reservation details or messaging
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize iCal provider"""
        super().__init__(ProviderType.ICAL, config)

        if httpx is None:
            raise ImportError("httpx is required for iCal provider. Install it with: pip install httpx")

        self.client = httpx.AsyncClient(timeout=30.0)
        self.ical_url = config.get("ical_url")
        self.property_id = config.get("property_id")
        self.property_name = config.get("property_name", "Unknown")

    async def authenticate(self) -> bool:
        """Verify iCal feed is accessible"""
        try:
            if not self.ical_url:
                return False

            response = await self.client.get(self.ical_url, follow_redirects=True)
            self._authenticated = response.status_code == 200
            return self._authenticated
        except Exception as e:
            print(f"iCal authentication failed: {e}")
            return False

    async def get_properties(self) -> list[Property]:
        """iCal only supports single property"""
        return [
            Property(
                provider_id=self.property_id or "ical_default",
                provider="ical",
                external_id="",
                name=self.property_name,
                address="",
                city="",
                state="",
            )
        ]

    async def get_property(self, provider_id: str) -> Property | None:
        """Get property info from iCal"""
        if provider_id == self.property_id or provider_id == "ical_default":
            return (await self.get_properties())[0]
        return None

    async def get_reservations(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Reservation]:
        """iCal doesn't provide reservation details"""
        return []

    async def get_reservation(self, provider_id: str) -> Reservation | None:
        """iCal doesn't provide individual reservation details"""
        return None

    async def get_calendar(
        self,
        property_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Calendar]:
        """Fetch calendar availability from iCal feed"""
        try:
            if not self.ical_url:
                return []

            response = await self.client.get(self.ical_url, follow_redirects=True)
            if response.status_code != 200:
                return []

            if icalendar is None:
                raise ImportError("icalendar is required. Install it with: pip install icalendar")

            calendars = []
            ical_data = icalendar.Calendar.from_ical(response.content)

            for component in ical_data.walk():
                if component.name == "VEVENT":
                    event_date = component.get("dtstart").dt
                    if isinstance(event_date, datetime):
                        event_date = event_date.date()

                    # Filter by date range if provided
                    if start_date and event_date < start_date:
                        continue
                    if end_date and event_date > end_date:
                        continue

                    # Create calendar entry for booked date
                    calendar = Calendar(
                        provider_id=component.get("uid", ""),
                        provider="ical",
                        property_provider_id=property_id,
                        date=event_date,
                        status="booked",  # iCal events are booked dates
                        synced_at=utc_now(),
                    )
                    calendars.append(calendar)

            return calendars
        except Exception as e:
            print(f"Error fetching iCal calendar: {e}")
            return []

    async def get_messages(
        self,
        property_id: str | None = None,
        unread_only: bool = False,
    ) -> list[Message]:
        """iCal doesn't support messaging"""
        return []

    async def send_message(
        self,
        reservation_id: str,
        subject: str,
        body: str,
    ) -> bool:
        """iCal doesn't support messaging"""
        return False

    async def get_reviews(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
    ) -> list[Review]:
        """iCal doesn't provide reviews"""
        return []

    async def update_calendar(self, calendar_events: list[Calendar]) -> bool:
        """
        iCal is read-only - updates must be done at the source platform
        This is a placeholder that always returns False
        """
        print("iCal is read-only. Calendar updates must be made at the source platform.")
        return False

    async def update_pricing(
        self,
        property_id: str,
        nightly_price: float | None = None,
        calendar_prices: dict[date, float] | None = None,
    ) -> bool:
        """iCal doesn't support pricing management"""
        return False

    def get_provider_name(self) -> str:
        return "iCal (Generic)"

    def get_webhook_events(self) -> list[str]:
        """iCal doesn't support webhooks - polling only"""
        return []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
