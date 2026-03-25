from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from python.helpers import files, projects

WORKFLOW_PROFILE_ID = "folder_evaluation_delivery_v1"
WORKFLOW_TEMPLATE_PATH = "instruments/custom/workflow_engine/templates/folder_evaluation_delivery_v1.json"
SCHEMA_VERSION = "1.0.0"

STAGE_FAMILIES = [
    "discovery",
    "planning",
    "execution",
    "release_decision",
    "operations",
]

CANONICAL_ARTIFACTS = [
    "inventory.json",
    "research_report.json",
    "definition_of_done.json",
    "execution_plan.json",
    "evaluation_report.json",
    "release_readiness.json",
    "data_dictionary.json",
    "schema_model.json",
    "schema_change_log.json",
    "migration_spec.json",
    "linear_plan.json",
    "release_bundle.json",
]

SCHEMA_GOVERNANCE_ARTIFACTS = [
    "data_dictionary.json",
    "schema_model.json",
    "schema_change_log.json",
    "migration_spec.json",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(value: str) -> str:
    raw = (value or "").strip().lower()
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-_") or "target"


def _json_dumps(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)


def build_bundle_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_target_path(target_path: str) -> str:
    if not str(target_path or "").strip():
        raise ValueError("target_path is required")
    return str(Path(target_path).expanduser().resolve(strict=False))


def build_target_id(project_name: str, target_path: str) -> str:
    normalized = normalize_target_path(target_path)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"{_slug(project_name)}-{digest}"


def get_run_root(project_name: str, run_id: str) -> Path:
    return Path(projects.get_project_lifecycle_folder(project_name, "runs", run_id))


def get_artifact_root(project_name: str, run_id: str) -> Path:
    return get_run_root(project_name, run_id) / "artifacts"


def get_gate_root(project_name: str, run_id: str) -> Path:
    return get_run_root(project_name, run_id) / "gates"


def get_claim_root(project_name: str, run_id: str) -> Path:
    return get_run_root(project_name, run_id) / "claims"


def get_target_lock_path(project_name: str, target_id: str) -> Path:
    return Path(projects.get_project_lifecycle_folder(project_name, "target-locks", f"{target_id}.lock"))


@dataclass
class WorkflowRunContext:
    run_id: str
    target_id: str
    project_name: str
    target_path: str
    branch_ref: str
    workflow_profile: str = WORKFLOW_PROFILE_ID
    artifact_root: str = ""
    deploy_environment: str = ""
    approval_policy: str = "human_gated"
    max_parallelism: int = 1
    actor: str = "system"
    stage_family: str = "discovery"
    created_at: str = field(default_factory=_now_iso)
    scope: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskClaim:
    task_id: str
    owner: str
    read_globs: list[str] = field(default_factory=list)
    write_globs: list[str] = field(default_factory=list)
    owned_artifacts: list[str] = field(default_factory=list)
    depends_on: list[str] = field(default_factory=list)
    exclusive_write: bool = True
    lease_expires_at: str = ""
    conflict_policy: str = "fail"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArtifactEnvelope:
    artifact_name: str
    schema_version: str
    run_id: str
    stage_family: str
    producer: str
    bundle_hash: str
    generated_at: str
    inputs: dict[str, Any] = field(default_factory=dict)
    source_refs: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GateDecision:
    gate_name: str
    run_id: str
    approved: bool
    approved_by: str
    approved_at: str
    evidence_refs: list[str] = field(default_factory=list)
    bundle_hash: str = ""
    rejection_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_run_context(
    project_name: str,
    target_path: str,
    actor: str = "system",
    branch_ref: str = "",
    deploy_environment: str = "",
    scope: dict[str, Any] | None = None,
    constraints: dict[str, Any] | None = None,
    approval_policy: str = "human_gated",
    max_parallelism: int = 1,
) -> WorkflowRunContext:
    normalized_target = normalize_target_path(target_path)
    run_id = f"fdw_{uuid4().hex[:12]}"
    return WorkflowRunContext(
        run_id=run_id,
        target_id=build_target_id(project_name, normalized_target),
        project_name=project_name,
        target_path=normalized_target,
        branch_ref=branch_ref or "main",
        artifact_root=str(get_artifact_root(project_name, run_id)),
        deploy_environment=deploy_environment,
        approval_policy=approval_policy,
        max_parallelism=max(1, int(max_parallelism or 1)),
        actor=actor or "system",
        scope=scope or {},
        constraints=constraints or {},
    )


def _scope_root(pattern: str) -> str:
    normalized = str(pattern or "").strip().replace("\\", "/").lstrip("./")
    if not normalized:
        return ""
    wildcard_positions = [pos for pos in (normalized.find("*"), normalized.find("?"), normalized.find("[")) if pos >= 0]
    cut = min(wildcard_positions) if wildcard_positions else len(normalized)
    root = normalized[:cut].rstrip("/")
    if not root:
        return ""
    path = Path(root)
    parts: list[str] = []
    for part in path.parts:
        if any(char in part for char in "*?["):
            break
        parts.append(part)
    return "/".join(parts).strip("/")


def validate_task_claims(claims: list[TaskClaim]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    normalized_roots: list[tuple[str, str]] = []

    for claim in claims:
        if not claim.task_id.strip():
            errors.append("Task claim is missing task_id.")
            continue
        if claim.task_id in seen_ids:
            errors.append(f"Duplicate task claim id: {claim.task_id}")
        seen_ids.add(claim.task_id)
        if not claim.owner.strip():
            errors.append(f"Task claim {claim.task_id} is missing owner.")
        if claim.exclusive_write and not claim.write_globs:
            errors.append(f"Task claim {claim.task_id} must declare write_globs for exclusive writes.")
        for write_glob in claim.write_globs:
            root = _scope_root(write_glob)
            if not root:
                errors.append(f"Task claim {claim.task_id} has an invalid write_glob: {write_glob}")
                continue
            normalized_roots.append((claim.task_id, root))

    for index, (left_id, left_root) in enumerate(normalized_roots):
        for right_id, right_root in normalized_roots[index + 1 :]:
            if left_id == right_id:
                continue
            overlaps = (
                left_root == right_root
                or left_root.startswith(f"{right_root}/")
                or right_root.startswith(f"{left_root}/")
            )
            if overlaps:
                errors.append(
                    f"Task claims {left_id} and {right_id} overlap on write scope ({left_root} vs {right_root})."
                )
    return errors


def create_artifact_envelope(
    artifact_name: str,
    run_context: WorkflowRunContext,
    stage_family: str,
    producer: str,
    payload: dict[str, Any],
    inputs: dict[str, Any] | None = None,
    source_refs: list[str] | None = None,
) -> ArtifactEnvelope:
    return ArtifactEnvelope(
        artifact_name=artifact_name,
        schema_version=SCHEMA_VERSION,
        run_id=run_context.run_id,
        stage_family=stage_family,
        producer=producer,
        bundle_hash=build_bundle_hash(payload),
        generated_at=_now_iso(),
        inputs=inputs or {},
        source_refs=source_refs or [],
        payload=payload,
    )


def _artifact_payload(artifact_name: str, run_context: WorkflowRunContext) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "inventory.json": {
            "target_path": run_context.target_path,
            "current_state_summary": "",
            "top_level_entries": [],
            "risks": [],
        },
        "research_report.json": {
            "implemented_now": [],
            "gaps": [],
            "recommended_references": [],
        },
        "definition_of_done.json": {
            "functional_requirements": [],
            "tests_required": [],
            "quality_gates": [],
            "security_requirements": [],
            "observability_requirements": [],
            "rollback_requirements": [],
            "release_evidence": [],
        },
        "execution_plan.json": {
            "task_slices": [],
            "integrator": "",
            "approvals_required": ["planning_to_execution", "release_to_deploy"],
        },
        "evaluation_report.json": {
            "definition_of_done_score": 0,
            "rework_items": [],
            "quality_summary": "",
        },
        "release_readiness.json": {
            "ready": False,
            "blocking_checks": [],
            "required_observers": [],
        },
        "data_dictionary.json": {
            "policy": "additive_first",
            "states": ["proposed", "approved", "active", "deprecated", "removed"],
            "entities": [],
        },
        "schema_model.json": {
            "version": 1,
            "entities": [],
            "relationships": [],
        },
        "schema_change_log.json": {
            "entries": [],
            "semantic_reuse_forbidden": True,
        },
        "migration_spec.json": {
            "strategy": "expand_contract",
            "changes": [],
            "rollback_policy": "forward_fix_unless_explicitly_reversible",
        },
        "linear_plan.json": {
            "parent_issue": {},
            "child_issues": [],
        },
        "release_bundle.json": {
            "commit_sha": "",
            "pr_number": "",
            "linear_issue_keys": [],
            "artifact_manifest": [],
            "monitoring_snapshot": {},
        },
    }
    return defaults.get(artifact_name, {})


def initialize_run_artifacts(
    run_context: WorkflowRunContext, producer: str = "folder_delivery_workflow"
) -> dict[str, str]:
    artifact_root = Path(run_context.artifact_root)
    files.create_dir(str(artifact_root))
    artifact_paths: dict[str, str] = {}

    for artifact_name in CANONICAL_ARTIFACTS:
        envelope = create_artifact_envelope(
            artifact_name=artifact_name,
            run_context=run_context,
            stage_family=run_context.stage_family,
            producer=producer,
            payload=_artifact_payload(artifact_name, run_context),
            inputs={"target_id": run_context.target_id},
            source_refs=[run_context.target_path],
        )
        artifact_path = artifact_root / artifact_name
        artifact_path.write_text(_json_dumps(envelope.to_dict()) + "\n", encoding="utf-8")
        artifact_paths[artifact_name] = str(artifact_path)

    return artifact_paths


def write_task_claims(project_name: str, run_id: str, claims: list[TaskClaim]) -> dict[str, Any]:
    errors = validate_task_claims(claims)
    claim_root = get_claim_root(project_name, run_id)
    files.create_dir(str(claim_root))
    claim_path = claim_root / "task_claims.json"
    payload = {
        "run_id": run_id,
        "claims": [claim.to_dict() for claim in claims],
        "errors": errors,
        "bundle_hash": build_bundle_hash([claim.to_dict() for claim in claims]),
        "generated_at": _now_iso(),
    }
    claim_path.write_text(_json_dumps(payload) + "\n", encoding="utf-8")
    return payload


def record_gate_decision(
    project_name: str,
    run_id: str,
    gate_name: str,
    approved: bool,
    approved_by: str,
    evidence_refs: list[str] | None = None,
    bundle_hash: str = "",
    rejection_reason: str = "",
) -> dict[str, Any]:
    gate_root = get_gate_root(project_name, run_id)
    files.create_dir(str(gate_root))
    decision = GateDecision(
        gate_name=gate_name,
        run_id=run_id,
        approved=approved,
        approved_by=approved_by,
        approved_at=_now_iso(),
        evidence_refs=evidence_refs or [],
        bundle_hash=bundle_hash,
        rejection_reason=rejection_reason,
    )
    gate_path = gate_root / f"{_slug(gate_name)}.json"
    gate_path.write_text(_json_dumps(decision.to_dict()) + "\n", encoding="utf-8")
    return decision.to_dict()


def acquire_target_lock(project_name: str, run_context: WorkflowRunContext) -> str:
    lock_path = get_target_lock_path(project_name, run_context.target_id)
    files.create_dir(str(lock_path.parent))
    payload = {
        "run_id": run_context.run_id,
        "target_id": run_context.target_id,
        "target_path": run_context.target_path,
        "created_at": _now_iso(),
        "pid": os.getpid(),
    }
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, (_json_dumps(payload) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except FileExistsError as exc:
        existing = {}
        try:
            existing = json.loads(lock_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        raise RuntimeError(
            f"Target path is already locked for workflow execution by run "
            f"{existing.get('run_id', 'unknown')} ({run_context.target_path})."
        ) from exc
    return str(lock_path)


def release_target_lock(project_name: str, target_id: str, run_id: str = "") -> None:
    lock_path = get_target_lock_path(project_name, target_id)
    if not lock_path.exists():
        return
    if run_id:
        try:
            payload = json.loads(lock_path.read_text(encoding="utf-8"))
            if payload.get("run_id") and payload.get("run_id") != run_id:
                raise RuntimeError("Target lock belongs to another workflow run.")
        except json.JSONDecodeError:
            pass
    lock_path.unlink(missing_ok=True)


def build_linear_issue_batch(
    run_context: WorkflowRunContext,
    plan_title: str,
    execution_plan: dict[str, Any],
) -> list[dict[str, Any]]:
    parent_key = _slug(plan_title) or run_context.target_id
    issues = [
        {
            "title": plan_title,
            "description": (
                f"Workflow run `{run_context.run_id}` for `{run_context.target_path}`.\n\n"
                f"Target ID: `{run_context.target_id}`\n"
                f"Branch: `{run_context.branch_ref}`\n"
                f"Artifact root: `{run_context.artifact_root}`"
            ),
            "metadata": {
                "run_id": run_context.run_id,
                "target_id": run_context.target_id,
                "parent_key": parent_key,
                "artifact_root": run_context.artifact_root,
            },
        }
    ]
    for index, task_slice in enumerate(execution_plan.get("task_slices", []), start=1):
        title = str(task_slice.get("title") or f"{plan_title} slice {index}").strip()
        issues.append(
            {
                "title": title,
                "description": str(task_slice.get("description") or "").strip(),
                "metadata": {
                    "run_id": run_context.run_id,
                    "target_id": run_context.target_id,
                    "parent_key": parent_key,
                    "task_slice": task_slice,
                },
            }
        )
    return issues
