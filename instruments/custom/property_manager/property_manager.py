"""
Property Manager - Main Interface
Full rental property management including tenants, leases, maintenance, and financials
"""

from datetime import date, timedelta
from typing import Any

from .property_db import PropertyDatabase


class PropertyManager:
    """Main interface for property management"""

    def __init__(self, data_dir: str | None = None):
        self.db = PropertyDatabase(data_dir)

    # Property management
    def add_property(
        self, name: str, property_type: str, address: str, city: str, state: str, **kwargs
    ) -> dict[str, Any]:
        """Add a new property"""
        property_id = self.db.add_property(
            name=name, property_type=property_type, address=address, city=city, state=state, **kwargs
        )
        return self.get_property(property_id)

    def get_property(self, property_id: int) -> dict[str, Any] | None:
        """Get property with all related information"""
        prop = self.db.get_property(property_id)
        if not prop:
            return None

        prop = dict(prop)
        prop["units"] = self.db.get_units(property_id)
        prop["mortgage"] = self.db.get_mortgage(property_id)
        prop["insurance"] = self.db.get_insurance(property_id)
        prop["active_leases"] = self.db.get_active_leases(property_id)
        prop["open_maintenance"] = self.db.get_maintenance_requests(property_id, status="open")

        return prop

    def list_properties(self, **filters) -> list[dict]:
        """List all properties with summary info"""
        properties = self.db.list_properties(status=filters.get("status"), property_type=filters.get("property_type"))

        for prop in properties:
            units = self.db.get_units(prop["id"])
            leases = self.db.get_active_leases(prop["id"])

            prop["unit_count"] = len(units)
            prop["occupied_units"] = len([u for u in units if u["status"] == "occupied"])
            prop["active_lease_count"] = len(leases)
            prop["monthly_rent_total"] = sum(l["rent_amount"] for l in leases)

        return properties

    def update_property(self, property_id: int, **kwargs) -> int:
        """Update property information"""
        return self.db.update_property(property_id, **kwargs)

    # Unit management (for multi-unit properties)
    def add_units(self, property_id: int, units: list[dict]) -> list[int]:
        """Add multiple units to a property"""
        unit_ids = []
        for unit in units:
            unit_id = self.db.add_unit(
                property_id=property_id,
                unit_number=unit["unit_number"],
                **{k: v for k, v in unit.items() if k != "unit_number"},
            )
            unit_ids.append(unit_id)
        return unit_ids

    def generate_motel_units(
        self, property_id: int, count: int, base_rent: float, unit_type: str = "room"
    ) -> list[int]:
        """Generate numbered units for a motel"""
        units = []
        for i in range(1, count + 1):
            units.append(
                {
                    "unit_number": str(i).zfill(2),
                    "unit_type": unit_type,
                    "rent_amount": base_rent,
                    "bedrooms": 1,
                    "bathrooms": 1,
                }
            )
        return self.add_units(property_id, units)

    # Tenant management
    def add_tenant(self, first_name: str, last_name: str, **kwargs) -> dict:
        """Add a new tenant"""
        tenant_id = self.db.add_tenant(first_name, last_name, **kwargs)
        return self.db.get_tenant(tenant_id)

    def search_tenants(self, query: str) -> list[dict]:
        """Search for tenants"""
        return self.db.search_tenants(query)

    def get_tenant_history(self, tenant_id: int) -> dict[str, Any]:
        """Get tenant with lease and payment history"""
        tenant = self.db.get_tenant(tenant_id)
        if not tenant:
            return None

        leases = self.db.fetch_all(
            """
            SELECT l.*, p.name as property_name, u.unit_number
            FROM leases l
            JOIN properties p ON l.property_id = p.id
            LEFT JOIN units u ON l.unit_id = u.id
            WHERE l.tenant_id = ?
            ORDER BY l.start_date DESC
        """,
            (tenant_id,),
        )

        # Get payment history for all leases
        total_paid = 0
        for lease in leases:
            payments = self.db.get_payments(lease["id"])
            lease["payments"] = payments
            total_paid += sum(p["amount"] for p in payments if p["status"] == "paid")

        tenant["leases"] = leases
        tenant["total_paid"] = total_paid

        return tenant

    # Lease management
    def create_lease(self, property_id: int, tenant_id: int, start_date: str, rent_amount: float, **kwargs) -> dict:
        """Create a new lease"""
        # Update unit status if applicable
        unit_id = kwargs.get("unit_id")
        if unit_id:
            self.db.update_unit(unit_id, status="occupied")

        lease_id = self.db.create_lease(
            property_id=property_id, tenant_id=tenant_id, start_date=start_date, rent_amount=rent_amount, **kwargs
        )
        return self.db.get_lease(lease_id)

    def renew_lease(self, lease_id: int, new_end_date: str, new_rent: float | None = None) -> dict:
        """Renew an existing lease"""
        lease = self.db.get_lease(lease_id)
        if not lease:
            raise ValueError(f"Lease not found: {lease_id}")

        updates = {"end_date": new_end_date, "status": "active"}
        if new_rent:
            updates["rent_amount"] = new_rent

        self.db.update_lease(lease_id, **updates)
        return self.db.get_lease(lease_id)

    def terminate_lease(self, lease_id: int, reason: str | None = None) -> int:
        """Terminate a lease"""
        lease = self.db.get_lease(lease_id)
        if lease and lease["unit_id"]:
            self.db.update_unit(lease["unit_id"], status="available")

        return self.db.update_lease(
            lease_id, status="terminated", terms=f"Terminated: {reason}" if reason else "Terminated"
        )

    def get_expiring_leases(self, days: int = 30) -> list[dict]:
        """Get leases expiring within specified days"""
        future_date = (date.today() + timedelta(days=days)).isoformat()
        today = date.today().isoformat()

        return self.db.fetch_all(
            """
            SELECT l.*, p.name as property_name,
                   t.first_name || ' ' || t.last_name as tenant_name,
                   u.unit_number
            FROM leases l
            JOIN properties p ON l.property_id = p.id
            JOIN tenants t ON l.tenant_id = t.id
            LEFT JOIN units u ON l.unit_id = u.id
            WHERE l.status = 'active'
            AND l.end_date IS NOT NULL
            AND l.end_date BETWEEN ? AND ?
            ORDER BY l.end_date
        """,
            (today, future_date),
        )

    # Rent collection
    def record_rent_payment(self, lease_id: int, amount: float, payment_date: str | None = None, **kwargs) -> dict:
        """Record a rent payment"""
        if not payment_date:
            payment_date = date.today().isoformat()

        due_date = kwargs.get("due_date", payment_date)

        payment_id = self.db.record_payment(
            lease_id=lease_id, amount=amount, payment_date=payment_date, due_date=due_date, **kwargs
        )

        return self.db.fetch_one("SELECT * FROM rent_payments WHERE id = ?", (payment_id,))

    def get_rent_roll(self, month: str | None = None) -> list[dict]:
        """Get rent roll - all expected and received rent"""
        if not month:
            month = date.today().strftime("%Y-%m")

        return self.db.fetch_all(
            """
            SELECT l.id as lease_id, l.rent_amount as expected,
                   p.name as property_name, u.unit_number,
                   t.first_name || ' ' || t.last_name as tenant_name,
                   COALESCE(SUM(CASE WHEN rp.status = 'paid' THEN rp.amount ELSE 0 END), 0) as paid,
                   l.rent_amount - COALESCE(SUM(CASE WHEN rp.status = 'paid' THEN rp.amount ELSE 0 END), 0) as balance
            FROM leases l
            JOIN properties p ON l.property_id = p.id
            JOIN tenants t ON l.tenant_id = t.id
            LEFT JOIN units u ON l.unit_id = u.id
            LEFT JOIN rent_payments rp ON l.id = rp.lease_id
                AND strftime('%Y-%m', rp.due_date) = ?
            WHERE l.status = 'active'
            GROUP BY l.id
            ORDER BY p.name, u.unit_number
        """,
            (month,),
        )

    def get_overdue_rent(self) -> list[dict]:
        """Get all overdue rent payments"""
        return self.db.get_overdue_payments()

    # Expense tracking
    def record_expense(self, property_id: int, category: str, description: str, amount: float, **kwargs) -> dict:
        """Record a property expense"""
        expense_date = kwargs.get("expense_date", date.today().isoformat())

        expense_id = self.db.add_expense(
            property_id=property_id,
            category=category,
            description=description,
            amount=amount,
            expense_date=expense_date,
            **kwargs,
        )

        return self.db.fetch_one("SELECT * FROM expenses WHERE id = ?", (expense_id,))

    def get_expense_report(
        self, property_id: int, start_date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Get expense report for a property"""
        expenses = self.db.get_expenses(property_id, start_date, end_date)

        by_category = {}
        for exp in expenses:
            cat = exp["category"]
            if cat not in by_category:
                by_category[cat] = {"items": [], "total": 0}
            by_category[cat]["items"].append(exp)
            by_category[cat]["total"] += exp["amount"]

        return {
            "property_id": property_id,
            "start_date": start_date,
            "end_date": end_date,
            "by_category": by_category,
            "total": sum(exp["amount"] for exp in expenses),
            "expense_count": len(expenses),
        }

    # Maintenance management
    def create_maintenance_request(self, property_id: int, category: str, title: str, **kwargs) -> dict:
        """Create a maintenance request"""
        request_id = self.db.create_maintenance_request(
            property_id=property_id, category=category, title=title, **kwargs
        )

        return self.db.fetch_one(
            """
            SELECT m.*, p.name as property_name, u.unit_number
            FROM maintenance_requests m
            JOIN properties p ON m.property_id = p.id
            LEFT JOIN units u ON m.unit_id = u.id
            WHERE m.id = ?
        """,
            (request_id,),
        )

    def update_maintenance_status(self, request_id: int, status: str, **kwargs) -> int:
        """Update maintenance request status"""
        return self.db.update_maintenance(request_id, status=status, **kwargs)

    def complete_maintenance(self, request_id: int, actual_cost: float, notes: str | None = None) -> dict:
        """Mark maintenance as complete and record cost"""
        self.db.update_maintenance(request_id, status="completed", actual_cost=actual_cost, notes=notes)

        # Also record as expense
        request = self.db.fetch_one("SELECT * FROM maintenance_requests WHERE id = ?", (request_id,))

        if request:
            self.db.add_expense(
                property_id=request["property_id"],
                unit_id=request["unit_id"],
                category="maintenance",
                description=f"Maintenance: {request['title']}",
                amount=actual_cost,
                expense_date=date.today().isoformat(),
                notes=f"Request #{request_id}",
            )

        return request

    def get_maintenance_schedule(self) -> list[dict]:
        """Get upcoming scheduled maintenance"""
        return self.db.fetch_all("""
            SELECT m.*, p.name as property_name, u.unit_number
            FROM maintenance_requests m
            JOIN properties p ON m.property_id = p.id
            LEFT JOIN units u ON m.unit_id = u.id
            WHERE m.status = 'scheduled' AND m.scheduled_date >= date('now')
            ORDER BY m.scheduled_date
        """)

    # Financial reporting
    def get_property_financials(self, property_id: int, year: int | None = None) -> dict:
        """Get comprehensive financial report for a property"""
        return self.db.get_property_financials(property_id, year)

    def get_portfolio_financials(self, year: int | None = None) -> dict[str, Any]:
        """Get financial summary across all properties"""
        properties = self.db.list_properties()

        total_income = 0
        total_expenses = 0
        total_net = 0
        property_details = []

        for prop in properties:
            financials = self.db.get_property_financials(prop["id"], year)
            total_income += financials["income"]["total_rent"]
            total_expenses += financials["expenses"]["total"]
            total_net += financials["net_income"]

            property_details.append(
                {
                    "id": prop["id"],
                    "name": prop["name"],
                    "income": financials["income"]["total_rent"],
                    "expenses": financials["expenses"]["total"],
                    "net_income": financials["net_income"],
                    "roi_percent": financials["roi_percent"],
                }
            )

        return {
            "year": year,
            "total_income": total_income,
            "total_expenses": total_expenses,
            "total_net_income": total_net,
            "properties": property_details,
        }

    def get_cash_flow_projection(self, property_id: int, months: int = 12) -> list[dict]:
        """Project cash flow for upcoming months"""
        prop = self.get_property(property_id)
        if not prop:
            return []

        projections = []
        current_date = date.today()

        # Get monthly recurring income
        monthly_rent = sum(l["rent_amount"] for l in prop.get("active_leases", []))

        # Get monthly recurring expenses
        mortgage = prop.get("mortgage")
        monthly_mortgage = mortgage["monthly_payment"] if mortgage else 0

        # Get average monthly expenses (from past year)
        avg_expenses = self.db.fetch_one(
            """
            SELECT AVG(monthly_total) as avg
            FROM (
                SELECT strftime('%Y-%m', expense_date) as month, SUM(amount) as monthly_total
                FROM expenses WHERE property_id = ?
                GROUP BY month
            )
        """,
            (property_id,),
        )

        avg_monthly_expenses = avg_expenses["avg"] if avg_expenses and avg_expenses["avg"] else 0

        for i in range(months):
            month_date = current_date + timedelta(days=30 * i)
            month_str = month_date.strftime("%Y-%m")

            projections.append(
                {
                    "month": month_str,
                    "expected_income": monthly_rent,
                    "expected_expenses": avg_monthly_expenses + monthly_mortgage,
                    "projected_net": monthly_rent - avg_monthly_expenses - monthly_mortgage,
                }
            )

        return projections

    # Portfolio overview
    def get_portfolio_summary(self) -> dict[str, Any]:
        """Get complete portfolio summary"""
        return self.db.get_portfolio_summary()

    def get_dashboard(self) -> dict[str, Any]:
        """Get dashboard data for all properties"""
        summary = self.get_portfolio_summary()

        # Add additional dashboard metrics
        expiring_leases = self.get_expiring_leases(30)
        overdue_rent = self.get_overdue_rent()
        open_maintenance = self.db.get_maintenance_requests(status="open")
        emergency_maintenance = [m for m in open_maintenance if m["priority"] == "emergency"]

        return {
            "summary": summary,
            "alerts": {
                "expiring_leases": len(expiring_leases),
                "overdue_rent": len(overdue_rent),
                "overdue_amount": sum(p["amount"] for p in overdue_rent),
                "open_maintenance": len(open_maintenance),
                "emergency_maintenance": len(emergency_maintenance),
            },
            "expiring_leases": expiring_leases[:5],
            "overdue_rent": overdue_rent[:5],
            "emergency_maintenance": emergency_maintenance,
        }

    def close(self):
        """Close database connection"""
        self.db.close()


# Seed data helper for initial setup
def seed_initial_properties(manager: PropertyManager):
    """Seed initial property data based on user's properties"""

    # West Bethel Motel
    motel = manager.add_property(
        name="West Bethel Motel",
        property_type="motel",
        address="Main Street",  # Update with actual address
        city="Bethel",
        state="ME",
        notes="Multi-unit motel property",
    )

    # Generate motel rooms (adjust count as needed)
    manager.generate_motel_units(
        property_id=motel["id"],
        count=10,  # Adjust to actual room count
        base_rent=89.00,  # Nightly rate - adjust as needed
        unit_type="room",
    )

    # Three houses (placeholder - update with actual details)
    house_defaults = [
        {"name": "House 1", "city": "TBD", "state": "TBD"},
        {"name": "House 2", "city": "TBD", "state": "TBD"},
        {"name": "House 3", "city": "TBD", "state": "TBD"},
    ]

    for house in house_defaults:
        manager.add_property(
            name=house["name"],
            property_type="house",
            address="TBD",
            city=house["city"],
            state=house["state"],
            notes="Update with actual property details",
        )

    return {
        "motel_id": motel["id"],
        "message": "Initial properties created. Please update House details with actual addresses.",
    }
