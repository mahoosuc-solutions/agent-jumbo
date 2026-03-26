from __future__ import annotations

from pathlib import Path

from instruments.custom.ideas.ideas_manager import IdeasManager


def _patch_abs_path(monkeypatch, tmp_path: Path):
    from python.helpers import files

    original = files.get_abs_path

    def patched(*parts: str):
        joined = "/".join(str(part).replace("\\", "/") for part in parts)
        if "usr/projects" in joined:
            name = Path(joined).name
            return str(tmp_path / "usr" / "projects" / name)
        if "instruments/custom/workflow_engine/data/workflow.db" in joined:
            return str(tmp_path / "workflow_engine.db")
        if "instruments/custom/work_queue/data/work_queue.db" in joined:
            return str(tmp_path / "work_queue.db")
        return original(*parts)

    monkeypatch.setattr(files, "get_abs_path", patched)


def test_create_idea_validates_required_fields(tmp_path):
    manager = IdeasManager(str(tmp_path / "ideas.db"))

    try:
        manager.create_idea({"title": "Missing note"})
    except ValueError as exc:
        assert "raw_note is required" in str(exc)
    else:
        raise AssertionError("expected ValueError for missing raw_note")


def test_update_idea_rejects_invalid_promotion_readiness(tmp_path):
    manager = IdeasManager(str(tmp_path / "ideas.db"))
    idea = manager.create_idea({"title": "Queue ideas", "raw_note": "Need a clean queue intake path"})

    try:
        manager.update_idea(idea["id"], {"promotion_readiness": "ship-it-now"})
    except ValueError as exc:
        assert "invalid promotion_readiness" in str(exc)
    else:
        raise AssertionError("expected ValueError for invalid promotion_readiness")


def test_promote_to_project_creates_project_workflow_and_queue_items(tmp_path, monkeypatch):
    from python.helpers import projects

    _patch_abs_path(monkeypatch, tmp_path)

    manager = IdeasManager(str(tmp_path / "ideas.db"))
    idea = manager.create_idea(
        {
            "title": "Operator ideas dashboard",
            "raw_note": "Capture rough ideas, refine them with chat, then promote the good ones.",
            "summary": "Turn rough ideas into launchable projects.",
            "theme": "Operator OS",
        }
    )

    result = manager.promote_to_project(idea["id"])

    assert result["idea"]["status"] == "promoted"
    assert result["idea"]["project_name"]
    assert result["workflow"]["name"].endswith("Starter Workflow")
    assert result["work_items_created"] == 3

    project_name = result["idea"]["project_name"]
    project = projects.load_edit_project_data(project_name)
    assert project["title"] == "Operator ideas dashboard"
    assert "Project origin: promoted from idea" in project["instructions"]

    work_queue_manager = __import__(
        "instruments.custom.work_queue.work_queue_manager",
        fromlist=["WorkQueueManager"],
    ).WorkQueueManager(str(tmp_path / "work_queue.db"))
    items = work_queue_manager.get_items(project_path=projects.get_project_folder(project_name))
    assert items["total"] == 3
    assert {item["source"] for item in items["items"]} == {"idea"}
    assert {item["source_type"] for item in items["items"]} == {"idea_next_step"}
