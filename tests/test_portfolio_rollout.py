from __future__ import annotations

import json
from pathlib import Path

from instruments.custom.portfolio_manager.portfolio_db import PortfolioDatabase
from python.helpers import portfolio_rollout, projects


def _write_catalog(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "products": [
                    {
                        "slug": "alpha",
                        "name": "Alpha",
                        "description": "Alpha product",
                        "audience": "builder",
                        "repos": ["alpha-repo"],
                        "integrations": ["GitHub"],
                        "instruments": ["workflow_engine"],
                        "tools": ["project_lifecycle"],
                    },
                    {
                        "slug": "beta",
                        "name": "Beta",
                        "description": "Beta product",
                        "audience": "business",
                        "repos": ["missing-repo"],
                        "integrations": ["Linear"],
                        "instruments": [],
                        "tools": [],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )


def _fake_folder_run(monkeypatch):
    def fake_start_folder_workflow(project_name: str, target_path: str, **kwargs):
        run_context = portfolio_rollout.folder_delivery_workflow.create_run_context(
            project_name=project_name,
            target_path=target_path,
            actor="tester",
            branch_ref=kwargs.get("branch_ref", "feature/test"),
        )
        portfolio_rollout.folder_delivery_workflow.initialize_run_artifacts(run_context)
        portfolio_rollout.project_lifecycle.upsert_lifecycle(
            project_name,
            {
                "active_workflow_run": {
                    "run_id": run_context.run_id,
                    "workflow_profile": portfolio_rollout.folder_delivery_workflow.WORKFLOW_PROFILE_ID,
                    "target_id": run_context.target_id,
                    "target_path": run_context.target_path,
                    "status": "started",
                    "started_at": run_context.created_at,
                },
                "last_run": {
                    "run_id": run_context.run_id,
                    "phase": "folder_delivery",
                    "status": "started",
                    "started_at": run_context.created_at,
                    "finished_at": None,
                    "duration_ms": 0,
                },
            },
            actor="tester",
        )
        run_root = portfolio_rollout.folder_delivery_workflow.get_run_root(project_name, run_context.run_id)
        run_root.mkdir(parents=True, exist_ok=True)
        run_record = {
            "run_id": run_context.run_id,
            "project_name": project_name,
            "stage_family": "planning",
            "status": "started",
            "workflow": {"execution": {"execution_id": 101}},
        }
        (run_root / "run_record.json").write_text(json.dumps(run_record), encoding="utf-8")
        runs_dir = Path(projects.get_project_lifecycle_folder(project_name, "runs"))
        runs_dir.mkdir(parents=True, exist_ok=True)
        (runs_dir / f"{run_context.run_id}.json").write_text(json.dumps(run_record), encoding="utf-8")
        return {"run_id": run_context.run_id}

    monkeypatch.setattr(portfolio_rollout.project_lifecycle, "start_folder_workflow", fake_start_folder_workflow)
    monkeypatch.setattr(
        portfolio_rollout.project_lifecycle,
        "approve_folder_gate",
        lambda **kwargs: {"approved": True, "gate_name": kwargs.get("gate_name", "")},
    )


class _ImmediateThread:
    def __init__(self, target=None, kwargs=None, **_extras):
        self._target = target
        self._kwargs = kwargs or {}

    def start(self):
        if self._target:
            self._target(**self._kwargs)


def _mock_rollout_provider_ready(monkeypatch):
    monkeypatch.setattr(
        portfolio_rollout.rollout_agent_jobs.provider_readiness,
        "check_backend_readiness",
        lambda **kwargs: {
            "backend": kwargs.get("backend", ""),
            "provider": kwargs.get("provider", ""),
            "runtime_scope": kwargs.get("runtime_scope", "host"),
            "current_runtime_scope": kwargs.get("runtime_scope", "host"),
            "ready": True,
            "status": "ready",
            "checks": [{"id": "smoke", "ok": True, "detail": "ready"}],
            "fix_hint": "",
            "runtime": kwargs.get("backend", ""),
        },
    )
    monkeypatch.setattr(
        portfolio_rollout.provider_readiness,
        "check_backend_readiness",
        lambda **kwargs: {
            "backend": kwargs.get("backend", ""),
            "provider": kwargs.get("provider", ""),
            "runtime_scope": kwargs.get("runtime_scope", "host"),
            "current_runtime_scope": kwargs.get("runtime_scope", "host"),
            "ready": True,
            "status": "ready",
            "checks": [{"id": "smoke", "ok": True, "detail": "ready"}],
            "fix_hint": "",
            "runtime": kwargs.get("backend", ""),
        },
    )
    monkeypatch.setattr(portfolio_rollout.provider_readiness, "current_runtime_scope", lambda: "host")
    monkeypatch.setattr(portfolio_rollout.provider_readiness, "available_runtime_scopes", lambda: ["host", "container"])


def test_seed_catalog_portfolio_creates_managed_units(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    (repos_dir / "alpha-repo").mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    payload = portfolio_rollout.seed_catalog_portfolio(
        actor="tester",
        catalog_path=str(catalog_path),
        db=db,
    )

    assert payload["catalog_count"] == 2
    assert payload["summary"]["resolved_targets"] == 1
    assert payload["summary"]["blocked_products"] == 1

    units = {unit["slug"]: unit for unit in payload["units"]}
    assert units["alpha"]["status"] == "seeded"
    assert units["alpha"]["target_path"] == str((repos_dir / "alpha-repo").resolve())
    assert units["beta"]["status"] == "definition_blocked"
    assert "No local repo path resolved" in units["beta"]["blocked_reason"]

    lifecycle_path = Path(projects.get_project_lifecycle_folder("portfolio-alpha", "lifecycle.json"))
    assert lifecycle_path.exists()
    project_record = db.get_project_by_path(projects.get_project_folder("portfolio-alpha"))
    assert project_record is not None
    assert db.get_metadata(int(project_record["id"]))["product_slug"] == "alpha"


def test_start_definition_wave_only_starts_resolved_products(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)

    started_calls: list[tuple[str, str]] = []

    def fake_start_folder_workflow(project_name: str, target_path: str, **kwargs):
        started_calls.append((project_name, target_path))
        return {"run_id": f"run-{project_name}"}

    monkeypatch.setattr(portfolio_rollout.project_lifecycle, "start_folder_workflow", fake_start_folder_workflow)

    payload = portfolio_rollout.start_definition_wave(
        actor="tester",
        catalog_path=str(catalog_path),
        db=db,
    )

    assert payload["summary"] == {"started": 1, "skipped": 0, "blocked": 1}
    assert started_calls == [("portfolio-alpha", str(alpha_repo.resolve()))]
    assert payload["started"][0]["run_id"] == "run-portfolio-alpha"
    assert payload["blocked"][0]["slug"] == "beta"


def test_rollout_dashboard_does_not_treat_placeholder_artifacts_as_complete(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)

    def fake_start_folder_workflow(project_name: str, target_path: str, **kwargs):
        run_context = portfolio_rollout.folder_delivery_workflow.create_run_context(
            project_name=project_name,
            target_path=target_path,
            actor="tester",
            branch_ref="feature/test",
        )
        portfolio_rollout.folder_delivery_workflow.initialize_run_artifacts(run_context)
        portfolio_rollout.project_lifecycle.upsert_lifecycle(
            project_name,
            {
                "active_workflow_run": {
                    "run_id": run_context.run_id,
                    "workflow_profile": portfolio_rollout.folder_delivery_workflow.WORKFLOW_PROFILE_ID,
                    "target_id": run_context.target_id,
                    "target_path": run_context.target_path,
                    "status": "started",
                    "started_at": run_context.created_at,
                },
                "last_run": {
                    "run_id": run_context.run_id,
                    "phase": "folder_delivery",
                    "status": "started",
                    "started_at": run_context.created_at,
                    "finished_at": None,
                    "duration_ms": 0,
                },
            },
            actor="tester",
        )
        run_root = portfolio_rollout.folder_delivery_workflow.get_run_root(project_name, run_context.run_id)
        run_root.mkdir(parents=True, exist_ok=True)
        run_record = {
            "run_id": run_context.run_id,
            "project_name": project_name,
            "stage_family": "planning",
            "status": "started",
        }
        (run_root / "run_record.json").write_text(json.dumps(run_record), encoding="utf-8")
        runs_dir = Path(projects.get_project_lifecycle_folder(project_name, "runs"))
        runs_dir.mkdir(parents=True, exist_ok=True)
        (runs_dir / f"{run_context.run_id}.json").write_text(json.dumps(run_record), encoding="utf-8")
        return {"run_id": run_context.run_id}

    monkeypatch.setattr(portfolio_rollout.project_lifecycle, "start_folder_workflow", fake_start_folder_workflow)

    portfolio_rollout.start_definition_wave(actor="tester", catalog_path=str(catalog_path), db=db)
    dashboard = portfolio_rollout.get_rollout_dashboard(catalog_path=str(catalog_path), db=db)
    units = {unit["slug"]: unit for unit in dashboard["products"]}

    assert units["alpha"]["status"] == "planning"
    assert units["alpha"]["planning_artifacts"]["complete"] is False


def test_product_workspace_allows_target_override_for_blocked_product(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    override_repo = repos_dir / "override-repo"
    override_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _mock_rollout_provider_ready(monkeypatch)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.set_product_target(
        "beta",
        str(override_repo),
        actor="tester",
        catalog_path=str(catalog_path),
        db=db,
    )

    assert workspace["unit"]["target_path"] == str(override_repo.resolve())
    assert workspace["unit"]["status"] == "seeded"


def test_draft_and_approve_planning_bundle_requires_real_artifacts(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    (alpha_repo / "README.md").write_text("# Alpha\n", encoding="utf-8")
    (alpha_repo / "app.py").write_text("print('alpha')\n", encoding="utf-8")
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)
    assert workspace["unit"]["workflow_run_id"].startswith("fdw_")

    for artifact_name in portfolio_rollout.PLANNING_ARTIFACTS:
        workspace = portfolio_rollout.draft_planning_artifact(
            "alpha",
            artifact_name,
            actor="tester",
            catalog_path=str(catalog_path),
            db=db,
        )
        workspace = portfolio_rollout.approve_planning_artifact(
            "alpha",
            artifact_name,
            approved=True,
            actor="tester",
            catalog_path=str(catalog_path),
            db=db,
        )

    workspace = portfolio_rollout.approve_planning_bundle(
        "alpha",
        approved=True,
        actor="tester",
        catalog_path=str(catalog_path),
        db=db,
    )

    assert workspace["bundle_approval"]["approved"] is True
    assert workspace["progress"]["execution_ready"] is True
    assert workspace["unit"]["status"] == "ready_for_execution"


def test_live_artifact_job_writes_artifact_and_invalidates_approval(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)
    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs.threading, "Thread", _ImmediateThread)

    async def fake_run_provider(agent_provider: str, system: str, message: str, working_dir: str, repo_write_mode: str):
        return (
            json.dumps(
                {
                    "target_path": working_dir,
                    "current_state_summary": "Live model inventory summary",
                    "top_level_entries": ["README.md", "app.py"],
                    "risks": ["Needs human review"],
                }
            ),
            {"provider": "fake", "model": "fake-model", "runtime": agent_provider},
        )

    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs, "_run_provider", fake_run_provider)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.start_artifact_draft_job(
        "alpha",
        "inventory.json",
        actor="tester",
        agent_provider="codex",
        catalog_path=str(catalog_path),
        db=db,
    )
    artifact = workspace["artifacts"]["inventory.json"]
    assert artifact["complete"] is True
    assert artifact["approved"] is False
    assert artifact["latest_job"]["status"] == "completed"

    workspace = portfolio_rollout.approve_planning_artifact(
        "alpha",
        "inventory.json",
        approved=True,
        actor="tester",
        catalog_path=str(catalog_path),
        db=db,
    )
    assert workspace["artifacts"]["inventory.json"]["approved"] is True

    workspace = portfolio_rollout.save_planning_artifact(
        "alpha",
        "inventory.json",
        {
            "target_path": str(alpha_repo.resolve()),
            "current_state_summary": "Manual edit",
            "top_level_entries": ["README.md"],
            "risks": [],
        },
        actor="tester",
        catalog_path=str(catalog_path),
        db=db,
    )
    assert workspace["artifacts"]["inventory.json"]["approved"] is False
    assert workspace["bundle_approval"]["approved"] is False


def test_live_artifact_job_failure_preserves_error(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)
    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs.threading, "Thread", _ImmediateThread)

    async def fake_bad_provider(agent_provider: str, system: str, message: str, working_dir: str, repo_write_mode: str):
        return ("not valid json", {"provider": "fake", "model": "bad", "runtime": agent_provider})

    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs, "_run_provider", fake_bad_provider)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.start_artifact_draft_job(
        "alpha",
        "inventory.json",
        actor="tester",
        agent_provider="claude",
        catalog_path=str(catalog_path),
        db=db,
    )
    job = workspace["artifacts"]["inventory.json"]["latest_job"]
    assert job["status"] == "failed"
    assert job["error"]
    assert workspace["artifacts"]["inventory.json"]["complete"] is False


def test_product_planning_job_completes_all_artifacts(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    (alpha_repo / "README.md").write_text("# Alpha\n", encoding="utf-8")
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)
    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs.threading, "Thread", _ImmediateThread)
    monkeypatch.setattr(
        portfolio_rollout.rollout_agent_jobs,
        "_git_capture",
        lambda working_dir: {"available": True, "status_lines": [], "diff_stat": "", "diff_text": ""},
    )

    async def fake_run_provider(agent_provider: str, system: str, message: str, working_dir: str, repo_write_mode: str):
        if "inventory.json" in message:
            payload = {
                "target_path": working_dir,
                "current_state_summary": "Inventory summary",
                "top_level_entries": ["README.md"],
                "risks": ["Needs review"],
            }
        elif "research_report.json" in message:
            payload = {
                "implemented_now": ["README exists"],
                "gaps": ["Execution undefined"],
                "recommended_references": ["architecture.md"],
            }
        elif "definition_of_done.json" in message:
            payload = {
                "functional_requirements": ["Document target behavior"],
                "tests_required": ["Add unit tests"],
                "quality_gates": ["Lint"],
                "security_requirements": ["Secrets review"],
                "observability_requirements": ["Health checks"],
                "rollback_requirements": ["Rollback notes"],
                "release_evidence": ["Release checklist"],
            }
        elif "execution_plan.json" in message:
            payload = {
                "task_slices": [{"title": "Slice 1", "owner": "codex", "acceptance_criteria": ["done"]}],
                "integrator": "lead",
                "approvals_required": ["bundle"],
            }
        else:
            payload = {
                "parent_issue": {"title": "Alpha rollout", "description": "Parent issue"},
                "child_issues": [{"title": "Child", "description": "Task"}],
            }
        return (json.dumps(payload), {"provider": "fake", "model": "fake-model", "runtime": agent_provider})

    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs, "_run_provider", fake_run_provider)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.start_product_planning_job(
        "alpha",
        actor="tester",
        agent_provider="codex",
        catalog_path=str(catalog_path),
        db=db,
    )

    assert workspace["progress"]["complete_count"] == 5
    assert workspace["latest_product_job"]["status"] == "completed"
    assert len(workspace["latest_product_job"]["step_results"]) == 5
    assert workspace["artifacts"]["linear_plan.json"]["complete"] is True


def test_codex_attention_required_can_be_retried_with_claude(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)
    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs.threading, "Thread", _ImmediateThread)
    monkeypatch.setattr(
        portfolio_rollout.rollout_agent_jobs,
        "_git_capture",
        lambda working_dir: {"available": True, "status_lines": [], "diff_stat": "", "diff_text": ""},
    )

    async def fake_run_provider(agent_provider: str, system: str, message: str, working_dir: str, repo_write_mode: str):
        if agent_provider == "codex":
            raise portfolio_rollout.rollout_agent_jobs.OperatorActionRequired("codex CLI is not installed")
        return (
            json.dumps(
                {
                    "target_path": working_dir,
                    "current_state_summary": "Claude inventory",
                    "top_level_entries": ["README.md"],
                    "risks": [],
                }
            ),
            {"provider": "fake", "model": "fake-model", "runtime": agent_provider},
        )

    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs, "_run_provider", fake_run_provider)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.start_artifact_draft_job(
        "alpha",
        "inventory.json",
        actor="tester",
        agent_provider="codex",
        catalog_path=str(catalog_path),
        db=db,
    )
    job = workspace["artifacts"]["inventory.json"]["latest_job"]
    assert job["status"] == "attention_required"

    workspace = portfolio_rollout.rerun_planning_job(
        "alpha",
        job_id=job["job_id"],
        actor="tester",
        agent_provider="claude",
        catalog_path=str(catalog_path),
        db=db,
    )
    latest = workspace["artifacts"]["inventory.json"]["latest_job"]
    assert latest["status"] == "completed"
    assert latest["agent_provider"] == "claude"


def test_cancel_running_artifact_job_blocks_artifact_write(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)
    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs.threading, "Thread", _ImmediateThread)
    monkeypatch.setattr(
        portfolio_rollout.rollout_agent_jobs,
        "_git_capture",
        lambda working_dir: {"available": True, "status_lines": [], "diff_stat": "", "diff_text": ""},
    )

    async def fake_canceling_provider(
        agent_provider: str, system: str, message: str, working_dir: str, repo_write_mode: str
    ):
        marker = "Prompt version: "
        run_id = message.split('"run_id": "')[1].split('"', 1)[0]
        project_name = message.split('"project_name": "')[1].split('"', 1)[0]
        jobs = portfolio_rollout.rollout_agent_jobs.list_jobs(project_name, run_id)
        portfolio_rollout.rollout_agent_jobs.cancel_job(project_name, run_id, jobs[0]["job_id"], requested_by="tester")
        return (
            json.dumps(
                {
                    "target_path": working_dir,
                    "current_state_summary": "Should not persist",
                    "top_level_entries": ["README.md"],
                    "risks": [],
                }
            ),
            {"provider": "fake", "model": "fake-model", "runtime": agent_provider, "marker": marker},
        )

    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs, "_run_provider", fake_canceling_provider)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.start_artifact_draft_job(
        "alpha",
        "inventory.json",
        actor="tester",
        agent_provider="codex",
        catalog_path=str(catalog_path),
        db=db,
    )
    job = workspace["artifacts"]["inventory.json"]["latest_job"]
    assert job["status"] == "failed"
    assert "Canceled before artifact write" in job["error"]
    assert workspace["artifacts"]["inventory.json"]["complete"] is False


def test_failed_product_job_does_not_claim_later_artifacts(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)
    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs.threading, "Thread", _ImmediateThread)
    monkeypatch.setattr(
        portfolio_rollout.rollout_agent_jobs,
        "_git_capture",
        lambda working_dir: {"available": True, "status_lines": [], "diff_stat": "", "diff_text": ""},
    )

    async def fake_failing_provider(
        agent_provider: str, system: str, message: str, working_dir: str, repo_write_mode: str
    ):
        raise RuntimeError("inventory step failed")

    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs, "_run_provider", fake_failing_provider)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.start_product_planning_job(
        "alpha",
        actor="tester",
        agent_provider="codex",
        catalog_path=str(catalog_path),
        db=db,
    )
    assert workspace["latest_product_job"]["status"] == "failed"
    assert workspace["artifacts"]["inventory.json"]["latest_job"]["status"] == "failed"
    assert workspace["artifacts"]["research_report.json"]["latest_job"] is None
    assert workspace["artifacts"]["linear_plan.json"]["latest_job"] is None


def test_bundle_approval_requires_repo_diff_ack(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)
    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs.threading, "Thread", _ImmediateThread)

    snapshots = iter(
        [
            {"available": True, "status_lines": [], "diff_stat": "", "diff_text": ""},
            {
                "available": True,
                "status_lines": [" M plan.md"],
                "diff_stat": " plan.md | 1 +",
                "diff_text": "diff --git a/plan.md b/plan.md\n+change",
            },
        ]
    )
    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs, "_git_capture", lambda working_dir: next(snapshots))

    async def fake_run_provider(agent_provider: str, system: str, message: str, working_dir: str, repo_write_mode: str):
        return (
            json.dumps(
                {
                    "target_path": working_dir,
                    "current_state_summary": "Inventory summary",
                    "top_level_entries": ["README.md"],
                    "risks": [],
                }
            ),
            {"provider": "fake", "model": "fake-model", "runtime": agent_provider},
        )

    monkeypatch.setattr(portfolio_rollout.rollout_agent_jobs, "_run_provider", fake_run_provider)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_artifact_draft_job(
        "alpha",
        "inventory.json",
        actor="tester",
        agent_provider="codex",
        catalog_path=str(catalog_path),
        db=db,
    )

    for artifact_name in [
        "inventory.json",
        "research_report.json",
        "definition_of_done.json",
        "execution_plan.json",
        "linear_plan.json",
    ]:
        if artifact_name != "inventory.json":
            portfolio_rollout.save_planning_artifact(
                "alpha",
                artifact_name,
                portfolio_rollout._artifact_payload_draft(
                    portfolio_rollout._require_product("alpha", str(catalog_path)),
                    portfolio_rollout.get_product_workspace(
                        "alpha", actor="tester", catalog_path=str(catalog_path), db=db
                    )["unit"],
                    artifact_name,
                ),
                actor="tester",
                catalog_path=str(catalog_path),
                db=db,
            )
        portfolio_rollout.approve_planning_artifact(
            "alpha",
            artifact_name,
            approved=True,
            actor="tester",
            catalog_path=str(catalog_path),
            db=db,
        )

    try:
        portfolio_rollout.approve_planning_bundle(
            "alpha",
            approved=True,
            actor="tester",
            catalog_path=str(catalog_path),
            db=db,
        )
        raise AssertionError("expected repo diff acknowledgment failure")
    except Exception as exc:
        assert "repo diff acknowledgment" in str(exc)

    workspace = portfolio_rollout.approve_planning_bundle(
        "alpha",
        approved=True,
        actor="tester",
        acknowledge_repo_diff=True,
        catalog_path=str(catalog_path),
        db=db,
    )
    assert workspace["bundle_approval"]["approved"] is True


def test_partial_definition_of_done_artifact_stays_incomplete(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.save_planning_artifact(
        "alpha",
        "definition_of_done.json",
        {"functional_requirements": ["Only one field"]},
        actor="tester",
        catalog_path=str(catalog_path),
        db=db,
    )
    artifact = workspace["artifacts"]["definition_of_done.json"]
    assert artifact["complete"] is False
    assert artifact["validation_errors"]


def test_manual_save_is_blocked_while_job_active(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    _mock_rollout_provider_ready(monkeypatch)

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    active_job = {
        "job_id": "planjob_active",
        "status": "running",
        "artifact_name": "inventory.json",
        "job_type": "artifact",
    }
    monkeypatch.setattr(
        portfolio_rollout.rollout_agent_jobs,
        "list_jobs",
        lambda project_name, run_id, artifact_name="", job_type="": [active_job],
    )

    try:
        portfolio_rollout.save_planning_artifact(
            "alpha",
            "inventory.json",
            {
                "target_path": str(alpha_repo.resolve()),
                "current_state_summary": "Manual",
                "top_level_entries": ["README.md"],
                "risks": [],
            },
            actor="tester",
            catalog_path=str(catalog_path),
            db=db,
        )
        raise AssertionError("expected active planning job save block")
    except Exception as exc:
        assert "planning job is active" in str(exc)


def test_unready_provider_returns_attention_required_job(tmp_path, monkeypatch):
    projects_dir = tmp_path / "managed-projects"
    repos_dir = tmp_path / "repos"
    repos_dir.mkdir()
    alpha_repo = repos_dir / "alpha-repo"
    alpha_repo.mkdir()
    catalog_path = tmp_path / "catalog.json"
    _write_catalog(catalog_path)

    monkeypatch.setattr(projects, "PROJECTS_PARENT_DIR", str(projects_dir))
    monkeypatch.setattr(portfolio_rollout, "_repo_search_roots", lambda: [repos_dir])
    _fake_folder_run(monkeypatch)
    monkeypatch.setattr(portfolio_rollout.provider_readiness, "current_runtime_scope", lambda: "host")
    monkeypatch.setattr(portfolio_rollout.provider_readiness, "available_runtime_scopes", lambda: ["host", "container"])
    monkeypatch.setattr(
        portfolio_rollout.rollout_agent_jobs.provider_readiness,
        "check_backend_readiness",
        lambda **kwargs: {
            "backend": kwargs.get("backend", ""),
            "provider": kwargs.get("provider", ""),
            "runtime_scope": kwargs.get("runtime_scope", "host"),
            "current_runtime_scope": "host",
            "ready": False,
            "status": "auth_required",
            "checks": [{"id": "smoke", "ok": False, "detail": "401 Unauthorized"}],
            "fix_hint": "Authenticate Codex CLI in the host runtime before starting rollout jobs.",
            "runtime": "codex_cli",
        },
    )
    monkeypatch.setattr(
        portfolio_rollout.provider_readiness,
        "check_backend_readiness",
        lambda **kwargs: {
            "backend": kwargs.get("backend", ""),
            "provider": kwargs.get("provider", ""),
            "runtime_scope": kwargs.get("runtime_scope", "host"),
            "current_runtime_scope": "host",
            "ready": False,
            "status": "auth_required",
            "checks": [{"id": "smoke", "ok": False, "detail": "401 Unauthorized"}],
            "fix_hint": "Authenticate Codex CLI in the host runtime before starting rollout jobs.",
            "runtime": "codex_cli",
        },
    )

    db = PortfolioDatabase(data_dir=str(tmp_path / "db"))
    portfolio_rollout.seed_catalog_portfolio(actor="tester", catalog_path=str(catalog_path), db=db)
    portfolio_rollout.start_product_planning("alpha", actor="tester", catalog_path=str(catalog_path), db=db)

    workspace = portfolio_rollout.start_product_planning_job(
        "alpha",
        actor="tester",
        agent_provider="codex",
        catalog_path=str(catalog_path),
        db=db,
    )
    job = workspace["latest_product_job"]
    assert job["status"] == "attention_required"
    assert job["failure_class"] == "auth_required"
    assert job["readiness_snapshot"]["ready"] is False
