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


@pytest.fixture()
def life_os_db(temp_db):
    """Temp DB initialized by LifeOSManager (via LifeOSDatabase schema init)."""
    from instruments.custom.life_os.life_manager import LifeOSManager

    LifeOSManager(temp_db)
    return temp_db


@pytest.fixture()
def workflow_engine_db():
    """Temp DB initialized by WorkflowEngineDatabase — uses a real temp dir so
    os.makedirs(dirname) inside the constructor doesn't fail."""
    import tempfile

    from instruments.custom.workflow_engine.workflow_db import WorkflowEngineDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "workflow_engine.db")
        WorkflowEngineDatabase(db_path)
        yield db_path
