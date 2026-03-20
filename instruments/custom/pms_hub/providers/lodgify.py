"""
Lodgify Provider Adapter
Integration with Lodgify's REST API for vacation rental management
API: https://docs.lodgify.com/reference/webhooks
"""

import hashlib
import hmac
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None

from python.helpers.datetime_utils import parse_iso_date, parse_iso_datetime

from ..canonical_models import (
    Calendar,
    Message,
    MessageType,
    PaymentStatus,
    Property,
    Reservation,
    ReservationStatus,
    Review,
)
from ..pms_provider import PMSProvider, ProviderType


class LodgifyProvider(PMSProvider):
    """
    Lodgify PMS Provider Adapter
    Provides full integration with Lodgify's REST API
    Lodgify is an Airbnb Preferred+ Software Partner
    """

    BASE_URL = "https://api.lodgify.com"

    def __init__(self, config: dict[str, Any]):
        """Initialize Lodgify provider"""
        super().__init__(ProviderType.LODGIFY, config)

        if httpx is None:
            raise ImportError("httpx is required for Lodgify provider. Install it with: pip install httpx")

        self.client = httpx.AsyncClient(timeout=30.0)
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")  # For webhook signature verification
        self.account_id = config.get("account_id")

    async def authenticate(self) -> bool:
        """
        Authenticate with Lodgify API

        Returns:
            True if authentication successful
        """
        try:
            # Test authentication by fetching account info
            headers = self._get_headers()
            response = await self.client.get(f"{self.BASE_URL}/account", headers=headers)

            if response.status_code == 200:
                self._authenticated = True
                return True
            return False
        except Exception as e:
            print(f"Lodgify authentication failed: {e}")
            return False

    async def get_properties(self) -> list[Property]:
        """
        Fetch all properties from Lodgify

        Returns:
            List of Property objects
        """
        try:
            properties = []
            url = f"{self.BASE_URL}/properties"
            headers = self._get_headers()

            # Lodgify uses cursor-based pagination
            cursor = None

            while True:
                params = {"limit": 100}
                if cursor:
                    params["cursor"] = cursor

                response = await self.client.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("data", [])

                if not items:
                    break

                for item in items:
                    property_obj = self._transform_property(item)
                    properties.append(property_obj)

                # Check if there's a next cursor
                cursor = data.get("paging", {}).get("next_cursor")
                if not cursor:
                    break

            return properties
        except Exception as e:
            print(f"Error fetching properties from Lodgify: {e}")
            return []

    async def get_property(self, provider_id: str) -> Property | None:
        """
        Fetch single property from Lodgify

        Args:
            provider_id: Lodgify property ID

        Returns:
            Property object or None
        """
        try:
            url = f"{self.BASE_URL}/properties/{provider_id}"
            headers = self._get_headers()
            response = await self.client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return self._transform_property(data.get("data", {}))

            return None
        except Exception as e:
            print(f"Error fetching property {provider_id} from Lodgify: {e}")
            return None

    async def get_reservations(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Reservation]:
        """
        Fetch reservations from Lodgify

        Args:
            property_id: Optional filter by property
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of Reservation objects
        """
        try:
            reservations = []
            url = f"{self.BASE_URL}/reservations"
            headers = self._get_headers()

            params = {"limit": 100}
            if property_id:
                params["property_id"] = property_id

            if start_date:
                params["start_date"] = start_date.isoformat()

            if end_date:
                params["end_date"] = end_date.isoformat()

            cursor = None
            while True:
                if cursor:
                    params["cursor"] = cursor

                response = await self.client.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("data", [])

                if not items:
                    break

                for item in items:
                    reservation = self._transform_reservation(item)
                    reservations.append(reservation)

                cursor = data.get("paging", {}).get("next_cursor")
                if not cursor:
                    break

            return reservations
        except Exception as e:
            print(f"Error fetching reservations from Lodgify: {e}")
            return []

    async def get_reservation(self, provider_id: str) -> Reservation | None:
        """
        Fetch single reservation from Lodgify

        Args:
            provider_id: Lodgify reservation ID

        Returns:
            Reservation object or None
        """
        try:
            url = f"{self.BASE_URL}/reservations/{provider_id}"
            headers = self._get_headers()
            response = await self.client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return self._transform_reservation(data.get("data", {}))

            return None
        except Exception as e:
            print(f"Error fetching reservation {provider_id} from Lodgify: {e}")
            return None

    async def get_calendar(
        self,
        property_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Calendar]:
        """
        Fetch calendar/availability from Lodgify

        Args:
            property_id: Lodgify property ID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of Calendar objects
        """
        try:
            calendars = []
            url = f"{self.BASE_URL}/properties/{property_id}/availability"
            headers = self._get_headers()

            params = {}
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()

            response = await self.client.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                items = data.get("data", [])

                for item in items:
                    calendar = self._transform_calendar(item, property_id)
                    calendars.append(calendar)

            return calendars
        except Exception as e:
            print(f"Error fetching calendar from Lodgify: {e}")
            return []

    async def get_messages(
        self,
        property_id: str | None = None,
        unread_only: bool = False,
    ) -> list[Message]:
        """
        Fetch messages from Lodgify

        Args:
            property_id: Optional property filter
            unread_only: Only unread messages

        Returns:
            List of Message objects
        """
        try:
            messages = []
            url = f"{self.BASE_URL}/messages"
            headers = self._get_headers()

            params = {"limit": 100}
            if unread_only:
                params["unread"] = True

            cursor = None
            while True:
                if cursor:
                    params["cursor"] = cursor

                response = await self.client.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("data", [])

                if not items:
                    break

                for item in items:
                    message = self._transform_message(item)
                    messages.append(message)

                cursor = data.get("paging", {}).get("next_cursor")
                if not cursor:
                    break

            return messages
        except Exception as e:
            print(f"Error fetching messages from Lodgify: {e}")
            return []

    async def send_message(
        self,
        reservation_id: str,
        subject: str,
        body: str,
    ) -> bool:
        """
        Send message to guest through Lodgify

        Args:
            reservation_id: Lodgify reservation ID
            subject: Message subject
            body: Message body

        Returns:
            True if successful
        """
        try:
            url = f"{self.BASE_URL}/reservations/{reservation_id}/messages"
            headers = self._get_headers()

            payload = {
                "subject": subject,
                "message": body,
            }

            response = await self.client.post(url, headers=headers, json=payload)
            return response.status_code in (200, 201)
        except Exception as e:
            print(f"Error sending message via Lodgify: {e}")
            return False

    async def get_reviews(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
    ) -> list[Review]:
        """
        Fetch reviews from Lodgify

        Args:
            property_id: Optional property filter
            start_date: Only reviews after this date

        Returns:
            List of Review objects
        """
        try:
            reviews = []
            url = f"{self.BASE_URL}/reviews"
            headers = self._get_headers()

            params = {"limit": 100}
            if property_id:
                params["property_id"] = property_id

            cursor = None
            while True:
                if cursor:
                    params["cursor"] = cursor

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

                cursor = data.get("paging", {}).get("next_cursor")
                if not cursor:
                    break

            return reviews
        except Exception as e:
            print(f"Error fetching reviews from Lodgify: {e}")
            return []

    async def update_calendar(self, calendar_events: list[Calendar]) -> bool:
        """
        Update calendar in Lodgify

        Args:
            calendar_events: List of Calendar objects to update

        Returns:
            True if successful
        """
        try:
            headers = self._get_headers()

            # Group by property
            by_property: dict[str, list[Calendar]] = {}
            for event in calendar_events:
                if event.property_provider_id not in by_property:
                    by_property[event.property_provider_id] = []
                by_property[event.property_provider_id].append(event)

            # Update each property
            for property_id, events in by_property.items():
                payload = {
                    "data": [
                        {
                            "date": event.date.isoformat(),
                            "status": event.status,
                            "minimum_stay": event.min_nights,
                            "price": str(event.price) if event.price else None,
                        }
                        for event in events
                    ]
                }

                response = await self.client.put(
                    f"{self.BASE_URL}/properties/{property_id}/availability",
                    headers=headers,
                    json=payload,
                )

                if response.status_code not in (200, 201):
                    return False

            return True
        except Exception as e:
            print(f"Error updating calendar in Lodgify: {e}")
            return False

    async def update_pricing(
        self,
        property_id: str,
        nightly_price: float | None = None,
        calendar_prices: dict[date, float] | None = None,
    ) -> bool:
        """
        Update pricing in Lodgify

        Args:
            property_id: Lodgify property ID
            nightly_price: Base nightly price
            calendar_prices: Dict of date-specific prices

        Returns:
            True if successful
        """
        try:
            url = f"{self.BASE_URL}/properties/{property_id}/pricing"
            headers = self._get_headers()

            payload = {}
            if nightly_price:
                payload["nightly_price"] = nightly_price

            if calendar_prices:
                payload["calendar"] = [
                    {
                        "date": date_obj.isoformat(),
                        "price": price,
                    }
                    for date_obj, price in calendar_prices.items()
                ]

            response = await self.client.put(url, headers=headers, json=payload)
            return response.status_code in (200, 201)
        except Exception as e:
            print(f"Error updating pricing in Lodgify: {e}")
            return False

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "Lodgify"

    def get_webhook_events(self) -> list[str]:
        """Get supported webhook events"""
        return [
            "reservation.created",
            "reservation.updated",
            "reservation.cancelled",
            "message.created",
            "review.created",
        ]

    def verify_webhook(self, payload: dict[str, Any], signature: str) -> bool:
        """
        Verify Lodgify webhook signature using SHA256

        Args:
            payload: Webhook payload
            signature: Signature header (ms-signature)

        Returns:
            True if signature is valid
        """
        if not self.api_secret:
            return False

        try:
            # Lodgify uses ms-signature header with SHA256
            payload_str = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            expected_signature = hmac.new(
                self.api_secret.encode(),
                payload_str.encode(),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            print(f"Webhook signature verification failed: {e}")
            return False

    # Helper methods for data transformation

    def _get_headers(self) -> dict[str, str]:
        """Build request headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "PMS-Hub/1.0",
        }

    def _transform_property(self, data: dict[str, Any]) -> Property:
        """Transform Lodgify property to canonical model"""
        return Property(
            provider_id=str(data.get("id")),
            provider="lodgify",
            external_id=data.get("external_id", ""),
            name=data.get("name", ""),
            description=data.get("description"),
            property_type=data.get("property_type", "vacation_rental"),
            address=data.get("address", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            zip_code=data.get("zip_code"),
            country=data.get("country", "USA"),
            latitude=float(data.get("latitude")) if data.get("latitude") else None,
            longitude=float(data.get("longitude")) if data.get("longitude") else None,
            bedrooms=int(data.get("bedrooms", 1)),
            bathrooms=float(data.get("bathrooms", 1.0)),
            max_guests=int(data.get("max_guests", 1)),
            base_price=Decimal(str(data.get("nightly_price", 0))),
            currency=data.get("currency", "USD"),
            synced_at=datetime.now(timezone.utc),
        )

    def _transform_reservation(self, data: dict[str, Any]) -> Reservation:
        """Transform Lodgify reservation to canonical model"""
        status_map = {
            "pending": ReservationStatus.PENDING,
            "confirmed": ReservationStatus.CONFIRMED,
            "cancelled": ReservationStatus.CANCELLED,
            "checked_in": ReservationStatus.CHECKED_IN,
            "checked_out": ReservationStatus.CHECKED_OUT,
        }

        check_in = parse_iso_date(data.get("check_in_date"))
        check_out = parse_iso_date(data.get("check_out_date"))
        nights = (check_out - check_in).days

        return Reservation(
            provider_id=str(data.get("id")),
            provider="lodgify",
            property_provider_id=str(data.get("property_id", "")),
            confirmation_code=data.get("confirmation_code", ""),
            check_in_date=check_in,
            check_out_date=check_out,
            nights=nights,
            guests_count=int(data.get("guest_count", 1)),
            base_price=Decimal(str(data.get("base_price", 0))),
            discount=Decimal(str(data.get("discount", 0))),
            service_fee=Decimal(str(data.get("service_fee", 0))),
            cleaning_fee=Decimal(str(data.get("cleaning_fee", 0))),
            taxes=Decimal(str(data.get("taxes", 0))),
            total_price=Decimal(str(data.get("total_price", 0))),
            currency=data.get("currency", "USD"),
            status=status_map.get(data.get("status", "confirmed"), ReservationStatus.CONFIRMED),
            payment_status=PaymentStatus.PAID if data.get("is_paid") else PaymentStatus.PENDING,
            guest_name=data.get("guest_name", ""),
            guest_email=data.get("guest_email", ""),
            guest_phone=data.get("guest_phone"),
            special_requests=data.get("special_requests"),
            source="pms",
            synced_at=datetime.now(timezone.utc),
        )

    def _transform_message(self, data: dict[str, Any]) -> Message:
        """Transform Lodgify message to canonical model"""
        return Message(
            provider_id=str(data.get("id")),
            provider="lodgify",
            guest_provider_id=str(data.get("guest_id", "")),
            reservation_provider_id=str(data.get("reservation_id")) if data.get("reservation_id") else None,
            sender="host" if data.get("from_host") else "guest",
            message_type=MessageType.INQUIRY,
            subject=data.get("subject"),
            body=data.get("message", ""),
            is_read=bool(data.get("is_read")),
            requires_response=not bool(data.get("from_host")),
            created_at=parse_iso_datetime(data.get("created_at")),
            synced_at=datetime.now(timezone.utc),
        )

    def _transform_review(self, data: dict[str, Any]) -> Review:
        """Transform Lodgify review to canonical model"""
        return Review(
            provider_id=str(data.get("id")),
            provider="lodgify",
            reservation_provider_id=str(data.get("reservation_id", "")),
            guest_provider_id=str(data.get("guest_id", "")),
            rating=float(data.get("rating", 5.0)),
            title=data.get("title"),
            comment=data.get("comment", ""),
            created_at=parse_iso_datetime(data.get("created_at")),
            synced_at=datetime.now(timezone.utc),
        )

    def _transform_calendar(self, data: dict[str, Any], property_id: str) -> Calendar:
        """Transform Lodgify calendar to canonical model"""
        return Calendar(
            provider_id=str(data.get("id", "")),
            provider="lodgify",
            property_provider_id=property_id,
            date=parse_iso_date(data.get("date")),
            status=data.get("status", "available"),
            price=Decimal(str(data.get("price"))) if data.get("price") else None,
            min_nights=int(data.get("minimum_stay", 1)),
            synced_at=datetime.now(timezone.utc),
        )

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.client.aclose()
