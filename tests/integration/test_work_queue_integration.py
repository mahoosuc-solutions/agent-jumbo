"""Integration tests for WorkQueueManager — no server required."""

import sqlite3

import pytest

pytestmark = [pytest.mark.integration]

# Minimal valid work_item row matching the real schema's NOT NULL constraints
_ITEM_DEFAULTS = {
    "external_id": "test-ext-1",
    "source": "test",
    "source_type": "manual",
    "title": "Test item",
    "status": "discovered",
    "priority_score": 0,
    "project_path": "/tmp/test-project",
}

_INSERT_SQL = """
    INSERT INTO work_items
        (external_id, source, source_type, title, status, priority_score, project_path)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""


def _insert_item(db_path: str, overrides: dict | None = None) -> None:
    """Insert a work item using real schema columns."""
    vals = {**_ITEM_DEFAULTS, **(overrides or {})}
    conn = sqlite3.connect(db_path)
    conn.execute(
        _INSERT_SQL,
        (
            vals["external_id"],
            vals["source"],
            vals["source_type"],
            vals["title"],
            vals["status"],
            vals["priority_score"],
            vals["project_path"],
        ),
    )
    conn.commit()
    conn.close()


def test_work_queue_manager_init(work_queue_db):
    """WorkQueueManager initializes with a fresh database."""
    from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

    manager = WorkQueueManager(work_queue_db)
    dashboard = manager.get_dashboard()
    assert dashboard["total"] == 0
    assert isinstance(dashboard["by_status"], dict)


def test_work_queue_add_and_list(work_queue_db):
    """Add an item and verify it appears in the dashboard."""
    from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

    manager = WorkQueueManager(work_queue_db)
    _insert_item(work_queue_db, {"title": "Listed item", "priority_score": 5})

    dashboard = manager.get_dashboard()
    assert dashboard["total"] == 1


def test_work_queue_update_status(work_queue_db):
    """Update an item's status via the manager."""
    from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

    manager = WorkQueueManager(work_queue_db)
    _insert_item(work_queue_db, {"title": "Status test"})

    result = manager.update_item_status(1, "queued")
    assert result is True


def test_work_queue_bulk_update(work_queue_db):
    """Bulk update statuses for multiple items."""
    from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

    manager = WorkQueueManager(work_queue_db)
    for i in range(3):
        _insert_item(
            work_queue_db,
            {"external_id": f"bulk-{i}", "title": f"Bulk item {i}"},
        )

    count = manager.bulk_update_status([1, 2, 3], "queued")
    assert count == 3


def test_security_audit_log_empty(workflow_db):
    """Query security audit log from empty database."""
    conn = sqlite3.connect(workflow_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM security_audit_log ORDER BY timestamp DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    assert len(rows) == 0
