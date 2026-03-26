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
