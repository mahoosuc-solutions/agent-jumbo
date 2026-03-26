from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from instruments.custom.portfolio_manager.portfolio_db import PortfolioDatabase
from python.helpers import (
    files,
    folder_delivery_workflow,
    project_lifecycle,
    projects,
    provider_readiness,
    rollout_agent_jobs,
)

PRODUCT_CATALOG_PATH = "docs/product-page/product-catalog.json"
PORTFOLIO_PROJECT_PREFIX = "portfolio-"
PORTFOLIO_INITIATIVE_TITLE = "Portfolio Completion Rollout"
ROLLOUT_TARGET_OVERRIDE_KEY = "rollout_target_path_override"
ROLLUP_LINEAR_SYNC_KEY = "rollout_linear_sync"
PLANNING_BUNDLE_GATE = "planning_to_execution"
PLANNING_ARTIFACTS = [
    "inventory.json",
    "research_report.json",
    "definition_of_done.json",
    "execution_plan.json",
    "linear_plan.json",
]
ROLLOUT_PROVIDER_OPTIONS = ["codex", "claude"]


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


def _catalog_lookup(catalog_path: str = PRODUCT_CATALOG_PATH) -> dict[str, CatalogProduct]:
    return {product.slug: product for product in _load_catalog(catalog_path)}


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


def _find_portfolio_project_record(db: PortfolioDatabase, product: CatalogProduct) -> dict[str, Any] | None:
    return db.get_project_by_path(projects.get_project_folder(product.project_name))


def _load_rollout_metadata(db: PortfolioDatabase, product: CatalogProduct) -> dict[str, Any]:
    project_record = _find_portfolio_project_record(db, product)
    if not project_record:
        return {}
    return db.get_metadata(int(project_record["id"])) or {}


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


def _resolve_paths_for_product(
    db: PortfolioDatabase, product: CatalogProduct
) -> tuple[list[dict[str, str]], list[str], str]:
    metadata = _load_rollout_metadata(db, product)
    override_path = str(metadata.get(ROLLOUT_TARGET_OVERRIDE_KEY, "")).strip()
    resolved_repos, unresolved_repos = _resolve_repo_paths(product.repos)
    target_path = _primary_target_path(resolved_repos)
    if override_path:
        normalized_override = folder_delivery_workflow.normalize_target_path(override_path)
        if all(item["path"] != normalized_override for item in resolved_repos):
            resolved_repos = [{"repo": "override", "path": normalized_override}, *resolved_repos]
        target_path = normalized_override
    return resolved_repos, unresolved_repos, target_path


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


def _run_review_path(project_name: str, run_id: str) -> Path:
    return folder_delivery_workflow.get_run_root(project_name, run_id) / "planning_review.json"


def _load_review_state(project_name: str, run_id: str) -> dict[str, Any]:
    path = _run_review_path(project_name, run_id)
    if not path.exists():
        return {"artifacts": {}, "bundle": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {"artifacts": {}, "bundle": {}}
    return {
        "artifacts": data.get("artifacts", {}) if isinstance(data.get("artifacts"), dict) else {},
        "bundle": data.get("bundle", {}) if isinstance(data.get("bundle"), dict) else {},
    }


def _write_review_state(project_name: str, run_id: str, state: dict[str, Any]) -> dict[str, Any]:
    path = _run_review_path(project_name, run_id)
    files.create_dir(str(path.parent))
    payload = {
        "artifacts": state.get("artifacts", {}) if isinstance(state.get("artifacts"), dict) else {},
        "bundle": state.get("bundle", {}) if isinstance(state.get("bundle"), dict) else {},
    }
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(path)
    return payload


def _invalidate_artifact_approval(project_name: str, run_id: str, artifact_name: str) -> dict[str, Any]:
    review_state = _load_review_state(project_name, run_id)
    review_state.setdefault("artifacts", {}).pop(artifact_name, None)
    review_state["bundle"] = {}
    return _write_review_state(project_name, run_id, review_state)


def _artifact_validation_errors(artifact_name: str, payload: dict[str, Any], ready: bool) -> list[str]:
    if ready:
        return []
    messages = {
        "inventory.json": ["Inventory must include a summary, top-level entries, or risks."],
        "research_report.json": ["Research must include implemented behavior, gaps, or references."],
        "definition_of_done.json": ["Definition of Done must define functional, testing, or quality requirements."],
        "execution_plan.json": ["Execution plan must define task slices or an integrator."],
        "linear_plan.json": ["Linear plan must define a parent issue or child issues."],
    }
    return messages.get(artifact_name, ["Artifact is incomplete."])


def _artifact_status(
    project_name: str,
    run_id: str,
    artifact_name: str,
    review_state: dict[str, Any],
) -> dict[str, Any]:
    payload = folder_delivery_workflow.load_artifact_payload(project_name, run_id, artifact_name)
    envelope = folder_delivery_workflow.load_artifact_envelope(project_name, run_id, artifact_name)
    ready = _planning_artifact_ready(project_name, run_id, artifact_name)
    approval = review_state.get("artifacts", {}).get(artifact_name, {})
    artifact_hash = str(envelope.get("bundle_hash", "")).strip()
    latest_job = rollout_agent_jobs.get_latest_job(project_name, run_id, artifact_name)
    latest_job_id = str(latest_job.get("job_id", "")).strip() if isinstance(latest_job, dict) else ""
    latest_job_status = str(latest_job.get("status", "")).strip() if isinstance(latest_job, dict) else ""
    approved = (
        bool(approval.get("approved"))
        and artifact_hash
        and approval.get("artifact_hash") == artifact_hash
        and (not latest_job_id or (approval.get("latest_job_id") == latest_job_id and latest_job_status == "completed"))
    )
    stale = bool(approval.get("approved")) and bool(artifact_hash) and approval.get("artifact_hash") != artifact_hash
    status = "approved" if approved else "drafted" if ready else "missing"
    return {
        "artifact_name": artifact_name,
        "title": artifact_name.replace(".json", "").replace("_", " ").title(),
        "payload": payload,
        "status": status,
        "complete": ready,
        "approved": approved,
        "approval_stale": stale,
        "approval": approval if isinstance(approval, dict) else {},
        "producer": str(envelope.get("producer", "")).strip(),
        "generated_at": str(envelope.get("generated_at", "")).strip(),
        "artifact_hash": artifact_hash,
        "validation_errors": _artifact_validation_errors(artifact_name, payload, ready),
        "latest_job": latest_job,
    }


def _bundle_approval_state(
    review_state: dict[str, Any],
    artifact_statuses: dict[str, dict[str, Any]],
    diff_evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    record = review_state.get("bundle", {}) if isinstance(review_state.get("bundle"), dict) else {}
    current_hashes = {
        artifact_name: details.get("artifact_hash", "") for artifact_name, details in artifact_statuses.items()
    }
    approved = bool(record.get("approved")) and record.get("artifact_hashes") == current_hashes
    stale = bool(record.get("approved")) and record.get("artifact_hashes") != current_hashes
    diff_evidence = diff_evidence or []
    reviewed_diff_job_ids = [
        str(item).strip() for item in record.get("repo_diff_reviewed_jobs", []) if str(item).strip()
    ]
    pending_diff_job_ids = [
        str(item.get("job_id", "")).strip()
        for item in diff_evidence
        if item.get("summary", {}).get("state_changed")
        and str(item.get("job_id", "")).strip() not in reviewed_diff_job_ids
    ]
    return {
        "approved": approved,
        "approval_stale": stale,
        "approved_by": record.get("approved_by", ""),
        "approved_at": record.get("approved_at", ""),
        "notes": record.get("notes", ""),
        "artifact_hashes": current_hashes,
        "repo_diff_reviewed_jobs": reviewed_diff_job_ids,
        "pending_diff_job_ids": pending_diff_job_ids,
        "requires_repo_diff_ack": bool(pending_diff_job_ids),
    }


def _planning_artifact_ready(project_name: str, run_id: str, artifact_name: str) -> bool:
    try:
        payload = folder_delivery_workflow.load_artifact_payload(project_name, run_id, artifact_name)
    except Exception:
        return False
    return not rollout_agent_jobs._artifact_completion_errors(artifact_name, payload)


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
    resolved_repos, unresolved_repos, target_path = _resolve_paths_for_product(db, product)
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

    review_state = (
        _load_review_state(project_name, workflow_run_id) if workflow_run_id else {"artifacts": {}, "bundle": {}}
    )
    artifact_statuses = (
        {name: _artifact_status(project_name, workflow_run_id, name, review_state) for name in PLANNING_ARTIFACTS}
        if workflow_run_id
        else {}
    )
    approved_artifacts = sum(1 for item in artifact_statuses.values() if item.get("approved"))
    linear_sync = db.get_metadata(int(db_project["id"])).get(ROLLUP_LINEAR_SYNC_KEY, {})
    bundle_approval = _bundle_approval_state(review_state, artifact_statuses)
    if status != "definition_blocked" and planning_status and planning_status.get("complete"):
        status = "ready_for_execution" if bundle_approval["approved"] else "approval_pending"

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
        "planning_progress": {
            "complete_count": len((planning_status or {}).get("present", [])),
            "approved_count": approved_artifacts,
            "total": len(PLANNING_ARTIFACTS),
        },
        "bundle_approval": bundle_approval,
        "linear_sync": linear_sync if isinstance(linear_sync, dict) else {},
        "current_runtime_scope": provider_readiness.current_runtime_scope(),
        "available_runtime_scopes": provider_readiness.available_runtime_scopes(),
    }


def _provider_readiness_snapshot() -> dict[str, Any]:
    scopes = provider_readiness.available_runtime_scopes()
    current_scope = provider_readiness.current_runtime_scope()
    providers: dict[str, dict[str, Any]] = {}
    for provider_name in ROLLOUT_PROVIDER_OPTIONS:
        backend = "claude_code" if provider_name == "claude" else "codex"
        providers[provider_name] = {
            scope: provider_readiness.check_backend_readiness(
                backend=backend,
                provider="anthropic" if provider_name == "claude" else "openai",
                runtime_scope=scope,
            )
            for scope in scopes
        }
    return {
        "current_runtime_scope": current_scope,
        "available_runtime_scopes": scopes,
        "providers": providers,
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


def _require_product(product_slug: str, catalog_path: str = PRODUCT_CATALOG_PATH) -> CatalogProduct:
    product = _catalog_lookup(catalog_path).get(product_slug)
    if not product:
        raise Exception(f"Unknown product slug: {product_slug}")
    return product


def _now_iso() -> str:
    return folder_delivery_workflow._now_iso()


def _top_level_entries(target_path: str, limit: int = 12) -> list[str]:
    path = Path(target_path)
    if not path.exists() or not path.is_dir():
        return []
    entries = sorted(path.iterdir(), key=lambda item: item.name.lower())[:limit]
    return [entry.name + ("/" if entry.is_dir() else "") for entry in entries]


def _list_glob(target_path: str, pattern: str, limit: int = 12) -> list[str]:
    root = Path(target_path)
    if not root.exists():
        return []
    results = sorted(root.glob(pattern))[:limit]
    values: list[str] = []
    for item in results:
        try:
            values.append(str(item.relative_to(root)))
        except ValueError:
            values.append(str(item))
    return values


def _ensure_run_for_product(
    product: CatalogProduct,
    actor: str = "system",
    branch_ref: str = "",
    deploy_environment: str = "",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    db = db or PortfolioDatabase()
    unit = _build_unit(product, db)
    if unit["status"] == "definition_blocked":
        raise Exception(unit["blocked_reason"] or "Product is blocked")
    if unit["workflow_run_id"]:
        return unit, get_product_workspace(product.slug, actor=actor, catalog_path=catalog_path, db=db)
    project_lifecycle.start_folder_workflow(
        project_name=product.project_name,
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
            "ui_started": True,
        },
        branch_ref=branch_ref,
        deploy_environment=deploy_environment,
        max_parallelism=1,
    )
    return _build_unit(product, db), get_product_workspace(product.slug, actor=actor, catalog_path=catalog_path, db=db)


def _artifact_payload_draft(product: CatalogProduct, unit: dict[str, Any], artifact_name: str) -> dict[str, Any]:
    target_path = str(unit.get("target_path", "")).strip()
    repos = unit.get("resolved_repos", []) or []
    repo_lines = [f"{item['repo']}: {item['path']}" for item in repos if item.get("path")]
    top_entries = _top_level_entries(target_path)
    python_files = _list_glob(target_path, "*.py", limit=10)
    doc_files = _list_glob(target_path, "*.md", limit=10)

    if artifact_name == "inventory.json":
        risks = []
        if unit.get("unresolved_repos"):
            risks.append(f"Unresolved repos: {', '.join(unit['unresolved_repos'])}")
        if not top_entries:
            risks.append("Target path has not been inspected deeply yet from the UI.")
        return {
            "target_path": target_path,
            "current_state_summary": (
                f"{product.name} is mapped to `{target_path}` with {len(top_entries)} visible top-level entries "
                f"and {len(repo_lines)} resolved repo mappings."
            ),
            "top_level_entries": top_entries,
            "risks": risks,
        }
    if artifact_name == "research_report.json":
        implemented_now = [
            f"Catalog audience: {product.audience}",
            *[f"Linked repo: {line}" for line in repo_lines],
            *[f"Integration: {item}" for item in product.integrations],
            *[f"Instrument: {item}" for item in product.instruments],
            *[f"Tool: {item}" for item in product.tools],
        ]
        gaps = [
            "Planning artifacts still require human review and approval.",
            "Implementation status needs file-level validation beyond the catalog metadata.",
        ]
        references = [*python_files[:5], *doc_files[:5]]
        return {
            "implemented_now": implemented_now,
            "gaps": gaps,
            "recommended_references": references,
        }
    if artifact_name == "definition_of_done.json":
        return {
            "functional_requirements": [
                f"Define and document the core operator workflow for {product.name}.",
                "Map current folder state to required end-state capabilities.",
                "Keep repo ownership and integration boundaries explicit.",
            ],
            "tests_required": [
                "Unit coverage for new workflow/runtime behavior.",
                "Integration validation for lifecycle and release gates.",
                "UI verification for rollout status and approvals.",
            ],
            "quality_gates": [
                "All five planning artifacts are complete and approved.",
                "Traceability and CI checks pass.",
                "No unresolved write-scope or ownership conflicts remain.",
            ],
            "security_requirements": [
                "No secrets embedded in artifacts.",
                "Target path and deployment assumptions reviewed before execution.",
            ],
            "observability_requirements": [
                "Workflow run state is visible in the rollout dashboard.",
                "Release and deployment evidence are persisted to workflow artifacts.",
            ],
            "rollback_requirements": [
                "Schema changes use additive-first migration strategy.",
                "Deployment plan includes rollback or forward-fix path.",
            ],
            "release_evidence": [
                "Approved planning bundle hash.",
                "Execution and release readiness artifacts.",
                "Linked Linear items and PR traceability.",
            ],
        }
    if artifact_name == "execution_plan.json":
        task_slices = [
            {
                "title": "Discovery and inventory synthesis",
                "owner": "architect",
                "write_scope": ["artifacts/inventory.json", "artifacts/research_report.json"],
                "acceptance_criteria": ["Current-state inventory reviewed", "Research gaps captured"],
            },
            {
                "title": "Definition of Done and schema contract",
                "owner": "database-architect",
                "write_scope": ["artifacts/definition_of_done.json", "artifacts/data_dictionary.json"],
                "acceptance_criteria": ["DoD approved", "Data model changes governed"],
            },
            {
                "title": "Execution slice planning and Linear sync",
                "owner": "github-specialist",
                "write_scope": ["artifacts/execution_plan.json", "artifacts/linear_plan.json"],
                "acceptance_criteria": ["Execution slices defined", "Linear plan ready to sync"],
            },
        ]
        return {
            "task_slices": task_slices,
            "integrator": "software-engineer",
            "approvals_required": [PLANNING_BUNDLE_GATE, "release_to_deploy"],
        }
    if artifact_name == "linear_plan.json":
        execution_plan = folder_delivery_workflow.load_artifact_payload(
            product.project_name, unit["workflow_run_id"], "execution_plan.json"
        )
        slices = execution_plan.get("task_slices", []) if isinstance(execution_plan.get("task_slices"), list) else []
        child_issues = [
            {
                "title": slice.get("title", "Execution slice"),
                "description": "\n".join(
                    [
                        f"Owner: {slice.get('owner', 'unassigned')}",
                        f"Acceptance: {', '.join(slice.get('acceptance_criteria', []))}",
                    ]
                ),
            }
            for slice in slices
            if isinstance(slice, dict)
        ]
        return {
            "parent_issue": {
                "title": f"{product.name} planning and execution",
                "description": f"Workflow project `{product.project_name}` for product slug `{product.slug}`.",
            },
            "child_issues": child_issues,
        }
    raise Exception(f"Unsupported planning artifact: {artifact_name}")


def set_product_target(
    product_slug: str,
    target_path: str,
    actor: str = "system",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    normalized_target = folder_delivery_workflow.normalize_target_path(target_path)
    if not Path(normalized_target).exists():
        raise Exception(f"Target path does not exist: {normalized_target}")
    project_name = _ensure_project_shell(product)
    _ensure_portfolio_db_project(db, product, normalized_target)
    project_record = _find_portfolio_project_record(db, product)
    if not project_record:
        raise Exception(f"Portfolio project not found for {project_name}")
    db.set_metadata(int(project_record["id"]), ROLLOUT_TARGET_OVERRIDE_KEY, normalized_target)
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def get_product_workspace(
    product_slug: str,
    actor: str = "system",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    _ensure_project_shell(product)
    unit = _build_unit(product, db)
    lifecycle = project_lifecycle.load_lifecycle(product.project_name)
    run_record = _load_active_run_record(product.project_name, lifecycle)
    run_id = unit.get("workflow_run_id", "")
    review_state = _load_review_state(product.project_name, run_id) if run_id else {"artifacts": {}, "bundle": {}}
    artifact_details = {
        name: (
            _artifact_status(product.project_name, run_id, name, review_state)
            if run_id
            else {
                "artifact_name": name,
                "title": name.replace(".json", "").replace("_", " ").title(),
                "payload": {},
                "status": "missing",
                "complete": False,
                "approved": False,
                "approval_stale": False,
                "approval": {},
                "producer": "",
                "generated_at": "",
                "artifact_hash": "",
                "validation_errors": _artifact_validation_errors(name, {}, False),
            }
        )
        for name in PLANNING_ARTIFACTS
    }
    bundle_approval = _bundle_approval_state(review_state, artifact_details)
    jobs = rollout_agent_jobs.list_jobs(product.project_name, run_id) if run_id else []
    diff_evidence = [
        {
            "job_id": job.get("job_id", ""),
            "job_type": job.get("job_type", ""),
            "artifact_name": job.get("artifact_name", ""),
            "current_artifact": job.get("current_artifact", ""),
            "agent_provider": job.get("agent_provider", ""),
            "status": job.get("status", ""),
            "summary": job.get("repo_diff_summary", {}) if isinstance(job.get("repo_diff_summary"), dict) else {},
            "path": job.get("repo_diff_path", ""),
            "patch_path": job.get("repo_diff_patch_path", ""),
            "started_at": job.get("started_at", ""),
            "finished_at": job.get("finished_at", ""),
        }
        for job in jobs
        if isinstance(job.get("repo_diff_summary"), dict) and job.get("repo_diff_summary")
    ]
    latest_product_job = next(
        (job for job in jobs if str(job.get("job_type", "")) == rollout_agent_jobs.JOB_TYPE_PRODUCT), None
    )
    bundle_approval = _bundle_approval_state(review_state, artifact_details, diff_evidence)
    readiness = _provider_readiness_snapshot()
    run_log = []
    if run_record:
        run_log.append(
            {
                "run_id": run_record.get("run_id", ""),
                "stage_family": run_record.get("stage_family", ""),
                "status": run_record.get("status", ""),
                "started_at": run_record.get("started_at", ""),
                "finished_at": run_record.get("finished_at", ""),
            }
        )
    return {
        "product": {
            "slug": product.slug,
            "name": product.name,
            "description": product.description,
            "audience": product.audience,
            "repos": product.repos,
            "integrations": product.integrations,
            "instruments": product.instruments,
            "tools": product.tools,
            "project_name": product.project_name,
        },
        "unit": unit,
        "lifecycle": lifecycle,
        "run": run_record or {},
        "artifacts": artifact_details,
        "bundle_approval": bundle_approval,
        "missing_artifacts": [name for name, details in artifact_details.items() if not details.get("complete")],
        "progress": {
            "complete_count": sum(1 for details in artifact_details.values() if details.get("complete")),
            "approved_count": sum(1 for details in artifact_details.values() if details.get("approved")),
            "total": len(PLANNING_ARTIFACTS),
            "bundle_approved": bundle_approval["approved"],
            "active_jobs": sum(1 for job in jobs if str(job.get("status", "")) in {"queued", "running"}),
            "execution_ready": unit.get("status") == "ready_for_execution" or bundle_approval["approved"],
        },
        "run_log": run_log,
        "gates": folder_delivery_workflow.load_gate_decisions(product.project_name, run_id) if run_id else [],
        "planning_jobs": jobs,
        "latest_product_job": latest_product_job,
        "diff_evidence": diff_evidence,
        "provider_readiness": readiness,
    }


def start_product_planning(
    product_slug: str,
    actor: str = "system",
    branch_ref: str = "",
    deploy_environment: str = "",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    _ensure_run_for_product(
        product,
        actor=actor,
        branch_ref=branch_ref,
        deploy_environment=deploy_environment,
        catalog_path=catalog_path,
        db=db,
    )
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def save_planning_artifact(
    product_slug: str,
    artifact_name: str,
    payload: dict[str, Any],
    actor: str = "system",
    producer: str = "human",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    if artifact_name not in PLANNING_ARTIFACTS:
        raise Exception(f"Unsupported planning artifact: {artifact_name}")
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, _workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    run_id = str(unit.get("workflow_run_id", "")).strip()
    active_jobs = [
        job
        for job in rollout_agent_jobs.list_jobs(product.project_name, run_id)
        if str(job.get("status", "")) in {"queued", "running"}
    ]
    if active_jobs:
        raise Exception("Cannot save planning artifacts while a planning job is active")
    _invalidate_artifact_approval(product.project_name, run_id, artifact_name)
    folder_delivery_workflow.write_system_artifact(
        project_name=product.project_name,
        run_id=run_id,
        artifact_name=artifact_name,
        payload=payload,
        stage_family="planning",
        producer=producer,
        inputs={"actor": actor, "source": "portfolio_rollout"},
        source_refs=[str(unit.get("target_path", ""))],
    )
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def draft_planning_artifact(
    product_slug: str,
    artifact_name: str,
    actor: str = "codex",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, _workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    payload = _artifact_payload_draft(product, unit, artifact_name)
    return save_planning_artifact(
        product_slug=product_slug,
        artifact_name=artifact_name,
        payload=payload,
        actor=actor,
        producer="codex-rollout-draft",
        catalog_path=catalog_path,
        db=db,
    )


def approve_planning_artifact(
    product_slug: str,
    artifact_name: str,
    approved: bool,
    actor: str = "system",
    notes: str = "",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    if artifact_name not in PLANNING_ARTIFACTS:
        raise Exception(f"Unsupported planning artifact: {artifact_name}")
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    run_id = str(unit.get("workflow_run_id", "")).strip()
    details = workspace["artifacts"][artifact_name]
    latest_job = rollout_agent_jobs.get_latest_job(product.project_name, run_id, artifact_name)
    if latest_job and str(latest_job.get("status", "")) in {"queued", "running"}:
        raise Exception(f"{artifact_name} still has an active draft job")
    if approved and not details.get("complete"):
        raise Exception(f"{artifact_name} is incomplete")
    review_state = _load_review_state(product.project_name, run_id)
    review_state.setdefault("artifacts", {})[artifact_name] = {
        "approved": bool(approved),
        "approved_by": actor,
        "approved_at": _now_iso(),
        "artifact_hash": details.get("artifact_hash", ""),
        "latest_job_id": latest_job.get("job_id", "") if isinstance(latest_job, dict) else "",
        "latest_job_provider": latest_job.get("agent_provider", "") if isinstance(latest_job, dict) else "",
        "latest_job_model": latest_job.get("agent_model", "") if isinstance(latest_job, dict) else "",
        "notes": notes,
    }
    _write_review_state(product.project_name, run_id, review_state)
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def approve_planning_bundle(
    product_slug: str,
    approved: bool,
    actor: str = "system",
    notes: str = "",
    acknowledge_repo_diff: bool = False,
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    run_id = str(unit.get("workflow_run_id", "")).strip()
    artifact_statuses = workspace["artifacts"]
    active_jobs = [
        job for job in workspace.get("planning_jobs", []) if str(job.get("status", "")) in {"queued", "running"}
    ]
    if approved:
        incomplete = [name for name, details in artifact_statuses.items() if not details.get("complete")]
        unapproved = [name for name, details in artifact_statuses.items() if not details.get("approved")]
        if active_jobs:
            raise Exception("Planning bundle has active draft jobs")
        if incomplete:
            raise Exception(f"Planning bundle is incomplete: {', '.join(incomplete)}")
        if unapproved:
            raise Exception(f"Planning bundle has unapproved artifacts: {', '.join(unapproved)}")
        if workspace.get("bundle_approval", {}).get("requires_repo_diff_ack") and not acknowledge_repo_diff:
            raise Exception("Planning bundle requires explicit repo diff acknowledgment before approval")
    review_state = _load_review_state(product.project_name, run_id)
    review_state["bundle"] = {
        "approved": bool(approved),
        "approved_by": actor,
        "approved_at": _now_iso(),
        "artifact_hashes": {
            artifact_name: details.get("artifact_hash", "") for artifact_name, details in artifact_statuses.items()
        },
        "notes": notes,
        "repo_diff_reviewed_jobs": (
            workspace.get("bundle_approval", {}).get("pending_diff_job_ids", [])
            if acknowledge_repo_diff
            else workspace.get("bundle_approval", {}).get("repo_diff_reviewed_jobs", [])
        ),
    }
    _write_review_state(product.project_name, run_id, review_state)
    if approved:
        project_lifecycle.approve_folder_gate(
            project_name=product.project_name,
            run_id=run_id,
            gate_name=PLANNING_BUNDLE_GATE,
            approved_by=actor,
            approved=True,
            evidence_refs=list(PLANNING_ARTIFACTS),
        )
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def sync_product_linear_plan(
    product_slug: str,
    actor: str = "system",
    team_id: str = "",
    project_id: str = "",
    state_id: str = "",
    default_priority: int = 0,
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, _workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    run_id = str(unit.get("workflow_run_id", "")).strip()
    result = project_lifecycle.sync_folder_linear_plan(
        project_name=product.project_name,
        run_id=run_id,
        actor=actor,
        team_id=team_id,
        default_priority=default_priority,
        project_id=project_id,
        state_id=state_id,
    )
    project_record = _find_portfolio_project_record(db, product)
    if project_record:
        db.set_metadata(
            int(project_record["id"]),
            ROLLUP_LINEAR_SYNC_KEY,
            {
                "synced_at": _now_iso(),
                "success": True,
                "issue_count": len(result.get("issues", [])) if isinstance(result.get("issues"), list) else 0,
                "run_id": run_id,
            },
        )
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def start_artifact_draft_job(
    product_slug: str,
    artifact_name: str,
    actor: str = "system",
    agent_provider: str = "codex",
    runtime_scope: str = "current",
    repo_write_mode: str = "writable",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    if artifact_name not in PLANNING_ARTIFACTS:
        raise Exception(f"Unsupported planning artifact: {artifact_name}")
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    rollout_agent_jobs.start_job(
        product_slug=product_slug,
        project_name=product.project_name,
        run_id=str(unit["workflow_run_id"]),
        artifact_name=artifact_name,
        working_dir=str(unit["target_path"]),
        requested_by=actor,
        agent_provider=agent_provider,
        product_context=workspace["product"],
        resolved_repos=unit.get("resolved_repos", []),
        unresolved_repos=unit.get("unresolved_repos", []),
        runtime_scope=runtime_scope,
        repo_write_mode=repo_write_mode,
    )
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def start_product_planning_job(
    product_slug: str,
    actor: str = "system",
    agent_provider: str = "codex",
    runtime_scope: str = "current",
    repo_write_mode: str = "writable",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    rollout_agent_jobs.start_product_job(
        product_slug=product_slug,
        project_name=product.project_name,
        run_id=str(unit["workflow_run_id"]),
        working_dir=str(unit["target_path"]),
        requested_by=actor,
        agent_provider=agent_provider,
        product_context=workspace["product"],
        resolved_repos=unit.get("resolved_repos", []),
        unresolved_repos=unit.get("unresolved_repos", []),
        runtime_scope=runtime_scope,
        repo_write_mode=repo_write_mode,
    )
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def cancel_planning_job(
    product_slug: str,
    job_id: str,
    actor: str = "system",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, _workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    rollout_agent_jobs.cancel_job(product.project_name, str(unit["workflow_run_id"]), job_id, requested_by=actor)
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def cancel_artifact_draft_job(
    product_slug: str,
    job_id: str,
    actor: str = "system",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    return cancel_planning_job(
        product_slug=product_slug,
        job_id=job_id,
        actor=actor,
        catalog_path=catalog_path,
        db=db,
    )


def get_planning_job(
    product_slug: str,
    job_id: str,
    actor: str = "system",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, _workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    return rollout_agent_jobs.get_job(product.project_name, str(unit["workflow_run_id"]), job_id)


def get_artifact_draft_job(
    product_slug: str,
    job_id: str,
    actor: str = "system",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    return get_planning_job(
        product_slug=product_slug,
        job_id=job_id,
        actor=actor,
        catalog_path=catalog_path,
        db=db,
    )


def list_planning_jobs(
    product_slug: str,
    actor: str = "system",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> list[dict[str, Any]]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, _workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    return rollout_agent_jobs.list_jobs(product.project_name, str(unit["workflow_run_id"]))


def rerun_planning_job(
    product_slug: str,
    job_id: str,
    actor: str = "system",
    agent_provider: str = "",
    runtime_scope: str = "",
    repo_write_mode: str = "",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    product = _require_product(product_slug, catalog_path)
    db = db or PortfolioDatabase()
    unit, _workspace = _ensure_run_for_product(product, actor=actor, catalog_path=catalog_path, db=db)
    rollout_agent_jobs.rerun_job(
        product.project_name,
        str(unit["workflow_run_id"]),
        job_id,
        requested_by=actor,
        agent_provider=agent_provider,
        runtime_scope=runtime_scope,
        repo_write_mode=repo_write_mode,
    )
    return get_product_workspace(product_slug, actor=actor, catalog_path=catalog_path, db=db)


def get_provider_readiness(
    product_slug: str = "",
    actor: str = "system",
    runtime_scope: str = "",
    catalog_path: str = PRODUCT_CATALOG_PATH,
    db: PortfolioDatabase | None = None,
) -> dict[str, Any]:
    if product_slug:
        _require_product(product_slug, catalog_path)
    return _provider_readiness_snapshot()


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
