"""One-time migration: copy auth tables from workflow.db to identity.db.

Copies security_audit_log, user_profiles, and user_passkeys rows from the
old workflow engine database into the new dedicated identity database, then
drops the source tables from workflow.db to prevent confusion.

Safe to run multiple times — uses INSERT OR IGNORE to skip duplicates.

Usage:
    python scripts/migrate_identity_db.py [--dry-run]
"""

import argparse
import os
import sqlite3
import sys

# Ensure project root is on sys.path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.helpers import files
from python.helpers.identity_db import get_identity_db

WORKFLOW_DB_PATH = files.get_abs_path("./instruments/custom/workflow_engine/data/workflow.db")

TABLES = [
    {
        "name": "security_audit_log",
        "src_pk": "event_id",
        "dst_pk": "id",
        "columns": "event_type, status, user_id, ip_address, device_info, details, timestamp",
    },
    {
        "name": "user_profiles",
        "src_pk": "user_id",
        "dst_pk": "user_id",
        "columns": "user_id, full_name, email, phone_number, avatar_url, device_info, timezone, locale, last_synced",
    },
    {
        "name": "user_passkeys",
        "src_pk": "passkey_id",
        "dst_pk": "passkey_id",
        "columns": "passkey_id, user_id, public_key, sign_count, transports, created_at, last_used",
    },
]


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    return row[0] > 0


def count_rows(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def migrate(dry_run: bool = False):
    if not os.path.exists(WORKFLOW_DB_PATH):
        print(f"Source database not found: {WORKFLOW_DB_PATH}")
        print("Nothing to migrate.")
        return

    # Open source (workflow.db)
    src = sqlite3.connect(WORKFLOW_DB_PATH)
    src.row_factory = sqlite3.Row

    # Open/create destination (identity.db)
    identity_db = get_identity_db()
    dst = identity_db._get_conn()

    print(f"Source:      {WORKFLOW_DB_PATH}")
    print(f"Destination: {identity_db.db_path}")
    print(f"Dry run:     {dry_run}")
    print()

    total_migrated = 0

    for table_info in TABLES:
        table = table_info["name"]
        columns = table_info["columns"]

        if not table_exists(src, table):
            print(f"  [{table}] not found in source — skipping")
            continue

        src_count = count_rows(src, table)
        print(f"  [{table}] {src_count} rows in source")

        if src_count == 0:
            print(f"  [{table}] nothing to migrate")
            continue

        if dry_run:
            print(f"  [{table}] would migrate {src_count} rows")
            total_migrated += src_count
            continue

        # Read all rows from source
        rows = src.execute(f"SELECT {columns} FROM {table}").fetchall()

        # Insert into destination (skip duplicates)
        placeholders = ", ".join(["?"] * len(columns.split(", ")))
        inserted = 0
        for row in rows:
            try:
                dst.execute(
                    f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})",
                    tuple(row),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                pass

        dst.commit()
        dst_count = count_rows(dst, table)
        print(f"  [{table}] inserted {inserted} rows → {dst_count} total in destination")
        total_migrated += inserted

    print()

    # Drop source tables (only if not dry run and migration succeeded)
    if not dry_run and total_migrated >= 0:
        print("Cleaning up source tables from workflow.db...")
        for table_info in TABLES:
            table = table_info["name"]
            if table_exists(src, table):
                src.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  Dropped {table}")
        src.commit()
        print("Cleanup complete.")
    elif dry_run:
        print("Dry run — no changes made. Run without --dry-run to execute.")

    src.close()
    dst.close()

    print()
    print(f"Migration complete. {total_migrated} rows processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate auth tables from workflow.db to identity.db")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be migrated without making changes")
    args = parser.parse_args()

    migrate(dry_run=args.dry_run)
