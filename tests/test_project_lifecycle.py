from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from python.helpers import project_lifecycle, projects


def _new_project_name() -> str:
    return f"pl_{uuid4().hex[:10]}"


def _create_project(name: str) -> None:
    projects.create_project(
        name,
        projects.BasicProjectData(
            title=f"PL {name}",
            description="project lifecycle test",
            instructions="",
            color="#0055aa",
            memory="own",
            file_structure={
                "enabled": True,
                "max_depth": 2,
                "max_files": 10,
                "max_folders": 10,
                "max_lines": 100,
                "gitignore": "",
            },
        ),
    )


def test_lifecycle_defaults_and_set_phase_round_trip():
    project_name = _new_project_name()
    _create_project(project_name)
    try:
        lifecycle = project_lifecycle.load_lifecycle(project_name)
        assert lifecycle["lifecycle_model"] == "hybrid"
        assert lifecycle["current_phase"] == "design"
        assert "development" in lifecycle["phase_bindings"]

        updated = project_lifecycle.set_phase(project_name, "testing")
        assert updated["current_phase"] == "testing"

        reloaded = project_lifecycle.load_lifecycle(project_name)
        assert reloaded["current_phase"] == "testing"
    finally:
        projects.delete_project(project_name)


def test_run_phase_creates_run_record(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeManager:
        def __init__(self):
            self._created = False

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 7, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 7, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 99,
                "workflow_id": 7,
                "workflow_name": workflow_name,
                "status": "running",
            }

    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: FakeManager())
    monkeypatch.setattr(project_lifecycle, "_run_visual_validation_if_configured", lambda *args, **kwargs: None)

    try:
        run = project_lifecycle.run_phase(
            project_name,
            phase="design",
            options=project_lifecycle.PhaseRunOptions(run_visual=False, actor="system"),
        )
        assert run["status"] == "started"
        assert run["workflow"]["execution"]["execution_id"] == 99

        run_file = Path(projects.get_project_lifecycle_folder(project_name, "runs", f"{run['run_id']}.json"))
        assert run_file.exists()

        rows = project_lifecycle.list_phase_runs(project_name, phase="design", limit=10)
        assert rows
        assert rows[0]["phase"] == "design"
    finally:
        projects.delete_project(project_name)


def test_run_phase_requires_visual_suite_when_enabled(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeManager:
        def __init__(self):
            self._created = False

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 7, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 7, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 99,
                "workflow_id": 7,
                "workflow_name": workflow_name,
                "status": "running",
            }

    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: FakeManager())

    try:
        run = project_lifecycle.run_phase(
            project_name,
            phase="design",
            options=project_lifecycle.PhaseRunOptions(run_visual=True, actor="alice"),
        )
        assert run["status"] == "failed"
        assert "no visual_suite is configured" in str(run.get("error", "")).lower()
    finally:
        projects.delete_project(project_name)


def test_run_phase_uses_actor_bound_browser_profile(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeManager:
        def __init__(self):
            self._created = False

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 7, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 7, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 99,
                "workflow_id": 7,
                "workflow_name": workflow_name,
                "status": "running",
            }

    captured: dict[str, str] = {}

    def fake_run_suite(project_name: str, suite_name: str, options):
        captured["profile_name"] = options.profile_name or ""
        captured["suite_name"] = suite_name
        return {"status": "passed", "run_id": "vr_test"}

    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: FakeManager())
    monkeypatch.setattr(project_lifecycle.project_validation, "run_suite", fake_run_suite)

    try:
        project_lifecycle.upsert_lifecycle(
            project_name,
            {
                "phase_bindings": {
                    "design": {
                        "visual_suite": "google-auth-smoke",
                    }
                },
                "browser": {
                    "profile_name": "fallback-profile",
                    "profiles": {"alice": "alice-google-profile"},
                },
            },
        )
        run = project_lifecycle.run_phase(
            project_name,
            phase="design",
            options=project_lifecycle.PhaseRunOptions(run_visual=True, actor="alice"),
        )
        assert run["status"] == "started"
        assert captured["suite_name"] == "google-auth-smoke"
        assert captured["profile_name"] == "alice-google-profile"
    finally:
        projects.delete_project(project_name)


def test_run_phase_records_failed_visual_validation(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeManager:
        def __init__(self):
            self._created = False

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 7, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 7, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 99,
                "workflow_id": 7,
                "workflow_name": workflow_name,
                "status": "running",
            }

    def fake_run_suite(*args, **kwargs):
        raise Exception("mock visual failure")

    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: FakeManager())
    monkeypatch.setattr(project_lifecycle.project_validation, "run_suite", fake_run_suite)

    try:
        project_lifecycle.upsert_lifecycle(
            project_name,
            {
                "phase_bindings": {
                    "design": {
                        "visual_suite": "google-auth-smoke",
                    }
                },
                "browser": {
                    "profile_name": "fallback-profile",
                },
            },
        )
        run = project_lifecycle.run_phase(
            project_name,
            phase="design",
            options=project_lifecycle.PhaseRunOptions(run_visual=True, actor="alice"),
        )

        assert run["status"] == "failed"
        assert "mock visual failure" in str(run.get("error", ""))

        rows = project_lifecycle.list_phase_runs(project_name, phase="design", limit=10)
        assert rows
        assert rows[0]["run_id"] == run["run_id"]
        assert rows[0]["status"] == "failed"
    finally:
        projects.delete_project(project_name)


def test_start_folder_workflow_creates_run_and_allows_gate_and_finalize(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeManager:
        def __init__(self):
            self._created = False
            self.approved: list[tuple[int, str, str]] = []

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 77, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 77, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 123,
                "workflow_id": 77,
                "workflow_name": workflow_name,
                "status": "running",
                "context": context,
            }

        def approve_stage(self, execution_id, stage_id, approved_by, notes=None):
            self.approved.append((execution_id, stage_id, approved_by))
            return {"status": "approved"}

    fake_manager = FakeManager()
    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: fake_manager)

    try:
        run = project_lifecycle.start_folder_workflow(
            project_name=project_name,
            target_path="python/helpers",
            actor="alice",
            scope={"include": ["python/helpers"]},
            constraints={"no_destructive_migrations": True},
            branch_ref="feat/test",
            max_parallelism=2,
        )
        assert run["workflow_profile"] == "folder_evaluation_delivery_v1"
        assert Path(run["artifacts"]["definition_of_done.json"]).exists()

        decision = project_lifecycle.approve_folder_gate(
            project_name=project_name,
            run_id=run["run_id"],
            gate_name="planning_to_execution",
            approved_by="alice",
            evidence_refs=["artifacts/definition_of_done.json"],
        )
        assert decision["approved"] is True
        assert fake_manager.approved == [(123, "planning", "alice")]

        finalized = project_lifecycle.finalize_folder_workflow(
            project_name=project_name,
            run_id=run["run_id"],
            actor="alice",
            status="completed",
        )
        assert finalized["status"] == "completed"
    finally:
        projects.delete_project(project_name)


def test_folder_release_artifacts_are_built_and_post_deploy_is_recorded(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeManager:
        def __init__(self):
            self._created = False
            self.approved: list[tuple[int, str, str]] = []

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 88, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 88, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 456,
                "workflow_id": 88,
                "workflow_name": workflow_name,
                "status": "running",
                "context": context,
            }

        def approve_stage(self, execution_id, stage_id, approved_by, notes=None):
            self.approved.append((execution_id, stage_id, approved_by))
            return {"status": "approved"}

    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: FakeManager())

    try:
        run = project_lifecycle.start_folder_workflow(
            project_name=project_name,
            target_path="python/helpers",
            actor="alice",
            branch_ref="feat/test",
        )
        bundle = project_lifecycle.build_folder_release_bundle(
            project_name=project_name,
            run_id=run["run_id"],
            actor="alice",
            commit_sha="6b5002cc",
            pr_number="4",
            linear_issue_keys=["AJB-123"],
            deploy_target="staging",
            pre_deploy_checks={
                "artifact_manifest_verified": True,
                "config_validated": True,
                "secrets_present": True,
                "dependency_reachability": True,
                "migration_compatibility": True,
                "environment_lock": True,
                "backup_confirmed": True,
            },
            post_deploy_checks={
                "health_endpoint": False,
                "chat_readiness": False,
                "workflow_smoke": False,
                "schema_verification": False,
                "monitoring_snapshot": False,
            },
            monitoring_snapshot={"status": "green", "observed_at": "2026-03-25T00:00:00+00:00"},
            rollback_plan={"strategy": "forward_fix", "owner": "ops", "trigger_conditions": ["health red"]},
        )
        assert bundle["workflow_execution"]["execution_id"] == 456
        assert bundle["artifact_manifest"]

        readiness = project_lifecycle.validate_folder_release_readiness(
            project_name=project_name,
            run_id=run["run_id"],
            actor="alice",
            required_observers=["engineering", "operations"],
        )
        assert readiness["ready"] is True
        assert readiness["blocking_checks"] == []

        gate = project_lifecycle.approve_folder_gate(
            project_name=project_name,
            run_id=run["run_id"],
            gate_name="release_to_deploy",
            approved_by="alice",
            evidence_refs=["artifacts/release_bundle.json", "artifacts/release_readiness.json"],
        )
        assert gate["approved"] is True

        post_deploy = project_lifecycle.record_folder_post_deploy(
            project_name=project_name,
            run_id=run["run_id"],
            actor="alice",
            checks={
                "health_endpoint": True,
                "chat_readiness": True,
                "workflow_smoke": True,
                "schema_verification": True,
                "monitoring_snapshot": True,
            },
            status="healthy",
            rollback_triggered=False,
            observation_window={
                "started_at": "2026-03-25T01:00:00+00:00",
                "duration_minutes": 30,
                "decision": "hold",
            },
            monitoring_snapshot={"status": "healthy", "observed_at": "2026-03-25T01:30:00+00:00"},
        )
        assert post_deploy["status"] == "healthy"

        release_bundle = project_lifecycle.folder_delivery_workflow.load_artifact_payload(
            project_name, run["run_id"], "release_bundle.json"
        )
        assert any(item.get("gate_name") == "release_to_deploy" for item in release_bundle["approvals"])
        assert release_bundle["post_deploy_checks"]["health_endpoint"] is True
    finally:
        projects.delete_project(project_name)


def test_sync_folder_linear_plan_creates_linear_artifacts(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeWorkflowManager:
        def __init__(self):
            self._created = False

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 77, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 77, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 222,
                "workflow_id": 77,
                "workflow_name": workflow_name,
                "status": "running",
                "context": context,
            }

    class FakeLinearManager:
        async def create_issue_batch(
            self,
            issues,
            team_id,
            default_priority=0,
            project_id=None,
            state_id=None,
            label_ids=None,
        ):
            created = []
            for index, issue in enumerate(issues, start=1):
                created.append(
                    {
                        "id": f"issue-{index}",
                        "identifier": f"AJB-{120 + index}",
                        "title": issue["title"],
                        "url": f"https://linear.app/test/issue/AJB-{120 + index}",
                        "priority": default_priority,
                        "state": {"name": "Todo"},
                    }
                )
            return {"success": True, "issues": created, "failures": []}

    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: FakeWorkflowManager())
    monkeypatch.setattr(project_lifecycle, "_get_linear_manager", lambda: FakeLinearManager())
    monkeypatch.setattr(project_lifecycle, "_get_linear_team_id", lambda: "team-1")

    try:
        run = project_lifecycle.start_folder_workflow(
            project_name=project_name,
            target_path="python/helpers",
            actor="alice",
        )
        project_lifecycle.folder_delivery_workflow.write_system_artifact(
            project_name=project_name,
            run_id=run["run_id"],
            artifact_name="execution_plan.json",
            payload={
                "task_slices": [
                    {"title": "Slice A", "description": "Implement A"},
                    {"title": "Slice B", "description": "Implement B"},
                ],
                "integrator": "agent_1",
                "approvals_required": ["planning_to_execution", "release_to_deploy"],
            },
            stage_family="planning",
            producer="test",
        )

        linear_plan = project_lifecycle.sync_folder_linear_plan(
            project_name=project_name,
            run_id=run["run_id"],
            actor="alice",
        )
        assert linear_plan["created_count"] == 3
        assert linear_plan["parent_issue"]["identifier"] == "AJB-121"
        assert len(linear_plan["child_issues"]) == 2

        release_bundle = project_lifecycle.folder_delivery_workflow.load_artifact_payload(
            project_name, run["run_id"], "release_bundle.json"
        )
        assert release_bundle["linear_issue_keys"] == ["AJB-121", "AJB-122", "AJB-123"]
        assert release_bundle["linear_plan"]["child_issue_count"] == 2
    finally:
        projects.delete_project(project_name)


def test_record_folder_deploy_run_updates_release_bundle(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeManager:
        def __init__(self):
            self._created = False
            self.approved: list[tuple[int, str, str]] = []

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 91, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 91, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 654,
                "workflow_id": 91,
                "workflow_name": workflow_name,
                "status": "running",
                "context": context,
            }

        def approve_stage(self, execution_id, stage_id, approved_by, notes=None):
            self.approved.append((execution_id, stage_id, approved_by))
            return {"status": "approved"}

    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: FakeManager())

    try:
        run = project_lifecycle.start_folder_workflow(
            project_name=project_name,
            target_path="python/helpers",
            actor="alice",
            branch_ref="feat/test",
        )
        project_lifecycle.build_folder_release_bundle(
            project_name=project_name,
            run_id=run["run_id"],
            actor="alice",
            commit_sha="44f0c41c",
            pr_number="4",
            linear_issue_keys=["AJB-123"],
            deploy_target="staging",
            pre_deploy_checks={
                "artifact_manifest_verified": True,
                "config_validated": True,
                "secrets_present": True,
                "dependency_reachability": True,
                "migration_compatibility": True,
                "environment_lock": True,
                "backup_confirmed": True,
            },
            post_deploy_checks={
                "health_endpoint": False,
                "chat_readiness": False,
                "workflow_smoke": False,
                "schema_verification": False,
                "monitoring_snapshot": False,
            },
            monitoring_snapshot={"status": "green", "observed_at": "2026-03-25T00:00:00+00:00"},
            rollback_plan={"strategy": "forward_fix", "owner": "ops", "trigger_conditions": ["health red"]},
        )
        project_lifecycle.validate_folder_release_readiness(
            project_name=project_name,
            run_id=run["run_id"],
            actor="alice",
            required_observers=["engineering", "operations"],
        )
        project_lifecycle.approve_folder_gate(
            project_name=project_name,
            run_id=run["run_id"],
            gate_name="release_to_deploy",
            approved_by="alice",
            evidence_refs=["artifacts/release_bundle.json"],
        )

        deploy_run = project_lifecycle.record_folder_deploy_run(
            project_name=project_name,
            run_id=run["run_id"],
            actor="alice",
            deployment_system="github_actions",
            repository="mahoosuc-solutions/agent-mahoo",
            workflow_file="deploy.yml",
            workflow_run_id="123456789",
            build_id="build-42",
            environment="staging",
            status="in_progress",
            deployment_url="https://github.com/mahoosuc-solutions/agent-mahoo/actions/runs/123456789",
            started_at="2026-03-25T02:00:00+00:00",
            commit_sha="44f0c41c",
            pr_number="4",
        )
        assert deploy_run["workflow_run_id"] == "123456789"

        release_bundle = project_lifecycle.folder_delivery_workflow.load_artifact_payload(
            project_name, run["run_id"], "release_bundle.json"
        )
        assert release_bundle["deployment_reference"]["build_id"] == "build-42"
        assert release_bundle["deployment_reference"]["workflow_run_id"] == "123456789"
        assert release_bundle["commit_sha"] == "44f0c41c"
        assert release_bundle["pr_number"] == "4"
    finally:
        projects.delete_project(project_name)


def test_run_phase_rejects_when_lock_exists(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)
    try:
        lock_file = Path(projects.get_project_lifecycle_folder(project_name, "run.lock"))
        lock_file.write_text('{"pid":1,"started_at":"2099-01-01T00:00:00+00:00"}\n', encoding="utf-8")

        raised = False
        try:
            project_lifecycle.run_phase(
                project_name,
                phase="design",
                options=project_lifecycle.PhaseRunOptions(run_visual=False, actor="system"),
            )
        except Exception as exc:
            raised = True
            assert "already in progress" in str(exc).lower()
        assert raised is True
    finally:
        projects.delete_project(project_name)


def test_run_retention_keeps_newest_runs(monkeypatch):
    project_name = _new_project_name()
    _create_project(project_name)

    class FakeManager:
        def __init__(self):
            self._created = False

        def get_workflow(self, name=None, workflow_id=None):
            if self._created:
                return {"workflow_id": 7, "name": name}
            return {"error": "Workflow not found"}

        def create_from_template(self, template_path, name, customizations=None):
            self._created = True
            return {"workflow_id": 7, "name": name, "status": "created"}

        def start_workflow(self, workflow_id=None, workflow_name=None, execution_name=None, context=None):
            return {
                "execution_id": 99,
                "workflow_id": 7,
                "workflow_name": workflow_name,
                "status": "running",
            }

    monkeypatch.setattr(project_lifecycle, "_get_workflow_manager", lambda: FakeManager())
    monkeypatch.setattr(project_lifecycle, "_run_visual_validation_if_configured", lambda *args, **kwargs: None)

    try:
        project_lifecycle.upsert_lifecycle(project_name, {"retention": {"max_runs": 2}})
        first = project_lifecycle.run_phase(
            project_name,
            phase="design",
            options=project_lifecycle.PhaseRunOptions(run_visual=False, actor="system"),
        )
        second = project_lifecycle.run_phase(
            project_name,
            phase="design",
            options=project_lifecycle.PhaseRunOptions(run_visual=False, actor="system"),
        )
        third = project_lifecycle.run_phase(
            project_name,
            phase="design",
            options=project_lifecycle.PhaseRunOptions(run_visual=False, actor="system"),
        )

        rows = project_lifecycle.list_phase_runs(project_name, phase="design", limit=10)
        ids = {row["run_id"] for row in rows}
        assert len(rows) == 2
        assert first["run_id"] not in ids
        assert second["run_id"] in ids
        assert third["run_id"] in ids
        assert "duration_ms" in rows[0]
        assert "finished_at" in rows[0]
    finally:
        projects.delete_project(project_name)
