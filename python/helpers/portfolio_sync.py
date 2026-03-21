"""Sync Core Projects (usr/projects/) into the Portfolio Manager database."""

from __future__ import annotations

import json
import os
from typing import Any


def sync_core_projects_to_portfolio(
    projects_dir: str | None = None,
    db: Any | None = None,
) -> dict[str, int]:
    """
    Scan Core Projects directory and upsert each into the Portfolio Manager DB.

    Args:
        projects_dir: Path to usr/projects/. If None, uses the default.
        db: PortfolioDatabase instance. If None, creates one.

    Returns:
        Summary dict with added, updated, total, and errors counts.
    """
    if projects_dir is None:
        from python.helpers import projects

        projects_dir = projects.get_projects_parent_folder()

    if db is None:
        from instruments.custom.portfolio_manager.portfolio_db import PortfolioDatabase

        db = PortfolioDatabase()

    added = 0
    updated = 0
    errors = 0

    if not os.path.isdir(projects_dir):
        return {"added": 0, "updated": 0, "total": 0, "errors": 0}

    for entry in sorted(os.listdir(projects_dir)):
        entry_path = os.path.join(projects_dir, entry)
        if not os.path.isdir(entry_path):
            continue

        # Read project metadata if available
        meta = _read_project_meta(entry_path)
        title = meta.get("title") or entry
        description = meta.get("description", "")

        try:
            existing = db.get_project_by_path(entry_path)
            if existing:
                db.update_project(
                    existing["id"],
                    description=description,
                    status=existing.get("status", "draft"),
                )
                updated += 1
            else:
                db.add_project(
                    name=title,
                    path=entry_path,
                    description=description,
                    status="draft",
                )
                added += 1
        except Exception:
            errors += 1

    return {
        "added": added,
        "updated": updated,
        "total": added + updated,
        "errors": errors,
    }


def _read_project_meta(project_path: str) -> dict:
    """Read .a0proj/project.json or .ajproj/project.json if it exists."""
    for meta_dir in (".a0proj", ".ajproj"):
        meta_file = os.path.join(project_path, meta_dir, "project.json")
        if os.path.isfile(meta_file):
            try:
                with open(meta_file, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}
