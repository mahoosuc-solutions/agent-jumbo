import os
import sqlite3
import time
import unittest

from python.helpers import files
from python.helpers.security import SecurityManager


class TestPerformanceSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure we have a clean test environment."""
        cls.db_path = files.get_abs_path("./data/identity.db")
        # Ensure directory exists
        os.makedirs(os.path.dirname(cls.db_path), exist_ok=True)
        # Ensure identity DB tables exist
        from python.helpers.identity_db import get_identity_db

        get_identity_db()

    def test_async_logging_speed(self):
        """Validates that log_event returns nearly instantaneously (asynchronous)."""
        start_time = time.perf_counter()

        # Log 10 events rapidly
        for i in range(10):
            SecurityManager.log_event("perf_test", "success", details={"index": i})

        end_time = time.perf_counter()
        duration = (end_time - start_time) * 1000  # convert to ms

        print(f"\n[PERF] 10 Async Logs took: {duration:.2f}ms")

        # 10 synchronous SQLite commits would take at least 50-200ms
        # Async should take < 5ms total for queuing
        self.assertLess(duration, 20.0, "Async logging is slower than expected (overhead should be negligible)")

    def test_database_persistence(self):
        """Verifies that async logs actually make it to the database."""
        test_id = f"test_{int(time.time())}"
        SecurityManager.log_event("persistence_check", "success", user_id=test_id)

        # Poll for the background thread to flush (up to 5s)
        row = None
        for _ in range(10):
            time.sleep(0.5)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT event_type FROM security_audit_log WHERE user_id = ?", (test_id,))
            row = cursor.fetchone()
            conn.close()
            if row:
                break

        self.assertIsNotNone(row, "Log event was not persisted to the database")
        self.assertEqual(row[0], "persistence_check")

    def test_wal_mode_enabled(self):
        """Checks if the database is running in WAL mode for concurrency."""
        from python.helpers.identity_db import IdentityDatabase

        db = IdentityDatabase(self.db_path)
        conn = db._get_conn()
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        conn.close()

        self.assertEqual(mode.lower(), "wal", "Database should be in WAL mode for performance")


if __name__ == "__main__":
    unittest.main()
