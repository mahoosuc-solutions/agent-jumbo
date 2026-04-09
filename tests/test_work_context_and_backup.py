from pathlib import Path
from types import SimpleNamespace

import pytest

from python.extensions.system_prompt._10_system_prompt import get_work_context_prompt
from python.helpers.backup import BackupService
from python.helpers.tool import Response, Tool


def test_backup_defaults_include_runtime_db_volume(monkeypatch):
    monkeypatch.setattr("python.helpers.backup.get_db_dir", lambda: Path("/aj/data"))

    service = BackupService()
    service.agent_mahoo_root = "/repo"

    metadata = service.get_default_backup_metadata()

    assert "aj/data/*.db" in metadata["include_patterns"]
    assert "aj/data/*.db-wal" in metadata["include_patterns"]
    assert "aj/data/*.db-shm" in metadata["include_patterns"]


def test_get_work_context_prompt_returns_agent_data():
    agent = SimpleNamespace(
        get_data=lambda key: "## Work Context\n- resume this task\n" if key == "work_context" else None
    )

    assert get_work_context_prompt(agent) == "## Work Context\n- resume this task"


class _DummyTool(Tool):
    async def execute(self, **kwargs) -> Response:
        return Response(message="ok", break_loop=False)


@pytest.mark.asyncio
async def test_tool_after_execution_logs_with_context_id(monkeypatch):
    captured: dict[str, str] = {}

    def fake_get_or_create_session(context_id: str, project_name: str | None):
        captured["session_context_id"] = context_id
        captured["project_name"] = project_name or ""
        return "session-1"

    def fake_log_tool_use(**kwargs):
        captured["logged_context_id"] = kwargs["context_id"]
        captured["tool_name"] = kwargs["tool_name"]

    monkeypatch.setattr("python.helpers.agent_journal.get_or_create_session", fake_get_or_create_session)
    monkeypatch.setattr("python.helpers.agent_journal.log_tool_use", fake_log_tool_use)

    async def hist_add_tool_result(name, text, **kwargs):
        return None

    fake_agent = SimpleNamespace(
        agent_name="A0",
        context=SimpleNamespace(id="ctx-123"),
        active_project=None,
        hist_add_tool_result=hist_add_tool_result,
    )

    tool = _DummyTool(
        agent=fake_agent,
        name="demo_tool",
        method=None,
        args={},
        message="",
        loop_data=None,
    )
    tool.log = SimpleNamespace(update=lambda **kwargs: None)

    await tool.after_execution(Response(message="done", break_loop=False))

    assert captured["session_context_id"] == "ctx-123"
    assert captured["logged_context_id"] == "ctx-123"
    assert captured["tool_name"] == "demo_tool"


def test_scheduler_storage_defaults_to_persisted_data_dir(monkeypatch, tmp_path):
    from python.helpers import task_scheduler

    monkeypatch.setattr(
        task_scheduler,
        "get_abs_path",
        lambda *parts: str(tmp_path.joinpath(*[str(part).lstrip("/") for part in parts])),
    )

    path = task_scheduler.get_scheduler_tasks_path()

    assert path.endswith("data/scheduler/tasks.json")


def test_scheduler_storage_migrates_legacy_tmp_file(monkeypatch, tmp_path):
    from python.helpers import task_scheduler

    monkeypatch.setattr(
        task_scheduler,
        "get_abs_path",
        lambda *parts: str(tmp_path.joinpath(*[str(part).lstrip("/") for part in parts])),
    )

    legacy_path = Path(task_scheduler.get_legacy_scheduler_tasks_path())
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_payload = '{"tasks":[{"uuid":"123","context_id":"123","state":"idle","name":"Legacy","system_prompt":"","prompt":"","attachments":[],"project_name":null,"project_color":null,"created_at":"2026-04-05T00:00:00Z","updated_at":"2026-04-05T00:00:00Z","last_run":null,"last_result":null,"type":"adhoc","token":"999"}]}'
    legacy_path.write_text(legacy_payload)

    migrated_path = Path(task_scheduler.ensure_scheduler_tasks_file())

    assert migrated_path.read_text() == legacy_payload
    assert migrated_path == tmp_path / "data" / "scheduler" / "tasks.json"
