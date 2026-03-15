"""
Canonical Data Models (CDM) for PMS Hub
Unified data representations that abstract provider-specific formats
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class ReservationStatus(str, Enum):
    """Reservation status states"""

    INQUIRY = "inquiry"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    DECLINED = "declined"


class PaymentStatus(str, Enum):
    """Payment status states"""

    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    REFUNDED = "refunded"


class MessageType(str, Enum):
    """Message types"""

    INQUIRY = "inquiry"
    BOOKING = "booking"
    PRE_ARRIVAL = "pre_arrival"
    DURING_STAY = "during_stay"
    POST_CHECKOUT = "post_checkout"
    ISSUE = "issue"
    SYSTEM = "system"


@dataclass
class Property:
    """Canonical property/listing representation"""

    provider_id: str  # Provider-specific ID (e.g., Hostaway listing_id)
    provider: str  # Provider name (hostaway, lodgify, etc.)
    external_id: str  # AirBnb listing ID or equivalent

    name: str
    address: str
    city: str
    state: str

    description: str | None = None
    property_type: str = "vacation_rental"  # vacation_rental, house, apartment, etc.
    zip_code: str | None = None
    country: str = "USA"
    latitude: float | None = None
    longitude: float | None = None

    bedrooms: int = 1
    bathrooms: float = 1.0
    max_guests: int = 1
    square_feet: int | None = None

    amenities: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)

    base_price: Decimal = Decimal("0")
    currency: str = "USD"

    # Sync metadata
    synced_at: datetime = field(default_factory=datetime.utcnow)
    last_modified: datetime = field(default_factory=datetime.utcnow)
    sync_hash: str | None = None  # For detecting changes


@dataclass
class Unit:
    """Unit within a property (for multi-unit properties)"""

    provider_id: str
    property_provider_id: str  # Parent property provider ID
    unit_number: str

    unit_type: str = "room"
    bedrooms: int = 1
    bathrooms: float = 1.0
    max_guests: int = 1

    base_price: Decimal = Decimal("0")
    currency: str = "USD"

    synced_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Guest:
    """Canonical guest representation"""

    provider_id: str  # Provider-specific guest ID
    provider: str

    first_name: str
    last_name: str
    email: str
    phone: str | None = None

    # Guest verification
    identity_verified: bool = False
    superhost_reviewed: bool = False
    review_count: int = 0
    review_rating: float | None = None  # 4.5 out of 5

    # Communication preferences
    preferred_contact_method: str = "email"  # email, phone, message

    metadata: dict[str, Any] = field(default_factory=dict)

    synced_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Reservation:
    """Canonical reservation representation"""

    provider_id: str  # e.g., Hostaway reservation ID
    provider: str  # hostaway, lodgify, etc.
    property_provider_id: str  # Provider's property/listing ID
    unit_provider_id: str | None = None  # For multi-unit properties
    guest_provider_id: str = ""

    # Booking details
    confirmation_code: str = ""
    check_in_date: date = field(default_factory=date.today)
    check_out_date: date = field(default_factory=date.today)
    nights: int = 1
    guests_count: int = 1

    # Pricing
    base_price: Decimal = Decimal("0")
    discount: Decimal = Decimal("0")
    service_fee: Decimal = Decimal("0")
    cleaning_fee: Decimal = Decimal("0")
    taxes: Decimal = Decimal("0")
    total_price: Decimal = Decimal("0")
    currency: str = "USD"

    # Status
    status: ReservationStatus = ReservationStatus.CONFIRMED
    payment_status: PaymentStatus = PaymentStatus.PENDING

    # Guest info
    guest_name: str = ""
    guest_email: str = ""
    guest_phone: str | None = None
    special_requests: str | None = None

    # Sync metadata
    source: str = "pms"  # pms, direct_booking, etc.
    synced_at: datetime = field(default_factory=datetime.utcnow)
    last_modified: datetime = field(default_factory=datetime.utcnow)

    # Internal references (populated during sync)
    property_manager_id: int | None = None  # Maps to property_manager property ID
    unit_manager_id: int | None = None  # Maps to property_manager unit ID
    tenant_manager_id: int | None = None  # Maps to property_manager tenant ID
    lease_manager_id: int | None = None  # Maps to property_manager lease ID


@dataclass
class Message:
    """Canonical guest message representation"""

    provider_id: str
    provider: str
    guest_provider_id: str
    reservation_provider_id: str | None = None

    sender: str = "guest"  # guest, host, system
    message_type: MessageType = MessageType.INQUIRY
    subject: str | None = None
    body: str = ""

    is_read: bool = False
    requires_response: bool = True

    created_at: datetime = field(default_factory=datetime.utcnow)
    synced_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Review:
    """Canonical review representation"""

    provider_id: str
    provider: str
    reservation_provider_id: str
    guest_provider_id: str

    rating: float = 5.0  # 1-5 stars
    title: str | None = None
    comment: str = ""

    categories: dict[str, float] = field(default_factory=dict)  # cleanliness, communication, etc.

    created_at: datetime = field(default_factory=datetime.utcnow)
    synced_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PricingRule:
    """Pricing rule for dynamic pricing"""

    provider_id: str
    provider: str
    property_provider_id: str

    rule_name: str
    rule_type: str  # minimum_stay, seasonal, weekly_discount, etc.

    start_date: date | None = None
    end_date: date | None = None
    min_nights: int = 1

    price_modifier: Decimal = Decimal("0")  # Absolute price or percentage
    is_percentage: bool = False

    is_active: bool = True

    synced_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Calendar:
    """Calendar/Availability representation"""

    provider_id: str
    provider: str
    property_provider_id: str

    date: date
    unit_provider_id: str | None = None
    status: str = "available"  # available, booked, blocked, not_available
    price: Decimal | None = None

    blocked_reason: str | None = None  # cleaning, maintenance, owner_block, etc.
    min_nights: int = 1

    synced_at: datetime = field(default_factory=datetime.utcnow)
