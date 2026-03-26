from __future__ import annotations

import pytest

from python.helpers import folder_delivery_workflow, projects, release_governance


def _valid_release_bundle() -> dict:
    return {
        "commit_sha": "14effb5b",
        "pr_number": "4",
        "linear_issue_keys": ["AJB-123"],
        "artifact_manifest": ["definition_of_done.json", "release_readiness.json"],
        "approvals": [{"gate": "release_to_deploy", "approved_by": "ops"}],
        "deploy_target": "staging",
        "pre_deploy_checks": {
            "artifact_manifest_verified": True,
            "config_validated": True,
            "secrets_present": True,
            "dependency_reachability": True,
            "migration_compatibility": True,
            "environment_lock": True,
            "backup_confirmed": True,
        },
        "post_deploy_checks": {
            "health_endpoint": True,
            "chat_readiness": True,
            "workflow_smoke": True,
            "schema_verification": True,
            "monitoring_snapshot": True,
        },
        "monitoring_snapshot": {"status": "healthy", "observed_at": "2026-03-25T00:00:00+00:00"},
        "rollback_plan": {"strategy": "forward_fix", "owner": "ops", "trigger_conditions": ["health red"]},
    }


def test_validate_release_bundle_accepts_complete_payload():
    assert release_governance.validate_release_bundle(_valid_release_bundle()) == []


def test_placeholder_release_bundle_does_not_trigger_validation():
    bundle = {
        "commit_sha": "",
        "pr_number": "",
        "linear_issue_keys": [],
        "artifact_manifest": [],
        "approvals": [],
        "deploy_target": "",
        "pre_deploy_checks": {
            "artifact_manifest_verified": False,
            "config_validated": False,
            "secrets_present": False,
            "dependency_reachability": False,
            "migration_compatibility": False,
            "environment_lock": False,
            "backup_confirmed": False,
        },
        "post_deploy_checks": {
            "health_endpoint": False,
            "chat_readiness": False,
            "workflow_smoke": False,
            "schema_verification": False,
            "monitoring_snapshot": False,
        },
        "monitoring_snapshot": {"status": "", "observed_at": ""},
        "rollback_plan": {"strategy": "", "owner": "", "trigger_conditions": []},
    }
    assert release_governance.should_validate_release_bundle(bundle) is False


def test_validate_release_bundle_rejects_failed_predeploy_checks():
    bundle = _valid_release_bundle()
    bundle["pre_deploy_checks"]["backup_confirmed"] = False
    errors = release_governance.validate_release_bundle(bundle)
    assert errors
    assert "must all pass" in errors[0]


def test_placeholder_post_deploy_report_does_not_trigger_validation():
    report = {
        "status": "degraded",
        "observation_window": {"started_at": "", "duration_minutes": 0, "decision": ""},
        "rollback_triggered": False,
        "checks": {
            "health_endpoint": False,
            "chat_readiness": False,
            "workflow_smoke": False,
            "schema_verification": False,
            "monitoring_snapshot": False,
        },
    }
    assert release_governance.should_validate_post_deploy_report(report) is False


def test_apply_artifact_updates_rejects_invalid_release_bundle():
    project_name = "release_bundle_validation"
    projects.create_project(
        project_name,
        projects.BasicProjectData(
            title="Release Bundle Validation",
            description="release validation test",
            instructions="",
            color="#225588",
            memory="own",
            file_structure={
                "enabled": True,
                "max_depth": 1,
                "max_files": 10,
                "max_folders": 10,
                "max_lines": 50,
                "gitignore": "",
            },
        ),
    )

    try:
        run_context = folder_delivery_workflow.create_run_context(project_name=project_name, target_path="python")
        folder_delivery_workflow.initialize_run_artifacts(run_context)
        folder_delivery_workflow.write_task_claims(
            project_name,
            run_context.run_id,
            [
                folder_delivery_workflow.TaskClaim(
                    task_id="integrate_results",
                    owner="agent_1",
                    write_globs=["usr/projects/**"],
                    owned_artifacts=["release_bundle.json", "release_readiness.json"],
                )
            ],
        )

        with pytest.raises(ValueError, match="pre_deploy_checks must all pass"):
            folder_delivery_workflow.apply_artifact_updates(
                project_name=project_name,
                run_id=run_context.run_id,
                task_id="integrate_results",
                stage_family="release_decision",
                producer=folder_delivery_workflow.WORKFLOW_PROFILE_ID,
                assigned_to="agent_1",
                artifact_updates=[
                    {
                        "artifact_name": "release_bundle.json",
                        "payload": _valid_release_bundle()
                        | {
                            "pre_deploy_checks": {
                                "artifact_manifest_verified": True,
                                "config_validated": True,
                                "secrets_present": True,
                                "dependency_reachability": True,
                                "migration_compatibility": True,
                                "environment_lock": True,
                                "backup_confirmed": False,
                            }
                        },
                    },
                    {
                        "artifact_name": "release_readiness.json",
                        "payload": {"ready": True, "blocking_checks": [], "required_observers": ["engineering"]},
                    },
                ],
            )
    finally:
        projects.delete_project(project_name)


def test_apply_artifact_updates_allows_unrelated_canonical_updates_with_release_scaffold():
    project_name = "release_bundle_scaffold"
    projects.create_project(
        project_name,
        projects.BasicProjectData(
            title="Release Bundle Scaffold",
            description="release scaffold test",
            instructions="",
            color="#225588",
            memory="own",
            file_structure={
                "enabled": True,
                "max_depth": 1,
                "max_files": 10,
                "max_folders": 10,
                "max_lines": 50,
                "gitignore": "",
            },
        ),
    )

    try:
        run_context = folder_delivery_workflow.create_run_context(project_name=project_name, target_path="python")
        folder_delivery_workflow.initialize_run_artifacts(run_context)
        folder_delivery_workflow.write_task_claims(
            project_name,
            run_context.run_id,
            [
                folder_delivery_workflow.TaskClaim(
                    task_id="integrate_results",
                    owner="agent_1",
                    write_globs=["usr/projects/**"],
                    owned_artifacts=["definition_of_done.json"],
                )
            ],
        )

        result = folder_delivery_workflow.apply_artifact_updates(
            project_name=project_name,
            run_id=run_context.run_id,
            task_id="integrate_results",
            stage_family="planning",
            producer=folder_delivery_workflow.WORKFLOW_PROFILE_ID,
            assigned_to="agent_1",
            artifact_updates=[
                {
                    "artifact_name": "definition_of_done.json",
                    "payload": {
                        "functional_requirements": ["inventory folder"],
                        "tests_required": ["unit"],
                        "quality_gates": ["ci"],
                        "security_requirements": [],
                        "observability_requirements": [],
                        "rollback_requirements": [],
                        "release_evidence": [],
                    },
                }
            ],
        )

        assert result["updated"]
    finally:
        projects.delete_project(project_name)
