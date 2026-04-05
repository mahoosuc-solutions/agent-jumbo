"""
Centralised SQLite database path resolver.

All databases should use db_path(name) to get their storage location.
In Docker:  /aj/data/{name}
In dev:     {repo_root}/data/{name}
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def _is_dockerized() -> bool:
    return bool(os.getenv("DOCKERIZED")) or Path("/.dockerenv").exists()


def get_db_dir() -> Path:
    """Return the canonical data directory for all SQLite databases."""
    if _is_dockerized():
        d = Path("/aj/data")
    else:
        # Resolve relative to this file: python/helpers/db_paths.py → repo root → data/
        d = Path(__file__).parent.parent.parent / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def db_path(name: str) -> str:
    """Return the absolute path for a named database file."""
    return str(get_db_dir() / name)


def migrate_db_if_needed(old_path: str, name: str) -> None:
    """Copy old instrument-local DB to named volume location if new path is empty."""
    new = get_db_dir() / name
    old = Path(old_path)
    if old.exists() and not new.exists():
        shutil.copy2(str(old), str(new))
