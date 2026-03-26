from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_SCHEMA_STATES = {"proposed", "approved", "active", "deprecated", "removed"}
REQUIRED_SCHEMA_ARTIFACTS = (
    "data_dictionary.json",
    "schema_model.json",
    "schema_change_log.json",
    "migration_spec.json",
)


def _require_dict(payload: Any, name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{name} payload must be an object")
    return payload


def validate_data_dictionary(payload: dict[str, Any]) -> list[str]:
    payload = _require_dict(payload, "data_dictionary")
    errors: list[str] = []

    if payload.get("policy") != "additive_first":
        errors.append("data_dictionary.policy must be 'additive_first'")

    states = set(payload.get("states", []))
    missing_states = REQUIRED_SCHEMA_STATES - states
    if missing_states:
        errors.append(f"data_dictionary.states is missing required values: {sorted(missing_states)}")

    entities = payload.get("entities")
    if not isinstance(entities, list):
        errors.append("data_dictionary.entities must be a list")
        return errors

    for entity in entities:
        if not isinstance(entity, dict):
            errors.append("data_dictionary.entities entries must be objects")
            continue
        if not str(entity.get("name", "")).strip():
            errors.append("Each data_dictionary entity must define a name")
        fields = entity.get("fields", [])
        if not isinstance(fields, list):
            errors.append(f"Entity '{entity.get('name', 'unknown')}' fields must be a list")
            continue
        for field in fields:
            if not isinstance(field, dict):
                errors.append(f"Entity '{entity.get('name', 'unknown')}' field entries must be objects")
                continue
            required = ("name", "type", "nullable", "semantic_definition", "lifecycle_state")
            missing = [key for key in required if key not in field]
            if missing:
                errors.append(
                    f"Field '{field.get('name', 'unknown')}' in entity '{entity.get('name', 'unknown')}' "
                    f"is missing required keys: {missing}"
                )
    return errors


def validate_schema_model(payload: dict[str, Any]) -> list[str]:
    payload = _require_dict(payload, "schema_model")
    errors: list[str] = []

    if not isinstance(payload.get("version"), int):
        errors.append("schema_model.version must be an integer")
    if not isinstance(payload.get("entities"), list):
        errors.append("schema_model.entities must be a list")
    if not isinstance(payload.get("relationships"), list):
        errors.append("schema_model.relationships must be a list")
    return errors


def validate_schema_change_log(payload: dict[str, Any]) -> list[str]:
    payload = _require_dict(payload, "schema_change_log")
    errors: list[str] = []

    entries = payload.get("entries")
    if not isinstance(entries, list):
        return ["schema_change_log.entries must be a list"]

    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("schema_change_log entries must be objects")
            continue
        action = str(entry.get("action", "")).strip()
        if not action:
            errors.append("schema_change_log entries must include action")
            continue
        if action in {"rename_column", "drop_column", "semantic_reuse"}:
            errors.append(
                f"schema_change_log action '{action}' is forbidden under additive-first policy; "
                "use add/deprecate/expand-contract steps instead"
            )
    return errors


def validate_migration_spec(payload: dict[str, Any]) -> list[str]:
    payload = _require_dict(payload, "migration_spec")
    errors: list[str] = []

    if payload.get("strategy") != "expand_contract":
        errors.append("migration_spec.strategy must be 'expand_contract'")
    if not str(payload.get("rollback_policy", "")).strip():
        errors.append("migration_spec.rollback_policy is required")
    if not isinstance(payload.get("changes"), list):
        errors.append("migration_spec.changes must be a list")
    return errors


def validate_schema_bundle(bundle: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    missing = [name for name in REQUIRED_SCHEMA_ARTIFACTS if name not in bundle]
    if missing:
        errors.append(f"Missing schema governance artifacts: {missing}")
        return errors

    errors.extend(validate_data_dictionary(bundle["data_dictionary.json"]))
    errors.extend(validate_schema_model(bundle["schema_model.json"]))
    errors.extend(validate_schema_change_log(bundle["schema_change_log.json"]))
    errors.extend(validate_migration_spec(bundle["migration_spec.json"]))
    return errors


def load_schema_bundle_from_artifact_root(artifact_root: str | Path) -> dict[str, dict[str, Any]]:
    root = Path(artifact_root)
    bundle: dict[str, dict[str, Any]] = {}

    for artifact_name in REQUIRED_SCHEMA_ARTIFACTS:
        artifact_path = root / artifact_name
        if not artifact_path.exists():
            continue
        envelope = json.loads(artifact_path.read_text(encoding="utf-8"))
        if isinstance(envelope, dict):
            payload = envelope.get("payload", envelope)
            if isinstance(payload, dict):
                bundle[artifact_name] = payload
    return bundle
