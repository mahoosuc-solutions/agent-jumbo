"""Integration tests for LifeOSManager — no server required."""

import pytest

pytestmark = [pytest.mark.integration]


def test_life_os_dashboard_empty(life_os_db):
    """get_dashboard() on a fresh DB returns a valid structure with zero events."""
    from instruments.custom.life_os.life_manager import LifeOSManager

    manager = LifeOSManager(life_os_db)
    dashboard = manager.get_dashboard()

    assert isinstance(dashboard, dict)
    assert dashboard["event_count"] == 0
    assert dashboard["latest_event"] is None
    assert isinstance(dashboard["widgets"], list)
    assert isinstance(dashboard["sources"], dict)


def test_life_os_emit_and_read_event(life_os_db):
    """Emitting an event stores it and get_dashboard() reflects it."""
    from instruments.custom.life_os.life_manager import LifeOSManager

    manager = LifeOSManager(life_os_db)
    result = manager.emit_event("health.sleep", {"hours": 7.5})

    assert "id" in result
    assert result["type"] == "health.sleep"
    assert result["payload"]["hours"] == 7.5

    dashboard = manager.get_dashboard()
    assert dashboard["event_count"] == 1
    assert dashboard["latest_event"] is not None


def test_life_os_dashboard_after_multiple_events(life_os_db):
    """Dashboard correctly aggregates sources after several events."""
    from instruments.custom.life_os.life_manager import LifeOSManager

    manager = LifeOSManager(life_os_db)
    manager.emit_event("health.sleep", {"hours": 8})
    manager.emit_event("health.exercise", {"minutes": 30})
    manager.emit_event("finance.expense", {"amount": 50})

    dashboard = manager.get_dashboard()
    assert dashboard["event_count"] == 3
    # Sources are bucketed by the first dot-segment of the event type
    assert dashboard["sources"].get("health") == 2
    assert dashboard["sources"].get("finance") == 1
