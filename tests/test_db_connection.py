"""Unit tests for DatabaseConnection and SyncLogMixin."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.helpers.db_connection import DatabaseConnection, SyncLogMixin


class TestDatabaseConnection:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.db = DatabaseConnection(os.path.join(self.tmp, "test.db"))
        self.db.conn.execute("CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)")
        self.db.conn.commit()

    def teardown_method(self):
        self.db.close()

    def test_lazy_connection_sets_wal(self):
        cursor = self.db.conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal"

    def test_transaction_commits_on_success(self):
        with self.db.transaction() as conn:
            conn.execute("INSERT INTO kv (key, value) VALUES ('a', '1')")
        row = self.db.query_one("SELECT value FROM kv WHERE key = 'a'")
        assert row is not None
        assert row["value"] == "1"

    def test_transaction_rolls_back_on_exception(self):
        with pytest.raises(ValueError):
            with self.db.transaction() as conn:
                conn.execute("INSERT INTO kv (key, value) VALUES ('b', '2')")
                raise ValueError("test error")
        row = self.db.query_one("SELECT value FROM kv WHERE key = 'b'")
        assert row is None

    def test_query_rows_returns_list_of_dicts(self):
        with self.db.transaction() as conn:
            conn.execute("INSERT INTO kv (key, value) VALUES ('x', '10')")
            conn.execute("INSERT INTO kv (key, value) VALUES ('y', '20')")
        rows = self.db.query_rows("SELECT * FROM kv ORDER BY key")
        assert len(rows) == 2
        assert rows[0] == {"key": "x", "value": "10"}
        assert rows[1] == {"key": "y", "value": "20"}

    def test_query_rows_empty_returns_empty_list(self):
        rows = self.db.query_rows("SELECT * FROM kv")
        assert rows == []

    def test_query_one_returns_single_dict(self):
        with self.db.transaction() as conn:
            conn.execute("INSERT INTO kv (key, value) VALUES ('z', '99')")
        row = self.db.query_one("SELECT * FROM kv WHERE key = 'z'")
        assert row == {"key": "z", "value": "99"}

    def test_query_one_returns_none_when_empty(self):
        row = self.db.query_one("SELECT * FROM kv WHERE key = 'missing'")
        assert row is None

    def test_close_and_reopen(self):
        with self.db.transaction() as conn:
            conn.execute("INSERT INTO kv (key, value) VALUES ('persist', 'yes')")
        self.db.close()
        assert self.db._conn is None
        # Reopen via lazy property
        row = self.db.query_one("SELECT value FROM kv WHERE key = 'persist'")
        assert row["value"] == "yes"

    def test_connection_reused_across_calls(self):
        conn1 = self.db.conn
        conn2 = self.db.conn
        assert conn1 is conn2

    def test_mkdir_creates_parent_dirs(self):
        nested_path = os.path.join(self.tmp, "a", "b", "c", "test.db")
        db = DatabaseConnection(nested_path)
        assert os.path.isdir(os.path.dirname(nested_path))
        db.close()


class TestSyncLogMixin:
    """Test SyncLogMixin via a minimal concrete class."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()

        class SyncDB(SyncLogMixin):
            def __init__(self, path):
                self.db = DatabaseConnection(path)
                self.db.conn.execute("""
                    CREATE TABLE IF NOT EXISTS sync_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sync_type TEXT NOT NULL,
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP,
                        status TEXT DEFAULT 'running',
                        items_synced INTEGER DEFAULT 0,
                        error TEXT
                    )
                """)
                self.db.conn.commit()

        self.sync_db = SyncDB(os.path.join(self.tmp, "sync_test.db"))

    def teardown_method(self):
        self.sync_db.db.close()

    def test_start_and_complete_sync(self):
        sync_id = self.sync_db.start_sync("full")
        assert isinstance(sync_id, int)
        self.sync_db.complete_sync(sync_id, 42)
        last = self.sync_db.get_last_sync("full")
        assert last is not None
        assert last["items_synced"] == 42
        assert last["status"] == "completed"

    def test_sync_error(self):
        sync_id = self.sync_db.start_sync("partial")
        self.sync_db.complete_sync(sync_id, 0, error="Connection timeout")
        last = self.sync_db.get_last_sync()
        assert last["status"] == "error"
        assert last["error"] == "Connection timeout"

    def test_get_last_sync_none_when_empty(self):
        assert self.sync_db.get_last_sync() is None

    def test_get_last_sync_filtered_by_type(self):
        s1 = self.sync_db.start_sync("type_a")
        self.sync_db.complete_sync(s1, 1)
        s2 = self.sync_db.start_sync("type_b")
        self.sync_db.complete_sync(s2, 2)

        last_a = self.sync_db.get_last_sync("type_a")
        assert last_a["sync_type"] == "type_a"
        assert last_a["items_synced"] == 1

        last_b = self.sync_db.get_last_sync("type_b")
        assert last_b["sync_type"] == "type_b"
        assert last_b["items_synced"] == 2
