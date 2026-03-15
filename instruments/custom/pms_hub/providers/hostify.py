"""
Hostify Provider Adapter
Integration with Hostify's REST API for vacation rental management
"""

from datetime import date
from decimal import Decimal
from typing import Any

from python.helpers.datetime_utils import parse_iso_date, parse_iso_datetime, utc_now

try:
    import httpx
except ImportError:
    httpx = None

from ..canonical_models import (
    Calendar,
    Message,
    Property,
    Reservation,
    ReservationStatus,
    Review,
)
from ..pms_provider import PMSProvider, ProviderType


class HostifyProvider(PMSProvider):
    """
    Hostify PMS Provider Adapter
    All-in-one vacation rental management solution
    """

    BASE_URL = "https://api.hostify.com/v2"

    def __init__(self, config: dict[str, Any]):
        """Initialize Hostify provider"""
        super().__init__(ProviderType.HOSTIFY, config)

        if httpx is None:
            raise ImportError("httpx is required for Hostify provider. Install it with: pip install httpx")

        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = config.get("api_key")
        self.account_id = config.get("account_id")

    async def authenticate(self) -> bool:
        """Authenticate with Hostify API"""
        try:
            headers = self._get_headers()
            response = await self.client.get(f"{self.BASE_URL}/accounts/me", headers=headers)
            self._authenticated = response.status_code == 200
            return self._authenticated
        except Exception as e:
            print(f"Hostify authentication failed: {e}")
            return False

    async def get_properties(self) -> list[Property]:
        """Fetch all properties from Hostify"""
        try:
            properties = []
            url = f"{self.BASE_URL}/properties"
            headers = self._get_headers()
            params = {"limit": 100, "offset": 0}

            while True:
                response = await self.client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("data", [])
                if not items:
                    break

                for item in items:
                    properties.append(self._transform_property(item))

                params["offset"] += 100
                if len(items) < 100:
                    break

            return properties
        except Exception as e:
            print(f"Error fetching properties from Hostify: {e}")
            return []

    async def get_property(self, provider_id: str) -> Property | None:
        """Fetch single property from Hostify"""
        try:
            url = f"{self.BASE_URL}/properties/{provider_id}"
            headers = self._get_headers()
            response = await self.client.get(url, headers=headers)

            if response.status_code == 200:
                return self._transform_property(response.json().get("data", {}))
            return None
        except Exception as e:
            print(f"Error fetching property from Hostify: {e}")
            return None

    async def get_reservations(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Reservation]:
        """Fetch reservations from Hostify"""
        try:
            reservations = []
            url = f"{self.BASE_URL}/reservations"
            headers = self._get_headers()
            params = {"limit": 100, "offset": 0}

            if property_id:
                params["property_id"] = property_id
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

            while True:
                response = await self.client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("data", [])
                if not items:
                    break

                for item in items:
                    reservations.append(self._transform_reservation(item))

                params["offset"] += 100
                if len(items) < 100:
                    break

            return reservations
        except Exception as e:
            print(f"Error fetching reservations from Hostify: {e}")
            return []

    async def get_reservation(self, provider_id: str) -> Reservation | None:
        """Fetch single reservation from Hostify"""
        try:
            url = f"{self.BASE_URL}/reservations/{provider_id}"
            headers = self._get_headers()
            response = await self.client.get(url, headers=headers)

            if response.status_code == 200:
                return self._transform_reservation(response.json().get("data", {}))
            return None
        except Exception as e:
            print(f"Error fetching reservation from Hostify: {e}")
            return None

    async def get_calendar(
        self,
        property_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Calendar]:
        """Fetch calendar from Hostify"""
        try:
            url = f"{self.BASE_URL}/properties/{property_id}/calendar"
            headers = self._get_headers()
            params = {}

            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

            response = await self.client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                calendars = []
                for item in response.json().get("data", []):
                    calendars.append(self._transform_calendar(item, property_id))
                return calendars

            return []
        except Exception as e:
            print(f"Error fetching calendar from Hostify: {e}")
            return []

    async def get_messages(
        self,
        property_id: str | None = None,
        unread_only: bool = False,
    ) -> list[Message]:
        """Fetch messages from Hostify"""
        try:
            messages = []
            url = f"{self.BASE_URL}/messages"
            headers = self._get_headers()
            params = {"limit": 100, "offset": 0}

            if unread_only:
                params["unread"] = True

            while True:
                response = await self.client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("data", [])
                if not items:
                    break

                for item in items:
                    messages.append(self._transform_message(item))

                params["offset"] += 100
                if len(items) < 100:
                    break

            return messages
        except Exception as e:
            print(f"Error fetching messages from Hostify: {e}")
            return []

    async def send_message(
        self,
        reservation_id: str,
        subject: str,
        body: str,
    ) -> bool:
        """Send message to guest through Hostify"""
        try:
            url = f"{self.BASE_URL}/reservations/{reservation_id}/messages"
            headers = self._get_headers()
            payload = {"subject": subject, "message": body}

            response = await self.client.post(url, headers=headers, json=payload)
            return response.status_code in (200, 201)
        except Exception as e:
            print(f"Error sending message via Hostify: {e}")
            return False

    async def get_reviews(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
    ) -> list[Review]:
        """Fetch reviews from Hostify"""
        try:
            reviews = []
            url = f"{self.BASE_URL}/reviews"
            headers = self._get_headers()
            params = {"limit": 100, "offset": 0}

            while True:
                response = await self.client.get(url, headers=headers, params=params)
                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("data", [])
                if not items:
                    break

                for item in items:
                    review = self._transform_review(item)
                    if start_date is None or review.created_at.date() >= start_date:
                        reviews.append(review)

                params["offset"] += 100
                if len(items) < 100:
                    break

            return reviews
        except Exception as e:
            print(f"Error fetching reviews from Hostify: {e}")
            return []

    async def update_calendar(self, calendar_events: list[Calendar]) -> bool:
        """Update calendar in Hostify"""
        try:
            # Group by property
            by_property: dict[str, list[Calendar]] = {}
            for event in calendar_events:
                key = event.property_provider_id
                if key not in by_property:
                    by_property[key] = []
                by_property[key].append(event)

            for property_id, events in by_property.items():
                url = f"{self.BASE_URL}/properties/{property_id}/calendar"
                headers = self._get_headers()
                payload = {
                    "data": [
                        {
                            "date": event.date.isoformat(),
                            "status": event.status,
                            "minimum_stay": event.min_nights,
                        }
                        for event in events
                    ]
                }

                response = await self.client.put(url, headers=headers, json=payload)
                if response.status_code not in (200, 201):
                    return False

            return True
        except Exception as e:
            print(f"Error updating calendar in Hostify: {e}")
            return False

    async def update_pricing(
        self,
        property_id: str,
        nightly_price: float | None = None,
        calendar_prices: dict[date, float] | None = None,
    ) -> bool:
        """Update pricing in Hostify"""
        try:
            url = f"{self.BASE_URL}/properties/{property_id}/pricing"
            headers = self._get_headers()
            payload = {}

            if nightly_price:
                payload["nightly_price"] = nightly_price

            if calendar_prices:
                payload["calendar"] = [{"date": d.isoformat(), "price": p} for d, p in calendar_prices.items()]

            response = await self.client.put(url, headers=headers, json=payload)
            return response.status_code in (200, 201)
        except Exception as e:
            print(f"Error updating pricing in Hostify: {e}")
            return False

    def get_provider_name(self) -> str:
        return "Hostify"

    def get_webhook_events(self) -> list[str]:
        return [
            "reservation.created",
            "reservation.updated",
            "reservation.cancelled",
            "message.created",
            "review.created",
        ]

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "PMS-Hub/1.0",
        }

    def _transform_property(self, data: dict[str, Any]) -> Property:
        """Transform Hostify property"""
        return Property(
            provider_id=str(data.get("id")),
            provider="hostify",
            external_id=data.get("external_id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            property_type=data.get("type", "vacation_rental"),
            address=data.get("address", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            zip_code=data.get("zip_code"),
            bedrooms=int(data.get("bedrooms", 1)),
            bathrooms=float(data.get("bathrooms", 1.0)),
            max_guests=int(data.get("max_guests", 1)),
            base_price=Decimal(str(data.get("price", 0))),
            synced_at=utc_now(),
        )

    def _transform_reservation(self, data: dict[str, Any]) -> Reservation:
        """Transform Hostify reservation"""
        status_map = {
            "pending": ReservationStatus.PENDING,
            "confirmed": ReservationStatus.CONFIRMED,
            "cancelled": ReservationStatus.CANCELLED,
        }

        check_in = parse_iso_date(data.get("checkin"))
        check_out = parse_iso_date(data.get("checkout"))

        return Reservation(
            provider_id=str(data.get("id")),
            provider="hostify",
            property_provider_id=str(data.get("property_id", "")),
            check_in_date=check_in,
            check_out_date=check_out,
            nights=(check_out - check_in).days,
            guests_count=int(data.get("guests", 1)),
            total_price=Decimal(str(data.get("total", 0))),
            status=status_map.get(data.get("status", "confirmed"), ReservationStatus.CONFIRMED),
            guest_name=data.get("guest_name", ""),
            guest_email=data.get("guest_email", ""),
            source="pms",
            synced_at=utc_now(),
        )

    def _transform_message(self, data: dict[str, Any]) -> Message:
        """Transform Hostify message"""
        return Message(
            provider_id=str(data.get("id")),
            provider="hostify",
            guest_provider_id=str(data.get("guest_id", "")),
            sender="host" if data.get("from_host") else "guest",
            body=data.get("message", ""),
            is_read=bool(data.get("read")),
            created_at=parse_iso_datetime(data.get("created_at")),
            synced_at=utc_now(),
        )

    def _transform_review(self, data: dict[str, Any]) -> Review:
        """Transform Hostify review"""
        return Review(
            provider_id=str(data.get("id")),
            provider="hostify",
            reservation_provider_id=str(data.get("reservation_id", "")),
            guest_provider_id=str(data.get("guest_id", "")),
            rating=float(data.get("rating", 5.0)),
            comment=data.get("comment", ""),
            created_at=parse_iso_datetime(data.get("created_at")),
            synced_at=utc_now(),
        )

    def _transform_calendar(self, data: dict[str, Any], property_id: str) -> Calendar:
        """Transform Hostify calendar"""
        return Calendar(
            provider_id=str(data.get("id", "")),
            provider="hostify",
            property_provider_id=property_id,
            date=parse_iso_date(data.get("date")),
            status=data.get("status", "available"),
            price=Decimal(str(data.get("price"))) if data.get("price") else None,
            synced_at=utc_now(),
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
