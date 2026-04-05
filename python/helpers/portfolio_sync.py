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
        color = meta.get("color", "")
        memory_mode = meta.get("memory", "own")
        instructions = meta.get("instructions", "")

        # Determine which meta_dir exists
        meta_dir = ".ajproj"
        for candidate in (".a0proj", ".ajproj"):
            if os.path.isdir(os.path.join(entry_path, candidate)):
                meta_dir = candidate
                break

        # Read lifecycle metadata
        lifecycle = _read_lifecycle_meta(entry_path, meta_dir)

        try:
            existing = db.get_project_by_path(entry_path)
            if existing:
                db.update_project(
                    existing["id"],
                    description=description,
                    status=existing.get("status", "draft"),
                    color=color,
                    memory_mode=memory_mode,
                    instructions=instructions,
                    meta_dir=meta_dir,
                    lifecycle_phase=lifecycle["lifecycle_phase"],
                    lifecycle_model=lifecycle["lifecycle_model"],
                    lifecycle_updated_at=lifecycle["lifecycle_updated_at"],
                )
                updated += 1
            else:
                db.add_project(
                    name=title,
                    path=entry_path,
                    description=description,
                    status="draft",
                    color=color,
                    memory_mode=memory_mode,
                    instructions=instructions,
                    meta_dir=meta_dir,
                    lifecycle_phase=lifecycle["lifecycle_phase"],
                    lifecycle_model=lifecycle["lifecycle_model"],
                    lifecycle_updated_at=lifecycle["lifecycle_updated_at"],
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


def _read_lifecycle_meta(project_path: str, meta_dir: str) -> dict:
    """Read lifecycle metadata from lifecycle.json if it exists"""
    lifecycle_file = os.path.join(project_path, meta_dir, "lifecycle", "lifecycle.json")
    if os.path.isfile(lifecycle_file):
        try:
            with open(lifecycle_file, encoding="utf-8") as f:
                lc = json.load(f)
            return {
                "lifecycle_phase": lc.get("current_phase", ""),
                "lifecycle_model": lc.get("lifecycle_model", ""),
                "lifecycle_updated_at": lc.get("updated_at", ""),
            }
        except Exception:
            pass
    return {"lifecycle_phase": "", "lifecycle_model": "", "lifecycle_updated_at": None}


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
