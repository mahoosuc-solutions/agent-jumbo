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


def db_path(name: str, organization_id: str | None = None) -> str:
    """Return the absolute path for a named database file.

    In cloud mode with an organization_id, data is scoped per-org:
      data/{org_id}/{name}
    In standalone mode (no org), data lives in the root:
      data/{name}
    """
    base = get_db_dir()
    if organization_id:
        org_dir = base / organization_id
        org_dir.mkdir(parents=True, exist_ok=True)
        return str(org_dir / name)
    return str(base / name)


def get_current_org_id() -> str | None:
    """Get the current organization_id from MOS session, or None in standalone mode."""
    try:
        from flask import session

        mos_user = session.get("mos_user", {})
        return mos_user.get("organization_id") or None
    except Exception:
        return None


def db_path_scoped(name: str) -> str:
    """Return a tenant-scoped database path using the current session's org_id."""
    return db_path(name, get_current_org_id())


def migrate_db_if_needed(old_path: str, name: str) -> None:
    """Copy old instrument-local DB to named volume location if new path is empty."""
    new = get_db_dir() / name
    old = Path(old_path)
    if old.exists() and not new.exists():
        shutil.copy2(str(old), str(new))
