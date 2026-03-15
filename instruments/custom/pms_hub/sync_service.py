"""
PMS ↔ PropertyManager Sync Service
Bi-directional synchronization between PMS data and property_manager
"""

import sys
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now

# Add imports path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from .canonical_models import PaymentStatus, Reservation, ReservationStatus
from .provider_registry import ProviderRegistry


class PMSSyncService:
    """
    Manages synchronization between PMS providers and property_manager
    Maps between canonical PMS models and property_manager database schema
    """

    def __init__(self):
        """Initialize sync service"""
        self.registry = ProviderRegistry()

        # Import property_manager tools
        try:
            from property_manager.property_db import PropertyDatabase
            from property_manager.property_manager import PropertyManager as PM

            self.pm = PM()
            self.pm_db = PropertyDatabase()
        except ImportError:
            print("Warning: PropertyManager not available for sync")
            self.pm = None
            self.pm_db = None

    async def sync_reservation_to_property_manager(self, reservation: Reservation) -> tuple[bool, int | None]:
        """
        Sync a PMS reservation to property_manager as a short-term lease

        Args:
            reservation: Canonical Reservation object

        Returns:
            Tuple of (success, lease_id)
        """
        if not self.pm:
            return False, None

        try:
            # Step 1: Ensure property exists in property_manager
            property_id = await self._sync_property(reservation.property_provider_id)
            if not property_id:
                print(f"Failed to sync property: {reservation.property_provider_id}")
                return False, None

            # Step 2: Ensure unit exists (if multi-unit property)
            unit_id = None
            if reservation.unit_provider_id:
                unit_id = await self._sync_unit(property_id, reservation.unit_provider_id)

            # Step 3: Create or update tenant from guest info
            tenant_id = await self._sync_guest_to_tenant(reservation)
            if not tenant_id:
                print("Failed to create/update tenant")
                return False, None

            # Step 4: Create or update lease
            lease_id = await self._sync_reservation_to_lease(property_id, unit_id, tenant_id, reservation)

            if lease_id:
                # Step 5: Record payment if applicable
                if reservation.payment_status == PaymentStatus.PAID:
                    await self._record_payment(lease_id, reservation)

                # Update reservation with manager IDs for reference
                reservation.property_manager_id = property_id
                reservation.unit_manager_id = unit_id
                reservation.tenant_manager_id = tenant_id
                reservation.lease_manager_id = lease_id

            return bool(lease_id), lease_id

        except Exception as e:
            print(f"Error syncing reservation: {e}")
            return False, None

    async def _sync_property(self, provider_property_id: str) -> int | None:
        """
        Sync PMS property to property_manager

        Args:
            provider_property_id: PMS provider property ID

        Returns:
            property_manager property_id or None
        """
        try:
            # Check if property already exists (by external ID)
            # In a real implementation, we'd check external_id mapping
            # For now, create new property

            # Get provider to fetch property details
            providers = self.registry.list_providers(enabled_only=True)
            if not providers:
                return None

            provider = await self.registry.get_provider_async(providers[0])
            if not provider:
                return None

            pms_property = await provider.get_property(provider_property_id)
            if not pms_property:
                return None

            # Add property to property_manager
            property_data = {
                "name": pms_property.name,
                "property_type": "motel",  # Assume vacation rental = motel type
                "address": pms_property.address,
                "city": pms_property.city,
                "state": pms_property.state,
                "zip_code": pms_property.zip_code,
                "country": pms_property.country,
                "bedrooms": pms_property.bedrooms,
                "bathrooms": pms_property.bathrooms,
                "square_feet": pms_property.square_feet,
            }

            # Use property_manager API to add property
            result = await self.pm.add_property(property_data)
            if result and result.get("status") == "success":
                return result.get("data", {}).get("id")

            return None
        except Exception as e:
            print(f"Error syncing property: {e}")
            return None

    async def _sync_unit(self, property_id: int, provider_unit_id: str) -> int | None:
        """
        Sync PMS unit to property_manager unit

        Args:
            property_id: property_manager property_id
            provider_unit_id: PMS unit ID

        Returns:
            property_manager unit_id or None
        """
        try:
            # Create unit in property_manager
            unit_data = {
                "unit_number": provider_unit_id,
                "unit_type": "room",
                "bedrooms": 1,
                "bathrooms": 1,
                "status": "available",
            }

            # Add unit to property
            result = await self.pm.add_units(property_id, unit_data)
            if result and result.get("status") == "success":
                units = result.get("data", [])
                if units:
                    return units[0].get("id")

            return None
        except Exception as e:
            print(f"Error syncing unit: {e}")
            return None

    async def _sync_guest_to_tenant(self, reservation: Reservation) -> int | None:
        """
        Sync PMS guest to property_manager tenant

        Args:
            reservation: Reservation with guest info

        Returns:
            property_manager tenant_id or None
        """
        try:
            # Parse guest name
            guest_name_parts = reservation.guest_name.split(" ", 1)
            first_name = guest_name_parts[0] if guest_name_parts else "Guest"
            last_name = guest_name_parts[1] if len(guest_name_parts) > 1 else ""

            tenant_data = {
                "first_name": first_name,
                "last_name": last_name,
                "email": reservation.guest_email,
                "phone": reservation.guest_phone,
                "notes": f"PMS Reservation: {reservation.confirmation_code}",
            }

            result = await self.pm.add_tenant(tenant_data)
            if result and result.get("status") == "success":
                return result.get("data", {}).get("id")

            return None
        except Exception as e:
            print(f"Error syncing guest to tenant: {e}")
            return None

    async def _sync_reservation_to_lease(
        self,
        property_id: int,
        unit_id: int | None,
        tenant_id: int,
        reservation: Reservation,
    ) -> int | None:
        """
        Sync PMS reservation to property_manager lease

        Args:
            property_id: property_manager property_id
            unit_id: Optional property_manager unit_id
            tenant_id: property_manager tenant_id
            reservation: Reservation to sync

        Returns:
            property_manager lease_id or None
        """
        try:
            lease_data = {
                "property_id": property_id,
                "unit_id": unit_id,
                "tenant_id": tenant_id,
                "lease_type": "nightly",  # Short-term rental
                "start_date": reservation.check_in_date.isoformat(),
                "end_date": reservation.check_out_date.isoformat(),
                "rent_amount": float(reservation.base_price),
                "rent_frequency": "nightly",
                "security_deposit": 0,
                "deposit_paid": 1,
                "status": self._map_reservation_status(reservation.status),
                "terms": f"PMS ID: {reservation.provider_id}",
            }

            result = await self.pm.create_lease(lease_data)
            if result and result.get("status") == "success":
                return result.get("data", {}).get("id")

            return None
        except Exception as e:
            print(f"Error syncing reservation to lease: {e}")
            return None

    async def _record_payment(self, lease_id: int, reservation: Reservation) -> bool:
        """
        Record payment in property_manager

        Args:
            lease_id: property_manager lease_id
            reservation: Reservation with payment info

        Returns:
            True if successful
        """
        try:
            payment_data = {
                "lease_id": lease_id,
                "amount": float(reservation.total_price),
                "payment_date": isoformat_z(utc_now()),
                "due_date": reservation.check_in_date.isoformat(),
                "payment_method": "online",
                "status": "paid",
                "notes": f"PMS Payment: {reservation.confirmation_code}",
            }

            result = await self.pm.record_payment(payment_data)
            return result and result.get("status") == "success"
        except Exception as e:
            print(f"Error recording payment: {e}")
            return False

    def _map_reservation_status(self, reservation_status: ReservationStatus) -> str:
        """
        Map PMS reservation status to property_manager lease status

        Args:
            reservation_status: ReservationStatus enum

        Returns:
            property_manager lease status string
        """
        status_map = {
            ReservationStatus.PENDING: "pending",
            ReservationStatus.CONFIRMED: "active",
            ReservationStatus.CHECKED_IN: "active",
            ReservationStatus.CHECKED_OUT: "expired",
            ReservationStatus.CANCELLED: "terminated",
            ReservationStatus.DECLINED: "terminated",
            ReservationStatus.INQUIRY: "pending",
        }

        return status_map.get(reservation_status, "active")

    async def sync_all_reservations(self, provider_id: str) -> tuple[int, int]:
        """
        Sync all reservations from a PMS provider

        Args:
            provider_id: Registry provider ID

        Returns:
            Tuple of (synced_count, error_count)
        """
        try:
            provider = await self.registry.get_provider_async(provider_id)
            if not provider:
                print(f"Provider not found: {provider_id}")
                return 0, 0

            # Fetch all reservations
            reservations = await provider.get_reservations()

            synced = 0
            errors = 0

            for reservation in reservations:
                success, _ = await self.sync_reservation_to_property_manager(reservation)
                if success:
                    synced += 1
                else:
                    errors += 1

            return synced, errors
        except Exception as e:
            print(f"Error syncing reservations: {e}")
            return 0, len([])

    async def get_sync_status(self) -> dict:
        """
        Get current sync status

        Returns:
            Dict with sync information
        """
        try:
            providers = self.registry.list_providers(enabled_only=True)
            status = {
                "providers": len(providers),
                "providers_enabled": providers,
                "last_sync": None,
                "sync_errors": 0,
            }

            return status
        except Exception as e:
            print(f"Error getting sync status: {e}")
            return {}
