from __future__ import annotations

from pathlib import Path

import pytest

from python.helpers import folder_delivery_workflow, projects, schema_governance


def _valid_bundle() -> dict[str, dict]:
    return {
        "data_dictionary.json": {
            "policy": "additive_first",
            "states": ["proposed", "approved", "active", "deprecated", "removed"],
            "entities": [
                {
                    "name": "accounts",
                    "fields": [
                        {
                            "name": "account_id",
                            "type": "text",
                            "nullable": False,
                            "semantic_definition": "Primary account identifier",
                            "lifecycle_state": "active",
                        }
                    ],
                }
            ],
        },
        "schema_model.json": {"version": 1, "entities": [{"name": "accounts"}], "relationships": []},
        "schema_change_log.json": {"entries": [{"action": "add_column", "column": "account_id"}]},
        "migration_spec.json": {
            "strategy": "expand_contract",
            "changes": [{"action": "add_column", "column": "account_id"}],
            "rollback_policy": "forward_fix_unless_explicitly_reversible",
        },
    }


def test_validate_schema_bundle_accepts_additive_contract():
    assert schema_governance.validate_schema_bundle(_valid_bundle()) == []


def test_validate_schema_bundle_rejects_direct_rename():
    bundle = _valid_bundle()
    bundle["schema_change_log.json"] = {"entries": [{"action": "rename_column", "from": "old_name", "to": "new_name"}]}
    errors = schema_governance.validate_schema_bundle(bundle)
    assert errors
    assert "forbidden" in errors[0]


def test_apply_artifact_updates_rejects_invalid_schema_bundle():
    project_name = "schema_bundle_validation"
    projects.create_project(
        project_name,
        projects.BasicProjectData(
            title="Schema Bundle Validation",
            description="schema validation test",
            instructions="",
            color="#335577",
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
        folder_delivery_workflow.write_task_claims(
            project_name,
            run_context.run_id,
            [
                folder_delivery_workflow.TaskClaim(
                    task_id="integrate_results",
                    owner="agent_1",
                    write_globs=["usr/projects/**"],
                    owned_artifacts=list(folder_delivery_workflow.SCHEMA_GOVERNANCE_ARTIFACTS),
                )
            ],
        )

        artifact_root = Path(run_context.artifact_root)
        folder_delivery_workflow.initialize_run_artifacts(run_context)
        with pytest.raises(ValueError, match="forbidden"):
            folder_delivery_workflow.apply_artifact_updates(
                project_name=project_name,
                run_id=run_context.run_id,
                task_id="integrate_results",
                stage_family="planning",
                producer=folder_delivery_workflow.WORKFLOW_PROFILE_ID,
                assigned_to="agent_1",
                artifact_updates=[
                    {
                        "artifact_name": "data_dictionary.json",
                        "payload": _valid_bundle()["data_dictionary.json"],
                    },
                    {
                        "artifact_name": "schema_model.json",
                        "payload": _valid_bundle()["schema_model.json"],
                    },
                    {
                        "artifact_name": "schema_change_log.json",
                        "payload": {"entries": [{"action": "rename_column", "from": "old", "to": "new"}]},
                    },
                    {
                        "artifact_name": "migration_spec.json",
                        "payload": _valid_bundle()["migration_spec.json"],
                    },
                ],
            )
        assert artifact_root.exists()
    finally:
        projects.delete_project(project_name)
