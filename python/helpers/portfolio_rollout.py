from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from instruments.custom.portfolio_manager.portfolio_db import PortfolioDatabase
from python.helpers import files, folder_delivery_workflow, project_lifecycle, projects

PRODUCT_CATALOG_PATH = "docs/product-page/product-catalog.json"
PORTFOLIO_PROJECT_PREFIX = "portfolio-"
PORTFOLIO_INITIATIVE_TITLE = "Portfolio Completion Rollout"
PLANNING_ARTIFACTS = [
    "inventory.json",
    "research_report.json",
    "definition_of_done.json",
    "execution_plan.json",
    "linear_plan.json",
]


@dataclass
class CatalogProduct:
    slug: str
    name: str
    description: str
    audience: str
    repos: list[str]
    integrations: list[str]
    instruments: list[str]
    tools: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CatalogProduct:
        return cls(
            slug=str(data.get("slug", "")).strip(),
            name=str(data.get("name", "")).strip(),
            description=str(data.get("description", "")).strip(),
            audience=str(data.get("audience", "")).strip(),
            repos=[str(item).strip() for item in data.get("repos", []) if str(item).strip()],
            integrations=[str(item).strip() for item in data.get("integrations", []) if str(item).strip()],
            instruments=[str(item).strip() for item in data.get("instruments", []) if str(item).strip()],
            tools=[str(item).strip() for item in data.get("tools", []) if str(item).strip()],
        )

    @property
    def project_name(self) -> str:
        return f"{PORTFOLIO_PROJECT_PREFIX}{self.slug}"


def _load_catalog(catalog_path: str = PRODUCT_CATALOG_PATH) -> list[CatalogProduct]:
    payload = json.loads(files.read_file(catalog_path))
    products_payload = payload.get("products", []) if isinstance(payload, dict) else []
    return [CatalogProduct.from_dict(item) for item in products_payload if isinstance(item, dict)]


def _repo_search_roots() -> list[Path]:
    roots = [Path.cwd(), Path.cwd().parent, Path(projects.get_projects_parent_folder())]
    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve(strict=False))
        if key not in seen:
            unique.append(root)
            seen.add(key)
    return unique


def _resolve_repo_paths(repo_names: list[str]) -> tuple[list[dict[str, str]], list[str]]:
    resolved: list[dict[str, str]] = []
    unresolved: list[str] = []
    roots = _repo_search_roots()
    current_repo_name = Path.cwd().name

    for repo_name in repo_names:
        candidate_paths: list[Path] = []
        if repo_name == current_repo_name:
            candidate_paths.append(Path.cwd())
        for root in roots:
            candidate_paths.append(root / repo_name)

        chosen: Path | None = None
        seen: set[str] = set()
        for candidate in candidate_paths:
            normalized = str(candidate.resolve(strict=False))
            if normalized in seen:
                continue
            seen.add(normalized)
            if candidate.exists() and candidate.is_dir():
                chosen = candidate.resolve(strict=False)
                break

        if chosen is None:
            unresolved.append(repo_name)
            continue

        resolved.append(
            {
                "repo": repo_name,
                "path": str(chosen),
            }
        )

    return resolved, unresolved


def _primary_target_path(resolved_repos: list[dict[str, str]]) -> str:
    if not resolved_repos:
        return ""
    cwd = str(Path.cwd().resolve(strict=False))
    for repo in resolved_repos:
        if repo["path"] == cwd:
            return repo["path"]
    return resolved_repos[0]["path"]


def _basic_project_payload(product: CatalogProduct) -> dict[str, Any]:
    return {
        "title": product.name,
        "description": product.description,
        "instructions": (
            "This is a portfolio-managed product unit. Use the folder delivery workflow to produce "
            "inventory, research, Definition of Done, execution plan, and release evidence."
        ),
        "color": "#2563EB",
        "memory": "own",
    }


def _ensure_project_shell(product: CatalogProduct) -> str:
    project_name = product.project_name
    try:
        projects.load_basic_project_data(project_name)
        projects.update_project(project_name, _basic_project_payload(product) | {"name": project_name})  # type: ignore[arg-type]
    except Exception:
        projects.create_project(project_name, _basic_project_payload(product))  # type: ignore[arg-type]
    return project_name


def _ensure_portfolio_db_project(db: PortfolioDatabase, product: CatalogProduct, target_path: str) -> dict[str, Any]:
    project_name = product.project_name
    path = projects.get_project_folder(project_name)
    record = db.get_project_by_path(path)
    description = product.description
    if record:
        db.update_project(
            record["id"], name=product.name, description=description, status=record.get("status", "draft")
        )
        project_id = int(record["id"])
    else:
        project_id = db.add_project(
            name=product.name,
            path=path,
            description=description,
            status="draft",
        )

    metadata = {
        "product_slug": product.slug,
        "audience": product.audience,
        "linked_repos": product.repos,
        "integrations": product.integrations,
        "instruments": product.instruments,
        "tools": product.tools,
        "workflow_project_name": project_name,
        "resolved_target_path": target_path,
    }
    for key, value in metadata.items():
        db.set_metadata(project_id, key, value)

    project_record = db.get_project(project_id) or {"id": project_id, "path": path}
    return project_record


def _ensure_product_listing(
    db: PortfolioDatabase, portfolio_project_id: int, product: CatalogProduct
) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in db.get_products(project_id=portfolio_project_id)
            if str(item.get("name", "")).strip().lower() == product.name.lower()
        ),
        None,
    )
    payload = {
        "tagline": "",
        "description": product.description,
        "category": product.audience or "builder",
        "sale_readiness_score": 0,
    }
    if existing:
        db.update_product(int(existing["id"]), **payload)
        return db.get_product(int(existing["id"])) or existing

    product_id = db.create_product(portfolio_project_id, product.name, **payload)
    return db.get_product(product_id) or {"id": product_id, "name": product.name}


def _load_active_run_record(project_name: str, lifecycle: dict[str, Any]) -> dict[str, Any] | None:
    active = lifecycle.get("active_workflow_run") or {}
    run_id = str(active.get("run_id", "")).strip()
    if not run_id:
        return None
    try:
        return project_lifecycle._load_run_record(project_name, run_id)
    except Exception:
        return None


def _planning_completion(project_name: str, run_id: str) -> dict[str, Any]:
    present = [name for name in PLANNING_ARTIFACTS if _planning_artifact_ready(project_name, run_id, name)]
    return {
        "present": present,
        "missing": [name for name in PLANNING_ARTIFACTS if name not in present],
        "complete": len(present) == len(PLANNING_ARTIFACTS),
    }


def _planning_artifact_ready(project_name: str, run_id: str, artifact_name: str) -> bool:
    try:
        payload = folder_delivery_workflow.load_artifact_payload(project_name, run_id, artifact_name)
    except Exception:
        return False

    if artifact_name == "inventory.json":
        return bool(payload.get("current_state_summary") or payload.get("top_level_entries") or payload.get("risks"))
    if artifact_name == "research_report.json":
        return bool(payload.get("implemented_now") or payload.get("gaps") or payload.get("recommended_references"))
    if artifact_name == "definition_of_done.json":
        keys = (
            "functional_requirements",
            "tests_required",
            "quality_gates",
            "security_requirements",
            "observability_requirements",
            "rollback_requirements",
            "release_evidence",
        )
        return any(payload.get(key) for key in keys)
    if artifact_name == "execution_plan.json":
        return bool(payload.get("task_slices") or payload.get("integrator"))
    if artifact_name == "linear_plan.json":
        return bool(payload.get("parent_issue") or payload.get("child_issues"))
    return False


def _derive_status(
    target_path: str,
    unresolved_repos: list[str],
    lifecycle: dict[str, Any] | None,
    run_record: dict[str, Any] | None,
    planning_status: dict[str, Any] | None,
) -> tuple[str, str]:
    if not target_path:
        reason = "No local repo path resolved from catalog repos" if unresolved_repos else "No target repo configured"
        return "definition_blocked", reason
    if planning_status and planning_status.get("complete"):
        return "ready_for_execution", ""
    if run_record:
        stage_family = str(run_record.get("stage_family", "")).strip() or "planning"
        run_status = str(run_record.get("status", "")).strip()
        if run_status == "gated":
            return "approval_pending", ""
        if stage_family in {"discovery", "planning"}:
            return stage_family, ""
        if stage_family == "execution":
            return "executing", ""
        if stage_family == "release_decision":
            return "release_ready", ""
        if stage_family == "operations":
            return "done", ""
    if lifecycle:
        return "seeded", ""
    return "unmapped", "Lifecycle project not initialized"


def _build_unit(
    product: CatalogProduct,
    db: PortfolioDatabase,
) -> dict[str, Any]:
    resolved_repos, unresolved_repos = _resolve_repo_paths(product.repos)
    target_path = _primary_target_path(resolved_repos)
    project_name = product.project_name
    lifecycle = None
    run_record = None
    planning_status = None
    workflow_run_id = ""

    try:
        lifecycle = project_lifecycle.load_lifecycle(project_name)
        run_record = _load_active_run_record(project_name, lifecycle)
        workflow_run_id = str((lifecycle.get("active_workflow_run") or {}).get("run_id", "")).strip()
        if not workflow_run_id:
            workflow_run_id = str((lifecycle.get("last_run") or {}).get("run_id", "")).strip()
        if workflow_run_id:
            planning_status = _planning_completion(project_name, workflow_run_id)
    except Exception:
        lifecycle = None

    db_project = _ensure_portfolio_db_project(db, product, target_path)
    db_product = _ensure_product_listing(db, int(db_project["id"]), product)
    status, blocked_reason = _derive_status(target_path, unresolved_repos, lifecycle, run_record, planning_status)

    db.set_metadata(
        int(db_project["id"]),
        "rollout_status",
        {
            "status": status,
            "blocked_reason": blocked_reason,
            "workflow_run_id": workflow_run_id,
        },
    )
    db.set_metadata(int(db_project["id"]), "resolved_repo_paths", resolved_repos)
    db.set_metadata(int(db_project["id"]), "unresolved_repos", unresolved_repos)

    return {
        "slug": product.slug,
        "name": product.name,
        "audience": product.audience,
        "repos": product.repos,
        "resolved_repos": resolved_repos,
        "unresolved_repos": unresolved_repos,
        "target_path": target_path,
        "project_name": project_name,
        "portfolio_project_id": db_project["id"],
        "portfolio_product_id": db_product["id"],
        "workflow_run_id": workflow_run_id,
        "status": status,
        "blocked_reason": blocked_reason,
        "planning_artifacts": planning_status or {"present": [], "complete": False},
    }


def seed_catalog_portfolio(
    actor: str = "system",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    db = db or PortfolioDatabase()
    products_catalog = _load_catalog(catalog_path)
    units: list[dict[str, Any]] = []

    for product in products_catalog:
        _ensure_project_shell(product)
        lifecycle = {
            "access": {"owner": actor, "collaborators": []},
            "workflow_profiles": {
                folder_delivery_workflow.WORKFLOW_PROFILE_ID: {
                    "enabled": True,
                    "approval_policy": "human_gated",
                    "max_parallelism": 1,
                }
            },
        }
        project_lifecycle.upsert_lifecycle(product.project_name, lifecycle, actor=actor)
        units.append(_build_unit(product, db))

    return {
        "catalog_count": len(products_catalog),
        "seeded_count": len(units),
        "units": units,
        "summary": summarize_units(units),
    }


def summarize_units(units: list[dict[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, int] = {}
    for unit in units:
        status = str(unit.get("status", "unmapped")).strip() or "unmapped"
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "total_products": len(units),
        "mapped_products": sum(1 for unit in units if unit.get("project_name")),
        "resolved_targets": sum(1 for unit in units if unit.get("target_path")),
        "planning_complete": sum(1 for unit in units if unit.get("planning_artifacts", {}).get("complete")),
        "blocked_products": sum(1 for unit in units if unit.get("status") == "definition_blocked"),
        "ready_for_execution": sum(1 for unit in units if unit.get("status") == "ready_for_execution"),
        "done": sum(1 for unit in units if unit.get("status") == "done"),
        "by_status": by_status,
    }


def get_rollout_dashboard(
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    db = db or PortfolioDatabase()
    units = [_build_unit(product, db) for product in _load_catalog(catalog_path)]
    ranked = sorted(
        units,
        key=lambda item: (
            item.get("status") not in {"ready_for_execution", "executing", "release_ready"},
            item.get("status") == "definition_blocked",
            item.get("slug", ""),
        ),
    )
    return {
        "initiative_title": PORTFOLIO_INITIATIVE_TITLE,
        "products": ranked,
        "summary": summarize_units(ranked),
    }


def start_definition_wave(
    actor: str = "system",
    product_slugs: list[str] | None = None,
    branch_ref: str = "",
    deploy_environment: str = "",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    db = db or PortfolioDatabase()
    started: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []

    for product in _load_catalog(catalog_path):
        if product_slugs and product.slug not in set(product_slugs):
            continue
        _ensure_project_shell(product)
        unit = _build_unit(product, db)
        if unit["status"] == "definition_blocked":
            blocked.append({"slug": product.slug, "reason": unit["blocked_reason"]})
            continue
        if unit["planning_artifacts"]["complete"]:
            skipped.append({"slug": product.slug, "reason": "planning bundle already complete"})
            continue
        lifecycle = project_lifecycle.load_lifecycle(product.project_name)
        active = lifecycle.get("active_workflow_run") or {}
        if str(active.get("run_id", "")).strip():
            skipped.append({"slug": product.slug, "reason": "workflow already active", "run_id": active.get("run_id")})
            continue

        run = project_lifecycle.start_folder_workflow(
            product.project_name,
            target_path=unit["target_path"],
            actor=actor,
            scope={
                "product_slug": product.slug,
                "product_name": product.name,
                "linked_repos": product.repos,
                "audience": product.audience,
            },
            constraints={
                "resolved_repos": unit["resolved_repos"],
                "unresolved_repos": unit["unresolved_repos"],
                "definition_wave": True,
            },
            deploy_environment=deploy_environment,
            branch_ref=branch_ref,
            max_parallelism=1,
        )
        started.append(
            {
                "slug": product.slug,
                "project_name": product.project_name,
                "run_id": run["run_id"],
                "target_path": unit["target_path"],
            }
        )

    return {
        "started": started,
        "skipped": skipped,
        "blocked": blocked,
        "summary": {
            "started": len(started),
            "skipped": len(skipped),
            "blocked": len(blocked),
        },
    }


def build_portfolio_linear_plan(
    actor: str = "system",
    sync: bool = False,
    team_id: str = "",
    project_id: str = "",
    state_id: str = "",
    default_priority: int = 0,
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    db = db or PortfolioDatabase()
    dashboard = get_rollout_dashboard(catalog_path=catalog_path, db=db)
    units = dashboard["products"]
    issues = [
        {
            "title": PORTFOLIO_INITIATIVE_TITLE,
            "description": (
                "Portfolio-wide initiative for defining, planning, and executing the current product catalog "
                "through the folder delivery workflow."
            ),
            "priority": max(default_priority, 1),
        }
    ]
    for unit in units:
        issues.append(
            {
                "title": f"{unit['name']} epic",
                "description": (
                    f"Product slug: `{unit['slug']}`\n"
                    f"Status: `{unit['status']}`\n"
                    f"Workflow project: `{unit['project_name']}`\n"
                    f"Repos: {', '.join(unit['repos']) or 'none listed'}\n"
                    f"Target path: `{unit['target_path'] or 'unresolved'}`"
                ),
                "priority": default_priority,
                "project_id": project_id or None,
                "state_id": state_id or None,
            }
        )

    result = {
        "initiative_title": PORTFOLIO_INITIATIVE_TITLE,
        "issue_batch": issues,
        "sync": False,
        "team_id": team_id,
        "created": [],
    }

    if not sync:
        return result

    manager = project_lifecycle._get_linear_manager()
    resolved_team_id = str(team_id or project_lifecycle._get_linear_team_id()).strip()
    if not resolved_team_id:
        raise Exception("Linear team_id is required. Set LINEAR_DEFAULT_TEAM_ID or pass team_id.")

    created = project_lifecycle._run_async(
        manager.create_issue_batch(
            issues=issues,
            team_id=resolved_team_id,
            default_priority=default_priority,
            project_id=project_id or None,
            state_id=state_id or None,
        )
    )
    result["sync"] = True
    result["team_id"] = resolved_team_id
    result["created"] = created.get("issues", [])
    result["failures"] = created.get("failures", [])
    result["success"] = created.get("success", False)
    return result
