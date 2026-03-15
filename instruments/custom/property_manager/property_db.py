"""
Property Manager Database Schema and Operations
SQLite backend for full rental property management
"""

import sys
from datetime import date
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python.helpers.db_manager import DatabaseManager, get_timestamp


class PropertyDatabase:
    """Database operations for Property Manager"""

    SCHEMA = """
    -- Properties table: Core property information
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        property_type TEXT NOT NULL,  -- house, motel, apartment, commercial
        address TEXT NOT NULL,
        city TEXT NOT NULL,
        state TEXT NOT NULL,
        zip_code TEXT,
        country TEXT DEFAULT 'USA',
        bedrooms INTEGER,
        bathrooms REAL,
        square_feet INTEGER,
        lot_size REAL,
        year_built INTEGER,
        purchase_date TEXT,
        purchase_price REAL,
        current_value REAL,
        status TEXT DEFAULT 'active',  -- active, vacant, under_renovation, for_sale, sold
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    -- Units table: For multi-unit properties (motels, apartments)
    CREATE TABLE IF NOT EXISTS units (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        unit_number TEXT NOT NULL,
        unit_type TEXT,  -- room, suite, apartment, studio
        bedrooms INTEGER DEFAULT 1,
        bathrooms REAL DEFAULT 1,
        square_feet INTEGER,
        rent_amount REAL,
        status TEXT DEFAULT 'available',  -- available, occupied, maintenance, reserved
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
        UNIQUE(property_id, unit_number)
    );

    -- Tenants table: Tenant information
    CREATE TABLE IF NOT EXISTS tenants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        emergency_contact_name TEXT,
        emergency_contact_phone TEXT,
        id_type TEXT,
        id_number TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    -- Leases table: Lease agreements
    CREATE TABLE IF NOT EXISTS leases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        unit_id INTEGER,  -- NULL for single-unit properties
        tenant_id INTEGER NOT NULL,
        lease_type TEXT DEFAULT 'long-term',  -- long-term, month-to-month, short-term, nightly
        start_date TEXT NOT NULL,
        end_date TEXT,
        rent_amount REAL NOT NULL,
        rent_frequency TEXT DEFAULT 'monthly',  -- nightly, weekly, monthly, yearly
        security_deposit REAL,
        deposit_paid INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',  -- pending, active, expired, terminated
        terms TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
        FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
    );

    -- Rent payments table
    CREATE TABLE IF NOT EXISTS rent_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lease_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        payment_method TEXT,  -- cash, check, transfer, card, online
        status TEXT DEFAULT 'paid',  -- pending, paid, partial, late, waived
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (lease_id) REFERENCES leases(id) ON DELETE CASCADE
    );

    -- Expenses table: Property expenses
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        unit_id INTEGER,
        category TEXT NOT NULL,  -- mortgage, insurance, tax, utilities, maintenance, repairs, supplies, management, advertising, legal, other
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        expense_date TEXT NOT NULL,
        vendor TEXT,
        receipt_path TEXT,
        recurring INTEGER DEFAULT 0,
        recurring_frequency TEXT,  -- monthly, quarterly, yearly
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
        FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL
    );

    -- Maintenance requests table
    CREATE TABLE IF NOT EXISTS maintenance_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        unit_id INTEGER,
        reported_by TEXT,
        category TEXT NOT NULL,  -- plumbing, electrical, hvac, appliance, structural, cosmetic, pest, safety, other
        priority TEXT DEFAULT 'normal',  -- low, normal, high, emergency
        title TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'open',  -- open, in_progress, scheduled, completed, cancelled
        assigned_to TEXT,
        estimated_cost REAL,
        actual_cost REAL,
        scheduled_date TEXT,
        completed_date TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
        FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL
    );

    -- Mortgage/Loan information
    CREATE TABLE IF NOT EXISTS mortgages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        lender TEXT NOT NULL,
        loan_amount REAL NOT NULL,
        interest_rate REAL NOT NULL,
        loan_term_years INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        monthly_payment REAL NOT NULL,
        escrow_amount REAL DEFAULT 0,
        remaining_balance REAL,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    -- Insurance policies
    CREATE TABLE IF NOT EXISTS insurance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        provider TEXT NOT NULL,
        policy_number TEXT,
        policy_type TEXT,  -- property, liability, flood, umbrella
        coverage_amount REAL,
        premium_amount REAL NOT NULL,
        premium_frequency TEXT DEFAULT 'yearly',  -- monthly, quarterly, yearly
        start_date TEXT NOT NULL,
        end_date TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
    );

    -- Documents table
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER,
        unit_id INTEGER,
        tenant_id INTEGER,
        lease_id INTEGER,
        doc_type TEXT NOT NULL,  -- lease, receipt, inspection, photo, insurance, tax, other
        title TEXT NOT NULL,
        file_path TEXT,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE,
        FOREIGN KEY (unit_id) REFERENCES units(id) ON DELETE SET NULL,
        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
        FOREIGN KEY (lease_id) REFERENCES leases(id) ON DELETE CASCADE
    );

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_properties_status ON properties(status);
    CREATE INDEX IF NOT EXISTS idx_properties_type ON properties(property_type);
    CREATE INDEX IF NOT EXISTS idx_units_status ON units(status);
    CREATE INDEX IF NOT EXISTS idx_leases_status ON leases(status);
    CREATE INDEX IF NOT EXISTS idx_maintenance_status ON maintenance_requests(status);
    CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);
    CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(expense_date);
    CREATE INDEX IF NOT EXISTS idx_rent_payments_date ON rent_payments(payment_date);
    """

    def __init__(self, data_dir: str | None = None):
        self.db = DatabaseManager("properties.db", data_dir)
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema"""
        with self.db.cursor() as cur:
            cur.executescript(self.SCHEMA)

    # Property operations
    def add_property(self, name: str, property_type: str, address: str, city: str, state: str, **kwargs) -> int:
        """Add a new property"""
        now = get_timestamp()
        data = {
            "name": name,
            "property_type": property_type,
            "address": address,
            "city": city,
            "state": state,
            "zip_code": kwargs.get("zip_code"),
            "country": kwargs.get("country", "USA"),
            "bedrooms": kwargs.get("bedrooms"),
            "bathrooms": kwargs.get("bathrooms"),
            "square_feet": kwargs.get("square_feet"),
            "lot_size": kwargs.get("lot_size"),
            "year_built": kwargs.get("year_built"),
            "purchase_date": kwargs.get("purchase_date"),
            "purchase_price": kwargs.get("purchase_price"),
            "current_value": kwargs.get("current_value"),
            "status": kwargs.get("status", "active"),
            "notes": kwargs.get("notes"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("properties", data)

    def get_property(self, property_id: int) -> dict | None:
        """Get property by ID"""
        return self.db.fetch_one("SELECT * FROM properties WHERE id = ?", (property_id,))

    def list_properties(self, status: str | None = None, property_type: str | None = None) -> list[dict]:
        """List properties with optional filtering"""
        sql = "SELECT * FROM properties WHERE 1=1"
        params = []

        if status:
            sql += " AND status = ?"
            params.append(status)
        if property_type:
            sql += " AND property_type = ?"
            params.append(property_type)

        sql += " ORDER BY name"
        return self.db.fetch_all(sql, tuple(params))

    def update_property(self, property_id: int, **kwargs) -> int:
        """Update property fields"""
        kwargs["updated_at"] = get_timestamp()
        return self.db.update("properties", kwargs, "id = ?", (property_id,))

    def delete_property(self, property_id: int) -> int:
        """Delete property and all related data"""
        return self.db.delete("properties", "id = ?", (property_id,))

    # Unit operations (for multi-unit properties like motels)
    def add_unit(self, property_id: int, unit_number: str, **kwargs) -> int:
        """Add a unit to a property"""
        now = get_timestamp()
        data = {
            "property_id": property_id,
            "unit_number": unit_number,
            "unit_type": kwargs.get("unit_type"),
            "bedrooms": kwargs.get("bedrooms", 1),
            "bathrooms": kwargs.get("bathrooms", 1),
            "square_feet": kwargs.get("square_feet"),
            "rent_amount": kwargs.get("rent_amount"),
            "status": kwargs.get("status", "available"),
            "notes": kwargs.get("notes"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("units", data)

    def get_units(self, property_id: int) -> list[dict]:
        """Get all units for a property"""
        return self.db.fetch_all("SELECT * FROM units WHERE property_id = ? ORDER BY unit_number", (property_id,))

    def update_unit(self, unit_id: int, **kwargs) -> int:
        """Update unit fields"""
        kwargs["updated_at"] = get_timestamp()
        return self.db.update("units", kwargs, "id = ?", (unit_id,))

    # Tenant operations
    def add_tenant(self, first_name: str, last_name: str, **kwargs) -> int:
        """Add a new tenant"""
        now = get_timestamp()
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": kwargs.get("email"),
            "phone": kwargs.get("phone"),
            "emergency_contact_name": kwargs.get("emergency_contact_name"),
            "emergency_contact_phone": kwargs.get("emergency_contact_phone"),
            "id_type": kwargs.get("id_type"),
            "id_number": kwargs.get("id_number"),
            "notes": kwargs.get("notes"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("tenants", data)

    def get_tenant(self, tenant_id: int) -> dict | None:
        """Get tenant by ID"""
        return self.db.fetch_one("SELECT * FROM tenants WHERE id = ?", (tenant_id,))

    def list_tenants(self) -> list[dict]:
        """List all tenants"""
        return self.db.fetch_all("SELECT * FROM tenants ORDER BY last_name, first_name")

    def search_tenants(self, query: str) -> list[dict]:
        """Search tenants by name or email"""
        return self.db.fetch_all(
            """
            SELECT * FROM tenants
            WHERE first_name LIKE ? OR last_name LIKE ? OR email LIKE ?
            ORDER BY last_name, first_name
        """,
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        )

    # Lease operations
    def create_lease(self, property_id: int, tenant_id: int, start_date: str, rent_amount: float, **kwargs) -> int:
        """Create a new lease"""
        now = get_timestamp()
        data = {
            "property_id": property_id,
            "unit_id": kwargs.get("unit_id"),
            "tenant_id": tenant_id,
            "lease_type": kwargs.get("lease_type", "long-term"),
            "start_date": start_date,
            "end_date": kwargs.get("end_date"),
            "rent_amount": rent_amount,
            "rent_frequency": kwargs.get("rent_frequency", "monthly"),
            "security_deposit": kwargs.get("security_deposit"),
            "deposit_paid": kwargs.get("deposit_paid", 0),
            "status": kwargs.get("status", "active"),
            "terms": kwargs.get("terms"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("leases", data)

    def get_lease(self, lease_id: int) -> dict | None:
        """Get lease with property and tenant info"""
        return self.db.fetch_one(
            """
            SELECT l.*,
                   p.name as property_name, p.address as property_address,
                   t.first_name || ' ' || t.last_name as tenant_name,
                   u.unit_number
            FROM leases l
            JOIN properties p ON l.property_id = p.id
            JOIN tenants t ON l.tenant_id = t.id
            LEFT JOIN units u ON l.unit_id = u.id
            WHERE l.id = ?
        """,
            (lease_id,),
        )

    def get_active_leases(self, property_id: int | None = None) -> list[dict]:
        """Get all active leases"""
        sql = """
            SELECT l.*,
                   p.name as property_name,
                   t.first_name || ' ' || t.last_name as tenant_name,
                   u.unit_number
            FROM leases l
            JOIN properties p ON l.property_id = p.id
            JOIN tenants t ON l.tenant_id = t.id
            LEFT JOIN units u ON l.unit_id = u.id
            WHERE l.status = 'active'
        """
        params = []
        if property_id:
            sql += " AND l.property_id = ?"
            params.append(property_id)
        sql += " ORDER BY l.end_date"
        return self.db.fetch_all(sql, tuple(params))

    def update_lease(self, lease_id: int, **kwargs) -> int:
        """Update lease fields"""
        kwargs["updated_at"] = get_timestamp()
        return self.db.update("leases", kwargs, "id = ?", (lease_id,))

    # Rent payment operations
    def record_payment(self, lease_id: int, amount: float, payment_date: str, due_date: str, **kwargs) -> int:
        """Record a rent payment"""
        data = {
            "lease_id": lease_id,
            "amount": amount,
            "payment_date": payment_date,
            "due_date": due_date,
            "payment_method": kwargs.get("payment_method"),
            "status": kwargs.get("status", "paid"),
            "notes": kwargs.get("notes"),
            "created_at": get_timestamp(),
        }
        return self.db.insert("rent_payments", data)

    def get_payments(self, lease_id: int) -> list[dict]:
        """Get all payments for a lease"""
        return self.db.fetch_all(
            "SELECT * FROM rent_payments WHERE lease_id = ? ORDER BY payment_date DESC", (lease_id,)
        )

    def get_overdue_payments(self) -> list[dict]:
        """Get all overdue rent payments"""
        today = date.today().isoformat()
        return self.db.fetch_all(
            """
            SELECT rp.*, l.rent_amount,
                   p.name as property_name,
                   t.first_name || ' ' || t.last_name as tenant_name
            FROM rent_payments rp
            JOIN leases l ON rp.lease_id = l.id
            JOIN properties p ON l.property_id = p.id
            JOIN tenants t ON l.tenant_id = t.id
            WHERE rp.status = 'pending' AND rp.due_date < ?
            ORDER BY rp.due_date
        """,
            (today,),
        )

    # Expense operations
    def add_expense(
        self, property_id: int, category: str, description: str, amount: float, expense_date: str, **kwargs
    ) -> int:
        """Record an expense"""
        data = {
            "property_id": property_id,
            "unit_id": kwargs.get("unit_id"),
            "category": category,
            "description": description,
            "amount": amount,
            "expense_date": expense_date,
            "vendor": kwargs.get("vendor"),
            "receipt_path": kwargs.get("receipt_path"),
            "recurring": kwargs.get("recurring", 0),
            "recurring_frequency": kwargs.get("recurring_frequency"),
            "notes": kwargs.get("notes"),
            "created_at": get_timestamp(),
        }
        return self.db.insert("expenses", data)

    def get_expenses(
        self, property_id: int, start_date: str | None = None, end_date: str | None = None, category: str | None = None
    ) -> list[dict]:
        """Get expenses with optional filtering"""
        sql = "SELECT * FROM expenses WHERE property_id = ?"
        params = [property_id]

        if start_date:
            sql += " AND expense_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND expense_date <= ?"
            params.append(end_date)
        if category:
            sql += " AND category = ?"
            params.append(category)

        sql += " ORDER BY expense_date DESC"
        return self.db.fetch_all(sql, tuple(params))

    def get_expense_summary(self, property_id: int, year: int | None = None) -> dict[str, float]:
        """Get expense summary by category"""
        sql = """
            SELECT category, SUM(amount) as total
            FROM expenses WHERE property_id = ?
        """
        params = [property_id]

        if year:
            sql += " AND strftime('%Y', expense_date) = ?"
            params.append(str(year))

        sql += " GROUP BY category"
        rows = self.db.fetch_all(sql, tuple(params))
        return {row["category"]: row["total"] for row in rows}

    # Maintenance operations
    def create_maintenance_request(self, property_id: int, category: str, title: str, **kwargs) -> int:
        """Create a maintenance request"""
        now = get_timestamp()
        data = {
            "property_id": property_id,
            "unit_id": kwargs.get("unit_id"),
            "reported_by": kwargs.get("reported_by"),
            "category": category,
            "priority": kwargs.get("priority", "normal"),
            "title": title,
            "description": kwargs.get("description"),
            "status": kwargs.get("status", "open"),
            "assigned_to": kwargs.get("assigned_to"),
            "estimated_cost": kwargs.get("estimated_cost"),
            "scheduled_date": kwargs.get("scheduled_date"),
            "notes": kwargs.get("notes"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("maintenance_requests", data)

    def get_maintenance_requests(self, property_id: int | None = None, status: str | None = None) -> list[dict]:
        """Get maintenance requests"""
        sql = """
            SELECT m.*, p.name as property_name, u.unit_number
            FROM maintenance_requests m
            JOIN properties p ON m.property_id = p.id
            LEFT JOIN units u ON m.unit_id = u.id
            WHERE 1=1
        """
        params = []

        if property_id:
            sql += " AND m.property_id = ?"
            params.append(property_id)
        if status:
            sql += " AND m.status = ?"
            params.append(status)

        sql += " ORDER BY CASE m.priority WHEN 'emergency' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END, m.created_at DESC"
        return self.db.fetch_all(sql, tuple(params))

    def update_maintenance(self, request_id: int, **kwargs) -> int:
        """Update maintenance request"""
        kwargs["updated_at"] = get_timestamp()
        if kwargs.get("status") == "completed":
            kwargs["completed_date"] = get_timestamp()
        return self.db.update("maintenance_requests", kwargs, "id = ?", (request_id,))

    # Mortgage operations
    def add_mortgage(
        self,
        property_id: int,
        lender: str,
        loan_amount: float,
        interest_rate: float,
        loan_term_years: int,
        start_date: str,
        monthly_payment: float,
        **kwargs,
    ) -> int:
        """Add mortgage information"""
        now = get_timestamp()
        data = {
            "property_id": property_id,
            "lender": lender,
            "loan_amount": loan_amount,
            "interest_rate": interest_rate,
            "loan_term_years": loan_term_years,
            "start_date": start_date,
            "monthly_payment": monthly_payment,
            "escrow_amount": kwargs.get("escrow_amount", 0),
            "remaining_balance": kwargs.get("remaining_balance", loan_amount),
            "notes": kwargs.get("notes"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("mortgages", data)

    def get_mortgage(self, property_id: int) -> dict | None:
        """Get mortgage for a property"""
        return self.db.fetch_one("SELECT * FROM mortgages WHERE property_id = ?", (property_id,))

    # Insurance operations
    def add_insurance(self, property_id: int, provider: str, premium_amount: float, start_date: str, **kwargs) -> int:
        """Add insurance policy"""
        now = get_timestamp()
        data = {
            "property_id": property_id,
            "provider": provider,
            "policy_number": kwargs.get("policy_number"),
            "policy_type": kwargs.get("policy_type", "property"),
            "coverage_amount": kwargs.get("coverage_amount"),
            "premium_amount": premium_amount,
            "premium_frequency": kwargs.get("premium_frequency", "yearly"),
            "start_date": start_date,
            "end_date": kwargs.get("end_date"),
            "notes": kwargs.get("notes"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("insurance", data)

    def get_insurance(self, property_id: int) -> list[dict]:
        """Get all insurance policies for a property"""
        return self.db.fetch_all("SELECT * FROM insurance WHERE property_id = ?", (property_id,))

    # Financial analytics
    def get_property_financials(self, property_id: int, year: int | None = None) -> dict[str, Any]:
        """Get comprehensive financial summary for a property"""
        year_filter = f" AND strftime('%Y', expense_date) = '{year}'" if year else ""
        year_filter_payments = f" AND strftime('%Y', payment_date) = '{year}'" if year else ""

        # Total income from rent
        income = self.db.fetch_one(
            f"""
            SELECT COALESCE(SUM(rp.amount), 0) as total_income
            FROM rent_payments rp
            JOIN leases l ON rp.lease_id = l.id
            WHERE l.property_id = ? AND rp.status = 'paid'
            {year_filter_payments}
        """,
            (property_id,),
        )

        # Total expenses by category
        expenses = self.db.fetch_all(
            f"""
            SELECT category, SUM(amount) as total
            FROM expenses WHERE property_id = ?
            {year_filter}
            GROUP BY category
        """,
            (property_id,),
        )

        total_expenses = sum(e["total"] for e in expenses)

        # Mortgage info
        mortgage = self.get_mortgage(property_id)
        mortgage_annual = mortgage["monthly_payment"] * 12 if mortgage else 0

        # Calculate key metrics
        property_info = self.get_property(property_id)
        net_income = (income["total_income"] if income else 0) - total_expenses

        # ROI calculation
        if property_info and property_info["purchase_price"]:
            roi = (net_income / property_info["purchase_price"]) * 100
        else:
            roi = 0

        return {
            "property_id": property_id,
            "year": year,
            "income": {"total_rent": income["total_income"] if income else 0},
            "expenses": {"by_category": {e["category"]: e["total"] for e in expenses}, "total": total_expenses},
            "mortgage": {
                "monthly_payment": mortgage["monthly_payment"] if mortgage else 0,
                "annual_payment": mortgage_annual,
                "remaining_balance": mortgage["remaining_balance"] if mortgage else 0,
            },
            "net_income": net_income,
            "roi_percent": round(roi, 2),
            "cash_flow_monthly": net_income / 12 if year else net_income,
        }

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Get summary of all properties"""
        properties = self.list_properties()

        total_value = sum(p["current_value"] or 0 for p in properties)
        total_equity = 0

        for prop in properties:
            mortgage = self.get_mortgage(prop["id"])
            if mortgage:
                equity = (prop["current_value"] or 0) - (mortgage["remaining_balance"] or 0)
            else:
                equity = prop["current_value"] or 0
            total_equity += equity

        # Vacancy rate
        total_units = self.db.fetch_one("SELECT COUNT(*) as count FROM units")
        vacant_units = self.db.fetch_one("SELECT COUNT(*) as count FROM units WHERE status = 'available'")

        vacancy_rate = 0
        if total_units and total_units["count"] > 0:
            vacancy_rate = (vacant_units["count"] / total_units["count"]) * 100

        # Open maintenance
        open_maintenance = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM maintenance_requests WHERE status IN ('open', 'in_progress')"
        )

        return {
            "total_properties": len(properties),
            "total_value": total_value,
            "total_equity": total_equity,
            "vacancy_rate": round(vacancy_rate, 1),
            "open_maintenance_requests": open_maintenance["count"] if open_maintenance else 0,
            "properties": properties,
        }

    def close(self):
        """Close database connection"""
        self.db.close()
