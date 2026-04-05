from pathlib import Path

from scripts.validate_post_deploy_runtime import CheckResult, manual_smoke_markdown, write_artifacts


def test_manual_smoke_markdown_includes_browser_and_restart_evidence():
    results = [
        CheckResult("health", True, "status=healthy"),
        CheckResult("scheduler_file", True, "128 /aj/data/scheduler/tasks.json"),
        CheckResult("browser_smoke", True, "all good"),
        CheckResult("restart", True, "agent-jumbo-production"),
    ]
    artifacts = {
        "scheduler_api": {"task_count": 29},
        "scheduler_api_after_restart": {"task_count": 29},
        "browser": {
            "work_queue": {"heading": "Work Queue"},
            "workflows": {"active_dashboard": "workflows"},
            "tasks": {"cards": 29},
            "trust": {"level_cards": 4},
            "new_chat": {"changed": True},
        },
    }

    markdown = manual_smoke_markdown(
        timestamp="20260405-120000",
        base_url="http://localhost:6274",
        browser_base_url="http://127.0.0.1:80",
        container="agent-jumbo-production",
        results=results,
        artifacts=artifacts,
        restart_container=True,
    )

    assert "# Manual Smoke Record" in markdown
    assert "agent-jumbo-production" in markdown
    assert "tasks=`29`" not in markdown
    assert "tasks=29" in markdown
    assert "Work Queue" in markdown
    assert "new chat changed" in markdown.lower()


def test_write_artifacts_creates_markdown_and_json(tmp_path: Path):
    markdown_path, json_path = write_artifacts(
        report_dir=str(tmp_path),
        timestamp="20260405-120000",
        markdown="# Manual Smoke Record\n",
        artifacts={"browser": {"tasks": {"cards": 29}}},
    )

    assert Path(markdown_path).read_text() == "# Manual Smoke Record\n"
    assert '"cards": 29' in Path(json_path).read_text()
