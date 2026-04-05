"""Database Backup — snapshots all instrument SQLite databases."""

import glob
import logging
import os
import shutil
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)


def backup_all_databases(
    instruments_dir: str = "instruments/custom",
    backup_dir: str = "backups/db",
    max_backups: int = 7,
) -> dict:
    """Backup all instrument SQLite databases using the SQLite online backup API.

    Returns a dict with keys:
        backed_up   — number of databases successfully backed up
        errors      — list of {db, error} dicts for any failures
        snapshot_dir — absolute path to this snapshot's directory
        timestamp   — snapshot timestamp string
        total_dbs   — total number of .db files found
    """
    from python.helpers import files
    from python.helpers.db_paths import get_db_dir

    abs_instruments = files.get_abs_path(f"./{instruments_dir}")
    abs_backup = files.get_abs_path(f"./{backup_dir}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_dir = os.path.join(abs_backup, timestamp)
    os.makedirs(snapshot_dir, exist_ok=True)

    backed_up = 0
    errors: list[dict] = []

    # Find all .db files in instrument data dirs (legacy location)
    db_files = glob.glob(os.path.join(abs_instruments, "*/data/*.db"))

    # Also find all .db files in the centralized data directory
    data_dir = str(get_db_dir())
    centralized_db_files = glob.glob(os.path.join(data_dir, "*.db"))

    # Process legacy instrument databases
    for db_path in db_files:
        db_name = os.path.basename(db_path)
        instrument = os.path.basename(os.path.dirname(os.path.dirname(db_path)))
        backup_path = os.path.join(snapshot_dir, f"{instrument}_{db_name}")

        try:
            # Use SQLite online backup API (safe for WAL mode)
            source = sqlite3.connect(db_path)
            dest = sqlite3.connect(backup_path)
            source.backup(dest)
            dest.close()
            source.close()
            backed_up += 1
            logger.info("Backed up %s/%s", instrument, db_name)
        except Exception as e:
            errors.append({"db": f"{instrument}/{db_name}", "error": str(e)})
            logger.error("Failed to backup %s/%s: %s", instrument, db_name, e)

    # Process centralized databases from data/ directory
    for db_path in centralized_db_files:
        db_name = os.path.basename(db_path)
        backup_path = os.path.join(snapshot_dir, f"data_{db_name}")

        try:
            # Use SQLite online backup API (safe for WAL mode)
            source = sqlite3.connect(db_path)
            dest = sqlite3.connect(backup_path)
            source.backup(dest)
            dest.close()
            source.close()
            backed_up += 1
            logger.info("Backed up data/%s", db_name)
        except Exception as e:
            errors.append({"db": f"data/{db_name}", "error": str(e)})
            logger.error("Failed to backup data/%s: %s", db_name, e)

    # Prune old backups beyond retention limit
    _prune_backups(abs_backup, max_backups)

    total_dbs = len(db_files) + len(centralized_db_files)

    return {
        "backed_up": backed_up,
        "errors": errors,
        "snapshot_dir": snapshot_dir,
        "timestamp": timestamp,
        "total_dbs": total_dbs,
    }


def _prune_backups(backup_dir: str, max_backups: int):
    """Keep only the latest *max_backups* snapshot directories."""
    if not os.path.exists(backup_dir):
        return
    snapshots = sorted(
        [d for d in os.listdir(backup_dir) if os.path.isdir(os.path.join(backup_dir, d))],
        reverse=True,
    )
    for old in snapshots[max_backups:]:
        old_path = os.path.join(backup_dir, old)
        shutil.rmtree(old_path, ignore_errors=True)
        logger.info("Pruned old backup: %s", old)
