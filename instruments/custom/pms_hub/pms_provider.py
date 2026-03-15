"""
Base PMS Provider Abstract Class
All provider adapters inherit from this class and implement the standard interface
"""

from abc import ABC, abstractmethod
from datetime import date
from enum import Enum
from typing import Any

from .canonical_models import (
    Calendar,
    Message,
    Property,
    Reservation,
    Review,
)


class ProviderType(str, Enum):
    """Supported PMS provider types"""

    HOSTAWAY = "hostaway"
    LODGIFY = "lodgify"
    HOSTIFY = "hostify"
    ICAL = "ical"
    VRBO = "vrbo"  # Future
    BOOKING_COM = "booking_com"  # Future


class PMSProvider(ABC):
    """
    Abstract base class for all PMS provider adapters
    Defines the standard interface that all providers must implement
    """

    def __init__(self, provider_type: ProviderType, config: dict[str, Any]):
        """
        Initialize provider

        Args:
            provider_type: Type of PMS provider
            config: Provider-specific configuration (API keys, credentials, etc.)
        """
        self.provider_type = provider_type
        self.config = config
        self._authenticated = False

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the PMS provider

        Returns:
            True if authentication successful
        """
        pass

    @abstractmethod
    async def get_properties(self) -> list[Property]:
        """
        Fetch all properties/listings from provider

        Returns:
            List of canonical Property objects
        """
        pass

    @abstractmethod
    async def get_property(self, provider_id: str) -> Property | None:
        """
        Fetch single property by provider ID

        Args:
            provider_id: Provider-specific property ID

        Returns:
            Canonical Property object or None if not found
        """
        pass

    @abstractmethod
    async def get_reservations(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Reservation]:
        """
        Fetch reservations for a date range

        Args:
            property_id: Optional filter by property
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of canonical Reservation objects
        """
        pass

    @abstractmethod
    async def get_reservation(self, provider_id: str) -> Reservation | None:
        """
        Fetch single reservation by provider ID

        Args:
            provider_id: Provider-specific reservation ID

        Returns:
            Canonical Reservation object or None
        """
        pass

    @abstractmethod
    async def get_calendar(
        self,
        property_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Calendar]:
        """
        Fetch calendar/availability for property

        Args:
            property_id: Provider property ID
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            List of Calendar objects
        """
        pass

    @abstractmethod
    async def get_messages(
        self,
        property_id: str | None = None,
        unread_only: bool = False,
    ) -> list[Message]:
        """
        Fetch messages (guest communications)

        Args:
            property_id: Optional filter by property
            unread_only: Only fetch unread messages

        Returns:
            List of Message objects
        """
        pass

    @abstractmethod
    async def send_message(
        self,
        reservation_id: str,
        subject: str,
        body: str,
    ) -> bool:
        """
        Send message to guest

        Args:
            reservation_id: Provider reservation ID
            subject: Message subject
            body: Message body

        Returns:
            True if message sent successfully
        """
        pass

    @abstractmethod
    async def get_reviews(
        self,
        property_id: str | None = None,
        start_date: date | None = None,
    ) -> list[Review]:
        """
        Fetch reviews/ratings

        Args:
            property_id: Optional filter by property
            start_date: Only reviews after this date

        Returns:
            List of Review objects
        """
        pass

    @abstractmethod
    async def update_calendar(self, calendar_events: list[Calendar]) -> bool:
        """
        Update calendar availability

        Args:
            calendar_events: List of Calendar objects to update

        Returns:
            True if update successful
        """
        pass

    @abstractmethod
    async def update_pricing(
        self,
        property_id: str,
        nightly_price: float | None = None,
        calendar_prices: dict[date, float] | None = None,
    ) -> bool:
        """
        Update property pricing

        Args:
            property_id: Provider property ID
            nightly_price: Base nightly price
            calendar_prices: Dict of date-specific prices

        Returns:
            True if update successful
        """
        pass

    def is_authenticated(self) -> bool:
        """Check if provider is authenticated"""
        return self._authenticated

    async def verify_webhook(self, payload: dict[str, Any], signature: str) -> bool:
        """
        Verify webhook signature from provider

        Args:
            payload: Webhook payload
            signature: Signature to verify

        Returns:
            True if signature is valid
        """
        # Default implementation - override in provider if needed
        return True

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get human-readable provider name"""
        pass

    @abstractmethod
    def get_webhook_events(self) -> list[str]:
        """
        Get list of webhook event types this provider supports

        Returns:
            List of webhook event type strings
        """
        pass
