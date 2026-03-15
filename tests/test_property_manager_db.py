import os

from instruments.custom.property_manager.property_db import PropertyDatabase


def test_property_db_roundtrip(tmp_path):
    data_dir = os.path.join(tmp_path, "data")
    db = PropertyDatabase(data_dir=data_dir)

    # Add a property
    prop_id = db.add_property(
        name="Sunset Motel",
        property_type="motel",
        address="123 Main St",
        city="Portland",
        state="OR",
        zip_code="97201",
        bedrooms=10,
        purchase_price=500000.0,
        current_value=600000.0,
    )
    assert prop_id

    # Get property
    prop = db.get_property(prop_id)
    assert prop["name"] == "Sunset Motel"
    assert prop["property_type"] == "motel"
    assert prop["city"] == "Portland"

    # Update property
    db.update_property(prop_id, current_value=650000.0)
    updated = db.get_property(prop_id)
    assert updated["current_value"] == 650000.0

    # List properties
    props = db.list_properties()
    assert len(props) == 1
    props_by_type = db.list_properties(property_type="motel")
    assert len(props_by_type) == 1

    # Add unit
    unit_id = db.add_unit(prop_id, "101", unit_type="room", rent_amount=89.99)
    assert unit_id
    units = db.get_units(prop_id)
    assert len(units) == 1
    assert units[0]["unit_number"] == "101"

    # Update unit
    db.update_unit(unit_id, status="occupied")
    units_after = db.get_units(prop_id)
    assert units_after[0]["status"] == "occupied"

    # Add tenant
    tenant_id = db.add_tenant("Jane", "Doe", email="jane@example.com", phone="555-1234")
    assert tenant_id
    tenant = db.get_tenant(tenant_id)
    assert tenant["first_name"] == "Jane"
    tenants = db.list_tenants()
    assert len(tenants) == 1

    # Search tenant
    found = db.search_tenants("Jane")
    assert len(found) == 1

    # Create lease
    lease_id = db.create_lease(
        property_id=prop_id,
        tenant_id=tenant_id,
        start_date="2025-01-01",
        rent_amount=1200.0,
        end_date="2026-01-01",
    )
    assert lease_id

    lease = db.get_lease(lease_id)
    assert lease["rent_amount"] == 1200.0

    active = db.get_active_leases()
    assert len(active) == 1

    # Record payment
    pay_id = db.record_payment(
        lease_id=lease_id,
        amount=1200.0,
        payment_date="2025-02-01",
        due_date="2025-02-01",
        payment_method="check",
    )
    assert pay_id
    payments = db.get_payments(lease_id)
    assert len(payments) == 1

    # Add expense
    exp_id = db.add_expense(
        property_id=prop_id,
        category="maintenance",
        description="Roof repair",
        amount=2500.0,
        expense_date="2025-03-01",
        vendor="Acme Roofing",
    )
    assert exp_id
    expenses = db.get_expenses(prop_id)
    assert len(expenses) == 1

    summary = db.get_expense_summary(prop_id)
    assert summary["maintenance"] == 2500.0

    # Maintenance request
    maint_id = db.create_maintenance_request(
        property_id=prop_id,
        category="plumbing",
        title="Leaky faucet in room 101",
        priority="high",
    )
    assert maint_id
    db.update_maintenance(maint_id, status="completed", actual_cost=150.0)

    # Portfolio summary
    portfolio = db.get_portfolio_summary()
    assert portfolio["total_properties"] == 1

    db.close()
