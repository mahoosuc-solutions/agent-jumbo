"""
Hostaway Provider Adapter
Integration with Hostaway's REST API for property management and channel coordination
API: https://api.hostaway.com/documentation
"""

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


class HostawayProvider(PMSProvider):
    """
    Hostaway PMS Provider Adapter
    Provides full integration with Hostaway's REST API
    """

    BASE_URL = "https://api.hostaway.com"
    OAUTH_URL = "https://api.hostaway.com/oauth"

    def __init__(self, config: dict[str, Any]):
        """Initialize Hostaway provider"""
        super().__init__(ProviderType.HOSTAWAY, config)

        if httpx is None:
            raise ImportError("httpx is required for Hostaway provider. Install it with: pip install httpx")

        self.api_token: str | None = None
        self.client = httpx.AsyncClient(timeout=30.0)

        # Load config
        self.user_id = config.get("user_id")
        self.api_key = config.get("api_key")
        self.access_token = config.get("access_token")

    async def authenticate(self) -> bool:
        """
        Authenticate with Hostaway API

        Returns:
            True if authentication successful
        """
        try:
            # Test authentication by fetching user data
            headers = self._get_headers()
            response = await self.client.get(f"{self.BASE_URL}/v1/user", headers=headers)

            if response.status_code == 200:
                self._authenticated = True
                return True
            return False
        except Exception as e:
            print(f"Hostaway authentication failed: {e}")
            return False

    async def get_properties(self) -> list[Property]:
        """
        Fetch all properties from Hostaway

        Returns:
            List of Property objects
        """
        try:
            properties = []
            url = f"{self.BASE_URL}/v1/properties"
            headers = self._get_headers()

            # Hostaway uses pagination
            offset = 0
            limit = 100

            while True:
                params = {"offset": offset, "limit": limit}
                response = await self.client.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("result", {}).get("properties", [])

                if not items:
                    break

                for item in items:
                    property_obj = self._transform_property(item)
                    properties.append(property_obj)

                offset += limit

                # Check if there are more items
                if len(items) < limit:
                    break

            return properties
        except Exception as e:
            print(f"Error fetching properties from Hostaway: {e}")
            return []

    async def get_property(self, provider_id: str) -> Property | None:
        """
        Fetch single property from Hostaway

        Args:
            provider_id: Hostaway property ID

        Returns:
            Property object or None
        """
        try:
            url = f"{self.BASE_URL}/v1/properties/{provider_id}"
            headers = self._get_headers()
            response = await self.client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return self._transform_property(data.get("result", {}))

            return None
        except Exception as e:
            print(f"Error fetching property {provider_id} from Hostaway: {e}")
            return None

    async def get_reservations(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Reservation]:
        """
        Fetch reservations from Hostaway

        Args:
            property_id: Optional filter by property
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of Reservation objects
        """
        try:
            reservations = []
            url = f"{self.BASE_URL}/v1/reservations"
            headers = self._get_headers()

            # Build filter parameters
            params = {
                "limit": 100,
                "offset": 0,
            }

            if property_id:
                params["propertyId"] = property_id

            if start_date:
                params["startDate"] = start_date.isoformat()

            if end_date:
                params["endDate"] = end_date.isoformat()

            # Pagination
            offset = 0
            while True:
                params["offset"] = offset
                response = await self.client.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("result", {}).get("reservations", [])

                if not items:
                    break

                for item in items:
                    reservation = self._transform_reservation(item)
                    reservations.append(reservation)

                offset += 100
                if len(items) < 100:
                    break

            return reservations
        except Exception as e:
            print(f"Error fetching reservations from Hostaway: {e}")
            return []

    async def get_reservation(self, provider_id: str) -> Reservation | None:
        """
        Fetch single reservation from Hostaway

        Args:
            provider_id: Hostaway reservation ID

        Returns:
            Reservation object or None
        """
        try:
            url = f"{self.BASE_URL}/v1/reservations/{provider_id}"
            headers = self._get_headers()
            response = await self.client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return self._transform_reservation(data.get("result", {}))

            return None
        except Exception as e:
            print(f"Error fetching reservation {provider_id} from Hostaway: {e}")
            return None

    async def get_calendar(
        self,
        property_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Calendar]:
        """
        Fetch calendar/availability from Hostaway

        Args:
            property_id: Hostaway property ID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of Calendar objects
        """
        try:
            calendars = []
            url = f"{self.BASE_URL}/v1/properties/{property_id}/calendar"
            headers = self._get_headers()

            params = {}
            if start_date:
                params["startDate"] = start_date.isoformat()
            if end_date:
                params["endDate"] = end_date.isoformat()

            response = await self.client.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                items = data.get("result", {}).get("calendarDays", [])

                for item in items:
                    calendar = self._transform_calendar(item, property_id)
                    calendars.append(calendar)

            return calendars
        except Exception as e:
            print(f"Error fetching calendar from Hostaway: {e}")
            return []

    async def get_messages(
        self,
        property_id: str | None = None,
        unread_only: bool = False,
    ) -> list[Message]:
        """
        Fetch messages from Hostaway

        Args:
            property_id: Optional property filter
            unread_only: Only unread messages

        Returns:
            List of Message objects
        """
        try:
            messages = []
            url = f"{self.BASE_URL}/v1/messages"
            headers = self._get_headers()

            params = {"limit": 100, "offset": 0}
            if unread_only:
                params["unread"] = 1

            offset = 0
            while True:
                params["offset"] = offset
                response = await self.client.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("result", {}).get("messages", [])

                if not items:
                    break

                for item in items:
                    message = self._transform_message(item)
                    messages.append(message)

                offset += 100
                if len(items) < 100:
                    break

            return messages
        except Exception as e:
            print(f"Error fetching messages from Hostaway: {e}")
            return []

    async def send_message(
        self,
        reservation_id: str,
        subject: str,
        body: str,
    ) -> bool:
        """
        Send message to guest through Hostaway

        Args:
            reservation_id: Hostaway reservation ID
            subject: Message subject
            body: Message body

        Returns:
            True if successful
        """
        try:
            url = f"{self.BASE_URL}/v1/messages"
            headers = self._get_headers()

            payload = {
                "reservationId": reservation_id,
                "subject": subject,
                "body": body,
            }

            response = await self.client.post(url, headers=headers, json=payload)
            return response.status_code == 201
        except Exception as e:
            print(f"Error sending message via Hostaway: {e}")
            return False

    async def get_reviews(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
    ) -> list[Review]:
        """
        Fetch reviews from Hostaway

        Args:
            property_id: Optional property filter
            start_date: Only reviews after this date

        Returns:
            List of Review objects
        """
        try:
            reviews = []
            url = f"{self.BASE_URL}/v1/reviews"
            headers = self._get_headers()

            params = {"limit": 100, "offset": 0}
            if property_id:
                params["propertyId"] = property_id

            offset = 0
            while True:
                params["offset"] = offset
                response = await self.client.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    break

                data = response.json()
                items = data.get("result", {}).get("reviews", [])

                if not items:
                    break

                for item in items:
                    review = self._transform_review(item)
                    if start_date is None or review.created_at.date() >= start_date:
                        reviews.append(review)

                offset += 100
                if len(items) < 100:
                    break

            return reviews
        except Exception as e:
            print(f"Error fetching reviews from Hostaway: {e}")
            return []

    async def update_calendar(self, calendar_events: list[Calendar]) -> bool:
        """
        Update calendar in Hostaway

        Args:
            calendar_events: List of Calendar objects to update

        Returns:
            True if successful
        """
        try:
            url = f"{self.BASE_URL}/v1/properties/calendar"
            headers = self._get_headers()

            # Batch update calendar
            payload = {
                "calendarDays": [
                    {
                        "date": event.date.isoformat(),
                        "status": event.status,
                        "minimumStay": event.min_nights,
                        "price": str(event.price) if event.price else None,
                    }
                    for event in calendar_events
                ]
            }

            response = await self.client.post(url, headers=headers, json=payload)
            return response.status_code in (200, 201)
        except Exception as e:
            print(f"Error updating calendar in Hostaway: {e}")
            return False

    async def update_pricing(
        self,
        property_id: str,
        nightly_price: float | None = None,
        calendar_prices: dict[date, float] | None = None,
    ) -> bool:
        """
        Update pricing in Hostaway

        Args:
            property_id: Hostaway property ID
            nightly_price: Base nightly price
            calendar_prices: Dict of date-specific prices

        Returns:
            True if successful
        """
        try:
            url = f"{self.BASE_URL}/v1/properties/{property_id}/pricing"
            headers = self._get_headers()

            payload = {}
            if nightly_price:
                payload["baseNightlyPrice"] = nightly_price

            if calendar_prices:
                payload["dates"] = [
                    {
                        "date": date_obj.isoformat(),
                        "price": price,
                    }
                    for date_obj, price in calendar_prices.items()
                ]

            response = await self.client.post(url, headers=headers, json=payload)
            return response.status_code in (200, 201)
        except Exception as e:
            print(f"Error updating pricing in Hostaway: {e}")
            return False

    def get_provider_name(self) -> str:
        """Get provider name"""
        return "Hostaway"

    def get_webhook_events(self) -> list[str]:
        """Get supported webhook events"""
        return [
            "reservation.new",
            "reservation.confirmed",
            "reservation.updated",
            "reservation.cancelled",
            "message.new",
            "review.new",
            "calendar.updated",
        ]

    # Helper methods for data transformation

    def _get_headers(self) -> dict[str, str]:
        """Build request headers"""
        return {
            "Authorization": f"Bearer {self.access_token or self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "PMS-Hub/1.0",
        }

    def _transform_property(self, data: dict[str, Any]) -> Property:
        """Transform Hostaway property to canonical model"""
        return Property(
            provider_id=str(data.get("id")),
            provider="hostaway",
            external_id=data.get("externalId", ""),
            name=data.get("title", ""),
            description=data.get("description"),
            property_type=data.get("propertyType", "vacation_rental"),
            address=data.get("address1", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            zip_code=data.get("zipCode"),
            country=data.get("country", "USA"),
            latitude=float(data.get("latitude", 0)) if data.get("latitude") else None,
            longitude=float(data.get("longitude", 0)) if data.get("longitude") else None,
            bedrooms=int(data.get("bedrooms", 1)),
            bathrooms=float(data.get("bathrooms", 1.0)),
            max_guests=int(data.get("maximumOccupancy", 1)),
            square_feet=data.get("squareMeters"),
            base_price=Decimal(str(data.get("basePrice", 0))),
            currency=data.get("currency", "USD"),
            synced_at=datetime.now(timezone.utc),
        )

    def _transform_reservation(self, data: dict[str, Any]) -> Reservation:
        """Transform Hostaway reservation to canonical model"""
        # Map Hostaway status to canonical status
        status_map = {
            "new": ReservationStatus.PENDING,
            "confirmed": ReservationStatus.CONFIRMED,
            "checked_in": ReservationStatus.CHECKED_IN,
            "checked_out": ReservationStatus.CHECKED_OUT,
            "cancelled": ReservationStatus.CANCELLED,
        }

        check_in = parse_iso_date(data.get("checkinDate"))
        check_out = parse_iso_date(data.get("checkoutDate"))
        nights = (check_out - check_in).days

        return Reservation(
            provider_id=str(data.get("id")),
            provider="hostaway",
            property_provider_id=str(data.get("propertyId", "")),
            confirmation_code=data.get("confirmationCode", ""),
            check_in_date=check_in,
            check_out_date=check_out,
            nights=nights,
            guests_count=int(data.get("numberOfGuests", 1)),
            base_price=Decimal(str(data.get("basePrice", 0))),
            discount=Decimal(str(data.get("discount", 0))),
            service_fee=Decimal(str(data.get("serviceFee", 0))),
            cleaning_fee=Decimal(str(data.get("cleaningFee", 0))),
            taxes=Decimal(str(data.get("taxes", 0))),
            total_price=Decimal(str(data.get("totalPrice", 0))),
            currency=data.get("currency", "USD"),
            status=status_map.get(data.get("status", "confirmed"), ReservationStatus.CONFIRMED),
            payment_status=PaymentStatus.PAID if data.get("isPaid") else PaymentStatus.PENDING,
            guest_name=f"{data.get('guestFirstName', '')} {data.get('guestLastName', '')}".strip(),
            guest_email=data.get("guestEmail", ""),
            guest_phone=data.get("guestPhone"),
            special_requests=data.get("specialRequests"),
            source="pms",
            synced_at=datetime.now(timezone.utc),
        )

    def _transform_message(self, data: dict[str, Any]) -> Message:
        """Transform Hostaway message to canonical model"""
        type_map = {
            "inquiry": MessageType.INQUIRY,
            "booking": MessageType.BOOKING,
            "pre_arrival": MessageType.PRE_ARRIVAL,
            "during_stay": MessageType.DURING_STAY,
            "post_checkout": MessageType.POST_CHECKOUT,
            "issue": MessageType.ISSUE,
        }

        return Message(
            provider_id=str(data.get("id")),
            provider="hostaway",
            guest_provider_id=str(data.get("guestId", "")),
            reservation_provider_id=str(data.get("reservationId")) if data.get("reservationId") else None,
            sender="host" if data.get("isHost") else "guest",
            message_type=type_map.get(data.get("messageType", "inquiry"), MessageType.INQUIRY),
            subject=data.get("subject"),
            body=data.get("body", ""),
            is_read=bool(data.get("isRead")),
            requires_response=not bool(data.get("isHost")),
            created_at=parse_iso_datetime(data.get("createdAt")),
            synced_at=datetime.now(timezone.utc),
        )

    def _transform_review(self, data: dict[str, Any]) -> Review:
        """Transform Hostaway review to canonical model"""
        return Review(
            provider_id=str(data.get("id")),
            provider="hostaway",
            reservation_provider_id=str(data.get("reservationId", "")),
            guest_provider_id=str(data.get("guestId", "")),
            rating=float(data.get("rating", 5.0)),
            title=data.get("title"),
            comment=data.get("comment", ""),
            categories={
                "cleanliness": float(data.get("cleanliness", 5.0)),
                "communication": float(data.get("communication", 5.0)),
                "location": float(data.get("location", 5.0)),
                "value": float(data.get("value", 5.0)),
            },
            created_at=parse_iso_datetime(data.get("createdAt")),
            synced_at=datetime.now(timezone.utc),
        )

    def _transform_calendar(self, data: dict[str, Any], property_id: str) -> Calendar:
        """Transform Hostaway calendar to canonical model"""
        return Calendar(
            provider_id=str(data.get("id", "")),
            provider="hostaway",
            property_provider_id=property_id,
            date=parse_iso_date(data.get("date")),
            status=data.get("status", "available"),
            price=Decimal(str(data.get("price"))) if data.get("price") else None,
            blocked_reason=data.get("blockedReason"),
            min_nights=int(data.get("minimumStay", 1)),
            synced_at=datetime.now(timezone.utc),
        )

    async def __aenter__(self):
        """Context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.client.aclose()
