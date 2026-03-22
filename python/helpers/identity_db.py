"""Identity Database — user profiles, passkeys, and security audit log.

Separated from the workflow engine DB to keep auth/identity concerns
independent of workflow orchestration.
"""

import os
import sqlite3


class IdentityDatabase:
    """SQLite database for user identity, passkeys, and security audit logging."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self):
        """Initialize identity tables."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_passkeys (
                passkey_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                public_key BLOB NOT NULL,
                sign_count INTEGER DEFAULT 0,
                transports TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                full_name TEXT,
                email TEXT,
                phone_number TEXT,
                avatar_url TEXT,
                device_info TEXT,
                timezone TEXT,
                locale TEXT,
                push_subscription TEXT,
                last_synced TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                status TEXT NOT NULL,
                user_id TEXT,
                ip_address TEXT,
                device_info TEXT,
                details TEXT,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()


# Default path for the identity database
IDENTITY_DB_PATH = "./data/identity.db"


def get_identity_db(db_path: str | None = None) -> IdentityDatabase:
    """Get an IdentityDatabase instance with the default or specified path."""
    from python.helpers import files

    path = files.get_abs_path(db_path or IDENTITY_DB_PATH)
    return IdentityDatabase(path)
