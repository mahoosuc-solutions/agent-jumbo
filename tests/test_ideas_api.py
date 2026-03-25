from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from python.api.ideas_dashboard import IdeasDashboard
from python.api.ideas_update import IdeasUpdate


class DummyRequest:
    def __init__(self, payload=None):
        self._payload = payload or {}
        self.is_json = True
        self.data = json.dumps(self._payload).encode("utf-8")

    def get_json(self):
        return self._payload


def _patch_abs_path(monkeypatch, tmp_path: Path):
    from python.helpers import files

    original = files.get_abs_path

    def patched(*parts: str):
        joined = "/".join(str(part).replace("\\", "/") for part in parts)
        if "instruments/custom/ideas/data/ideas.db" in joined:
            return str(tmp_path / "ideas.db")
        if "instruments/custom/workflow_engine/data/workflow.db" in joined:
            return str(tmp_path / "workflow_engine.db")
        if "instruments/custom/work_queue/data/work_queue.db" in joined:
            return str(tmp_path / "work_queue.db")
        if "usr/projects" in joined:
            name = Path(joined).name
            return str(tmp_path / "usr" / "projects" / name)
        return original(*parts)

    monkeypatch.setattr(files, "get_abs_path", patched)


@pytest.mark.asyncio
async def test_ideas_dashboard_create_and_list(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)

    update_handler = IdeasUpdate(SimpleNamespace(), SimpleNamespace())
    create_result = await update_handler.process(
        {"action": "create", "idea": {"title": "Triage inbox", "raw_note": "Turn inbox noise into projects"}},
        DummyRequest(),
    )
    assert create_result["success"] is True

    dashboard_handler = IdeasDashboard(SimpleNamespace(), SimpleNamespace())
    list_result = await dashboard_handler.process({"action": "list"}, DummyRequest())

    assert list_result["success"] is True
    assert list_result["total"] == 1
    assert list_result["ideas"][0]["title"] == "Triage inbox"


@pytest.mark.asyncio
async def test_ideas_update_promote_to_project(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)

    handler = IdeasUpdate(SimpleNamespace(), SimpleNamespace())
    created = await handler.process(
        {
            "action": "create",
            "idea": {
                "title": "Idea promotion",
                "raw_note": "Promote good ideas into a project with starter execution scaffolding.",
            },
        },
        DummyRequest(),
    )

    promoted = await handler.process(
        {"action": "promote_to_project", "idea_id": created["idea"]["id"]},
        DummyRequest(),
    )

    assert promoted["success"] is True
    assert promoted["idea"]["status"] == "promoted"
    assert promoted["project"]["name"]
    assert promoted["workflow"]["status"] == "created"
    assert promoted["work_items_created"] == 3
