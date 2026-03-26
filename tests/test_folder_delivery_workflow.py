from __future__ import annotations

import importlib.util
from pathlib import Path

from python.helpers import folder_delivery_workflow, projects


def _load_traceability_module():
    module_path = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "check_traceability.py"
    spec = importlib.util.spec_from_file_location("check_traceability", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_validate_task_claims_rejects_overlapping_write_scopes():
    claims = [
        folder_delivery_workflow.TaskClaim(
            task_id="slice_a",
            owner="architect",
            write_globs=["python/helpers/*.py"],
        ),
        folder_delivery_workflow.TaskClaim(
            task_id="slice_b",
            owner="developer",
            write_globs=["python/helpers/project_*.py"],
        ),
    ]

    errors = folder_delivery_workflow.validate_task_claims(claims)
    assert errors
    assert "overlap" in errors[0].lower()


def test_initialize_run_artifacts_creates_schema_governance_bundle():
    project_name = "fdw_artifacts"
    projects.create_project(
        project_name,
        projects.BasicProjectData(
            title="FDW",
            description="folder workflow test",
            instructions="",
            color="#004488",
            memory="own",
            file_structure={
                "enabled": True,
                "max_depth": 1,
                "max_files": 5,
                "max_folders": 5,
                "max_lines": 50,
                "gitignore": "",
            },
        ),
    )

    try:
        run_context = folder_delivery_workflow.create_run_context(
            project_name=project_name,
            target_path="python/helpers",
        )
        folder_delivery_workflow.acquire_target_lock(project_name, run_context)
        artifacts = folder_delivery_workflow.initialize_run_artifacts(run_context)

        for artifact_name in folder_delivery_workflow.SCHEMA_GOVERNANCE_ARTIFACTS:
            artifact_path = Path(artifacts[artifact_name])
            assert artifact_path.exists()
            payload = artifact_path.read_text(encoding="utf-8")
            assert run_context.run_id in payload

        folder_delivery_workflow.release_target_lock(project_name, run_context.target_id, run_context.run_id)
        assert not folder_delivery_workflow.get_target_lock_path(project_name, run_context.target_id).exists()
    finally:
        projects.delete_project(project_name)


def test_traceability_validator_requires_linear_and_github_fields():
    module = _load_traceability_module()

    errors = module.validate_pr_body("## Description\nMissing fields")
    assert len(errors) == 2

    valid_body = """
## Description
Traceability fields populated.

Linear issue: AJB-42
GitHub issue/PR: #123
"""
    assert module.validate_pr_body(valid_body) == []
