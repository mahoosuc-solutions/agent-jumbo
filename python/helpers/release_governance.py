from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_RELEASE_BUNDLE_KEYS = {
    "commit_sha",
    "pr_number",
    "linear_issue_keys",
    "artifact_manifest",
    "approvals",
    "deploy_target",
    "pre_deploy_checks",
    "post_deploy_checks",
    "monitoring_snapshot",
    "rollback_plan",
}

REQUIRED_PRE_DEPLOY_CHECKS = {
    "artifact_manifest_verified",
    "config_validated",
    "secrets_present",
    "dependency_reachability",
    "migration_compatibility",
    "environment_lock",
    "backup_confirmed",
}

REQUIRED_POST_DEPLOY_CHECKS = {
    "health_endpoint",
    "chat_readiness",
    "workflow_smoke",
    "schema_verification",
    "monitoring_snapshot",
}


def _require_dict(payload: Any, name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{name} payload must be an object")
    return payload


def validate_release_bundle(payload: dict[str, Any]) -> list[str]:
    payload = _require_dict(payload, "release_bundle")
    errors: list[str] = []

    missing = [key for key in REQUIRED_RELEASE_BUNDLE_KEYS if key not in payload]
    if missing:
        errors.append(f"release_bundle is missing required keys: {sorted(missing)}")
        return errors

    if not str(payload.get("commit_sha", "")).strip():
        errors.append("release_bundle.commit_sha is required")
    if not str(payload.get("pr_number", "")).strip():
        errors.append("release_bundle.pr_number is required")
    if not str(payload.get("deploy_target", "")).strip():
        errors.append("release_bundle.deploy_target is required")
    if not isinstance(payload.get("linear_issue_keys"), list) or not payload.get("linear_issue_keys"):
        errors.append("release_bundle.linear_issue_keys must be a non-empty list")
    if not isinstance(payload.get("artifact_manifest"), list) or not payload.get("artifact_manifest"):
        errors.append("release_bundle.artifact_manifest must be a non-empty list")
    if not isinstance(payload.get("approvals"), list):
        errors.append("release_bundle.approvals must be a list")
    if not isinstance(payload.get("rollback_plan"), dict):
        errors.append("release_bundle.rollback_plan must be an object")

    pre = payload.get("pre_deploy_checks")
    if not isinstance(pre, dict):
        errors.append("release_bundle.pre_deploy_checks must be an object")
    else:
        missing_pre = [key for key in REQUIRED_PRE_DEPLOY_CHECKS if key not in pre]
        if missing_pre:
            errors.append(f"release_bundle.pre_deploy_checks is missing keys: {sorted(missing_pre)}")
        failing_pre = [key for key in REQUIRED_PRE_DEPLOY_CHECKS if pre.get(key) is not True]
        if failing_pre:
            errors.append(f"release_bundle.pre_deploy_checks must all pass before deploy: {sorted(failing_pre)}")

    post = payload.get("post_deploy_checks")
    if not isinstance(post, dict):
        errors.append("release_bundle.post_deploy_checks must be an object")
    else:
        missing_post = [key for key in REQUIRED_POST_DEPLOY_CHECKS if key not in post]
        if missing_post:
            errors.append(f"release_bundle.post_deploy_checks is missing keys: {sorted(missing_post)}")

    monitoring = payload.get("monitoring_snapshot")
    if not isinstance(monitoring, dict):
        errors.append("release_bundle.monitoring_snapshot must be an object")
    else:
        for key in ("status", "observed_at"):
            if not str(monitoring.get(key, "")).strip():
                errors.append(f"release_bundle.monitoring_snapshot.{key} is required")

    return errors


def should_validate_release_bundle(payload: dict[str, Any]) -> bool:
    payload = _require_dict(payload, "release_bundle")
    return bool(
        str(payload.get("commit_sha", "")).strip()
        or str(payload.get("pr_number", "")).strip()
        or payload.get("linear_issue_keys")
        or payload.get("artifact_manifest")
        or payload.get("approvals")
        or str(payload.get("deploy_target", "")).strip()
        or any(
            value is True
            for value in _require_dict(
                payload.get("pre_deploy_checks", {}), "release_bundle.pre_deploy_checks"
            ).values()
        )
        or any(
            value is True
            for value in _require_dict(
                payload.get("post_deploy_checks", {}), "release_bundle.post_deploy_checks"
            ).values()
        )
    )


def should_validate_release_readiness(payload: dict[str, Any]) -> bool:
    payload = _require_dict(payload, "release_readiness")
    return payload.get("ready") is True


def validate_release_readiness(payload: dict[str, Any]) -> list[str]:
    payload = _require_dict(payload, "release_readiness")
    errors: list[str] = []
    if payload.get("ready") is not True:
        errors.append("release_readiness.ready must be true")
    if not isinstance(payload.get("blocking_checks"), list):
        errors.append("release_readiness.blocking_checks must be a list")
    elif payload.get("blocking_checks"):
        errors.append("release_readiness.blocking_checks must be empty before deploy")
    if not isinstance(payload.get("required_observers"), list) or not payload.get("required_observers"):
        errors.append("release_readiness.required_observers must be a non-empty list")
    return errors


def validate_post_deploy_report(payload: dict[str, Any]) -> list[str]:
    payload = _require_dict(payload, "post_deploy_report")
    errors: list[str] = []
    required = {"status", "observation_window", "rollback_triggered", "checks"}
    missing = [key for key in required if key not in payload]
    if missing:
        errors.append(f"post_deploy_report is missing required keys: {sorted(missing)}")
        return errors

    if str(payload.get("status", "")).strip() not in {"healthy", "degraded", "failed"}:
        errors.append("post_deploy_report.status must be one of healthy, degraded, failed")
    if not isinstance(payload.get("rollback_triggered"), bool):
        errors.append("post_deploy_report.rollback_triggered must be a boolean")

    observation = payload.get("observation_window")
    if not isinstance(observation, dict):
        errors.append("post_deploy_report.observation_window must be an object")
    else:
        for key in ("started_at", "duration_minutes", "decision"):
            if key not in observation:
                errors.append(f"post_deploy_report.observation_window.{key} is required")

    checks = payload.get("checks")
    if not isinstance(checks, dict):
        errors.append("post_deploy_report.checks must be an object")
    else:
        missing_checks = [key for key in REQUIRED_POST_DEPLOY_CHECKS if key not in checks]
        if missing_checks:
            errors.append(f"post_deploy_report.checks is missing keys: {sorted(missing_checks)}")
    return errors


def should_validate_post_deploy_report(payload: dict[str, Any]) -> bool:
    payload = _require_dict(payload, "post_deploy_report")
    observation_window = payload.get("observation_window")
    started_at = observation_window.get("started_at", "") if isinstance(observation_window, dict) else ""
    return bool(
        payload.get("status") in {"healthy", "failed"}
        or payload.get("rollback_triggered") is True
        or str(started_at).strip()
    )


def load_release_artifact_payload(artifact_root: str | Path, artifact_name: str) -> dict[str, Any]:
    artifact_path = Path(artifact_root) / artifact_name
    if not artifact_path.exists():
        return {}
    envelope = json.loads(artifact_path.read_text(encoding="utf-8"))
    if isinstance(envelope, dict):
        payload = envelope.get("payload", envelope)
        if isinstance(payload, dict):
            return payload
    return {}
