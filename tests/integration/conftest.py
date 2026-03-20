"""Integration test fixtures — lightweight component testing without full server."""

import os
import sqlite3
import tempfile

import pytest


@pytest.fixture()
def temp_db():
    """Create a temporary SQLite database file, cleaned up after test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture()
def work_queue_db(temp_db):
    """Temp DB with work_queue schema — uses the real WorkQueueDatabase to init."""
    from instruments.custom.work_queue.work_queue_db import WorkQueueDatabase

    WorkQueueDatabase(temp_db)
    return temp_db


@pytest.fixture()
def workflow_db(temp_db):
    """Temp DB with security_audit_log schema pre-created."""
    conn = sqlite3.connect(temp_db)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS security_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            event_type TEXT DEFAULT '',
            status TEXT DEFAULT '',
            user_id TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            device_info TEXT DEFAULT '',
            details TEXT DEFAULT ''
        );
    """)
    conn.close()
    return temp_db
