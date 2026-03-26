from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "render_folder_workflow_summary.py"
SPEC = importlib.util.spec_from_file_location("render_folder_workflow_summary", MODULE_PATH)
assert SPEC and SPEC.loader
render_folder_workflow_summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_folder_workflow_summary)


def _write_envelope(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"payload": payload}, indent=2) + "\n", encoding="utf-8")


def test_build_summary_includes_release_and_deploy_details(tmp_path):
    artifact_root = tmp_path / "fdw_123" / "artifacts"
    run_root = artifact_root.parent
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "run_record.json").write_text(
        json.dumps(
            {
                "project_name": "demo_project",
                "run_id": "fdw_123",
                "status": "gated",
                "target_path": "/repo/python/helpers",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_envelope(
        artifact_root / "release_bundle.json",
        {
            "commit_sha": "abc123",
            "pr_number": "4",
            "linear_issue_keys": ["AJB-123", "AJB-124"],
            "deployment_reference": {
                "workflow_run_id": "999",
                "build_id": "3",
                "status": "success",
            },
        },
    )
    _write_envelope(
        artifact_root / "release_readiness.json",
        {"ready": True, "blocking_checks": []},
    )
    _write_envelope(
        artifact_root / "linear_plan.json",
        {
            "parent_issue": {"identifier": "AJB-123"},
            "child_issues": [{"identifier": "AJB-124"}],
        },
    )
    _write_envelope(
        artifact_root / "deploy_run.json",
        {"deployment_system": "github_actions"},
    )
    _write_envelope(
        artifact_root / "post_deploy_report.json",
        {
            "status": "healthy",
            "checks": {
                "chat_readiness": True,
                "health_endpoint": True,
                "monitoring_snapshot": True,
                "schema_verification": True,
                "workflow_smoke": False,
            },
        },
    )

    markdown = render_folder_workflow_summary.build_summary([artifact_root])
    assert "Folder Workflow Evidence" in markdown
    assert "`demo_project` / `fdw_123`" in markdown
    assert "Commit: `abc123`" in markdown
    assert "Deploy run: `999`" in markdown
    assert "Post deploy: `healthy`" in markdown


def test_main_writes_output_and_step_summary(tmp_path, monkeypatch):
    artifact_root = tmp_path / "fdw_456" / "artifacts"
    run_root = artifact_root.parent
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "run_record.json").write_text(
        json.dumps({"project_name": "demo", "run_id": "fdw_456"}, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_envelope(artifact_root / "release_bundle.json", {"commit_sha": "def456", "pr_number": "5"})

    output_file = tmp_path / "summary.md"
    step_summary = tmp_path / "step-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(step_summary))

    result = render_folder_workflow_summary.main(
        [
            "--artifact-root",
            str(artifact_root),
            "--output-file",
            str(output_file),
            "--write-step-summary",
        ]
    )

    assert result == 0
    assert output_file.exists()
    assert step_summary.exists()
    assert "def456" in output_file.read_text(encoding="utf-8")
