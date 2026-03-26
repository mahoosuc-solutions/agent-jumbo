from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "update_folder_workflow_evidence.py"
SPEC = importlib.util.spec_from_file_location("update_folder_workflow_evidence", MODULE_PATH)
assert SPEC and SPEC.loader
update_folder_workflow_evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update_folder_workflow_evidence)


def _write_run_record(artifact_root: Path, project_name: str, run_id: str) -> None:
    run_root = artifact_root.parent
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "run_record.json").write_text(
        json.dumps({"project_name": project_name, "run_id": run_id}, indent=2) + "\n",
        encoding="utf-8",
    )
    (artifact_root / "release_bundle.json").write_text(json.dumps({"payload": {}}, indent=2) + "\n", encoding="utf-8")


def test_update_folder_workflow_evidence_ci_mode(monkeypatch, tmp_path):
    artifact_root = tmp_path / "fdw_123" / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    _write_run_record(artifact_root, "demo_project", "fdw_123")
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"pull_request": {"number": 17}}), encoding="utf-8")

    calls: dict[str, object] = {}

    def fake_sync_folder_linear_plan(**kwargs):
        calls["linear"] = kwargs
        return {"created_count": 2, "parent_issue": {"identifier": "AJB-200"}}

    def fake_build_folder_release_bundle(**kwargs):
        calls["bundle"] = kwargs
        return {
            "commit_sha": kwargs["commit_sha"],
            "pr_number": kwargs["pr_number"],
            "deploy_target": kwargs["deploy_target"],
        }

    monkeypatch.setenv("LINEAR_API_KEY", "test-key")
    monkeypatch.setenv("GITHUB_SHA", "abc123")
    monkeypatch.setattr(
        update_folder_workflow_evidence.project_lifecycle, "sync_folder_linear_plan", fake_sync_folder_linear_plan
    )
    monkeypatch.setattr(
        update_folder_workflow_evidence.project_lifecycle,
        "build_folder_release_bundle",
        fake_build_folder_release_bundle,
    )

    result = update_folder_workflow_evidence.main(
        [
            "--artifact-root",
            str(artifact_root),
            "--event-path",
            str(event_path),
            "--mode",
            "ci",
            "--sync-linear",
            "--environment",
            "staging",
        ]
    )

    assert result == 0
    assert calls["linear"]["project_name"] == "demo_project"
    assert calls["bundle"]["pr_number"] == "17"
    assert calls["bundle"]["commit_sha"] == "abc123"
    assert calls["bundle"]["deploy_target"] == "staging"


def test_update_folder_workflow_evidence_deploy_mode(monkeypatch, tmp_path):
    artifact_root = tmp_path / "fdw_456" / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=True)
    _write_run_record(artifact_root, "demo_project", "fdw_456")

    calls: dict[str, object] = {}

    def fake_record_folder_deploy_run(**kwargs):
        calls["deploy"] = kwargs
        return {
            "workflow_run_id": kwargs["workflow_run_id"],
            "build_id": kwargs["build_id"],
            "status": kwargs["status"],
            "environment": kwargs["environment"],
        }

    monkeypatch.setenv("GITHUB_SHA", "def456")
    monkeypatch.setenv("GITHUB_RUN_ID", "999")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "3")
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_WORKFLOW", "Web Deploy")
    monkeypatch.setattr(
        update_folder_workflow_evidence.project_lifecycle,
        "record_folder_deploy_run",
        fake_record_folder_deploy_run,
    )

    result = update_folder_workflow_evidence.main(
        [
            "--artifact-root",
            str(artifact_root),
            "--mode",
            "deploy",
            "--environment",
            "production",
            "--status",
            "success",
        ]
    )

    assert result == 0
    assert calls["deploy"]["workflow_run_id"] == "999"
    assert calls["deploy"]["build_id"] == "3"
    assert calls["deploy"]["environment"] == "production"
    assert calls["deploy"]["status"] == "success"


def test_update_folder_workflow_evidence_skips_without_roots(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(update_folder_workflow_evidence, "REPO_ROOT", tmp_path)
    result = update_folder_workflow_evidence.main([])
    captured = capsys.readouterr()
    assert result == 0
    assert "skipped" in captured.out.lower()
