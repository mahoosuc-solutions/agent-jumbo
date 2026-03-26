from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4

from instruments.custom.claude_sdk.sdk_manager import ClaudeSDKManager
from python.helpers import dirty_json, files, folder_delivery_workflow

JOB_SCHEMA_VERSION = "2.0.0"
PROMPT_VERSION = "2026-03-25.2"
STATUS_TERMINAL = {"completed", "failed", "canceled", "attention_required"}
JOB_PROVIDER_OPTIONS = {"codex", "claude"}
JOB_TYPE_ARTIFACT = "artifact"
JOB_TYPE_PRODUCT = "product"
PRODUCT_ARTIFACT_SEQUENCE = [
    "inventory.json",
    "research_report.json",
    "definition_of_done.json",
    "execution_plan.json",
    "linear_plan.json",
]

_ACTIVE_THREADS: dict[str, threading.Thread] = {}


class OperatorActionRequired(RuntimeError):
    pass


def _now_iso() -> str:
    return folder_delivery_workflow._now_iso()


def get_jobs_root(project_name: str, run_id: str) -> Path:
    return folder_delivery_workflow.get_run_root(project_name, run_id) / "planning_jobs"


def get_job_path(project_name: str, run_id: str, job_id: str) -> Path:
    return get_jobs_root(project_name, run_id) / f"{job_id}.json"


def list_jobs(
    project_name: str,
    run_id: str,
    artifact_name: str = "",
    job_type: str = "",
) -> list[dict[str, Any]]:
    root = get_jobs_root(project_name, run_id)
    if not root.exists():
        return []
    jobs: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        data = _read_json_file(path)
        if not isinstance(data, dict):
            continue
        if artifact_name and not _job_targets_artifact(data, artifact_name):
            continue
        if job_type and str(data.get("job_type", "")) != job_type:
            continue
        jobs.append(data)
    jobs.sort(key=lambda item: (str(item.get("started_at", "")), str(item.get("job_id", ""))), reverse=True)
    return jobs


def get_job(project_name: str, run_id: str, job_id: str) -> dict[str, Any]:
    path = get_job_path(project_name, run_id, job_id)
    if not path.exists():
        raise Exception(f"Planning job not found: {job_id}")
    data = _read_json_file(path)
    if not isinstance(data, dict):
        raise Exception(f"Invalid planning job payload: {job_id}")
    return data


def get_latest_job(
    project_name: str,
    run_id: str,
    artifact_name: str = "",
    job_type: str = "",
) -> dict[str, Any] | None:
    jobs = list_jobs(project_name, run_id, artifact_name=artifact_name, job_type=job_type)
    return jobs[0] if jobs else None


def _write_job(project_name: str, run_id: str, job: dict[str, Any]) -> dict[str, Any]:
    path = get_job_path(project_name, run_id, str(job["job_id"]))
    files.create_dir(str(path.parent))
    _atomic_write_text(path, json.dumps(job, indent=2, sort_keys=True) + "\n")
    return job


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _read_json_file(path: Path, attempts: int = 3) -> dict[str, Any] | list[Any] | Any:
    last_error: Exception | None = None
    for _ in range(max(1, attempts)):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
    if last_error:
        raise last_error
    raise ValueError(f"Unable to read JSON: {path}")


def _present(value: Any) -> bool:
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip()) if isinstance(value, str) else bool(value)


def _artifact_completion_errors(artifact_name: str, payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact_name == "inventory.json":
        if not _present(payload.get("current_state_summary")):
            errors.append("inventory.json.current_state_summary is required")
        if not isinstance(payload.get("top_level_entries"), list) or not _present(payload.get("top_level_entries")):
            errors.append("inventory.json.top_level_entries must be a non-empty array")
        if not isinstance(payload.get("risks"), list):
            errors.append("inventory.json.risks must be an array")
        return errors
    if artifact_name == "research_report.json":
        for key in ("implemented_now", "gaps"):
            if not isinstance(payload.get(key), list) or not _present(payload.get(key)):
                errors.append(f"research_report.json.{key} must be a non-empty array")
        if not isinstance(payload.get("recommended_references"), list):
            errors.append("research_report.json.recommended_references must be an array")
        return errors
    if artifact_name == "definition_of_done.json":
        for key in (
            "functional_requirements",
            "tests_required",
            "quality_gates",
            "security_requirements",
            "observability_requirements",
            "rollback_requirements",
            "release_evidence",
        ):
            if not isinstance(payload.get(key), list) or not _present(payload.get(key)):
                errors.append(f"definition_of_done.json.{key} must be a non-empty array")
        return errors
    if artifact_name == "execution_plan.json":
        if not isinstance(payload.get("task_slices"), list) or not payload.get("task_slices"):
            errors.append("execution_plan.json.task_slices must be a non-empty array")
        else:
            for index, item in enumerate(payload.get("task_slices", [])):
                if not isinstance(item, dict):
                    errors.append(f"execution_plan.json.task_slices[{index}] must be an object")
                    continue
                if not _present(item.get("title")) or not _present(item.get("owner")):
                    errors.append(f"execution_plan.json.task_slices[{index}] requires title and owner")
                if not isinstance(item.get("acceptance_criteria"), list) or not _present(
                    item.get("acceptance_criteria")
                ):
                    errors.append(
                        f"execution_plan.json.task_slices[{index}].acceptance_criteria must be a non-empty array"
                    )
        if not _present(payload.get("integrator")):
            errors.append("execution_plan.json.integrator is required")
        if not isinstance(payload.get("approvals_required"), list) or not _present(payload.get("approvals_required")):
            errors.append("execution_plan.json.approvals_required must be a non-empty array")
        return errors
    if artifact_name == "linear_plan.json":
        parent_issue = payload.get("parent_issue")
        child_issues = payload.get("child_issues")
        if (
            not isinstance(parent_issue, dict)
            or not _present(parent_issue.get("title"))
            or not _present(parent_issue.get("description"))
        ):
            errors.append("linear_plan.json.parent_issue requires title and description")
        if not isinstance(child_issues, list) or not child_issues:
            errors.append("linear_plan.json.child_issues must be a non-empty array")
        return errors
    return errors


def _parse_structured_output(raw_output: str) -> dict[str, Any]:
    parsed = dirty_json.try_parse(raw_output)
    if isinstance(parsed, dict):
        return parsed
    raise ValueError("Model output was not a valid JSON object")


def _resolve_external_executable(backend: str) -> str:
    candidates: list[str] = []
    if backend == "claude_code":
        env_path = os.getenv("CLAUDE_CLI_PATH", "").strip()
        if env_path:
            candidates.append(env_path)
        candidates.extend(
            [
                "claude",
                "claude-code",
                os.path.expanduser("~/dev/tools/claude-code/bin/claude"),
            ]
        )
    elif backend == "codex":
        env_path = os.getenv("CODEX_CLI_PATH", "").strip()
        if env_path:
            candidates.append(env_path)
        candidates.extend(
            [
                "codex",
                "codex-cli",
                os.path.expanduser("~/dev/tools/claude-code/bin/codex"),
            ]
        )
    else:
        raise RuntimeError(f"Unsupported external backend: {backend}")

    for candidate in candidates:
        if os.path.isabs(candidate) and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    hint_var = "CLAUDE_CLI_PATH" if backend == "claude_code" else "CODEX_CLI_PATH"
    raise OperatorActionRequired(
        f"{backend} CLI is not installed or not in PATH. Install it, or set {hint_var} to the executable path."
    )


def _artifact_payload_snapshot(
    project_name: str,
    run_id: str,
    artifact_names: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    names = artifact_names or PRODUCT_ARTIFACT_SEQUENCE
    snapshots: dict[str, dict[str, Any]] = {}
    for artifact_name in names:
        try:
            payload = folder_delivery_workflow.load_artifact_payload(project_name, run_id, artifact_name)
            envelope = folder_delivery_workflow.load_artifact_envelope(project_name, run_id, artifact_name)
        except Exception:
            payload = {}
            envelope = {}
        snapshots[artifact_name] = {"payload": payload, "envelope": envelope}
    return snapshots


def _job_targets_artifact(job: dict[str, Any], artifact_name: str) -> bool:
    if str(job.get("artifact_name", "")) == artifact_name:
        return True
    if str(job.get("job_type", "")) == JOB_TYPE_PRODUCT and str(job.get("current_artifact", "")) == artifact_name:
        return True
    results = job.get("step_results", [])
    if isinstance(results, list):
        for result in results:
            if isinstance(result, dict) and str(result.get("artifact_name", "")) == artifact_name:
                return True
    return False


def _workspace_context_for_prompt(job: dict[str, Any]) -> dict[str, Any]:
    artifact_names = PRODUCT_ARTIFACT_SEQUENCE
    project_name = str(job.get("project_name", ""))
    run_id = str(job.get("run_id", ""))
    snapshots = _artifact_payload_snapshot(project_name, run_id, artifact_names)
    artifacts = {name: {"payload": data.get("payload", {})} for name, data in snapshots.items()}
    missing = [name for name, data in snapshots.items() if _artifact_completion_errors(name, data.get("payload", {}))]
    return {
        "product": job.get("product_context", {}),
        "unit": {
            "workflow_run_id": run_id,
            "target_path": str(job.get("working_dir", "")),
            "resolved_repos": job.get("resolved_repos", []),
            "unresolved_repos": job.get("unresolved_repos", []),
            "status": "planning",
        },
        "artifacts": artifacts,
        "missing_artifacts": missing,
    }


def _prompt_contract(
    artifact_name: str,
    product_context: dict[str, Any],
    workspace_context: dict[str, Any],
) -> tuple[str, str]:
    product = workspace_context.get("product", product_context)
    unit = workspace_context.get("unit", {})
    existing = (workspace_context.get("artifacts", {}) or {}).get(artifact_name, {})
    missing = workspace_context.get("missing_artifacts", [])

    context_blob = {
        "product": {
            "slug": product.get("slug"),
            "name": product.get("name"),
            "description": product.get("description"),
            "audience": product.get("audience"),
            "repos": product.get("repos"),
            "integrations": product.get("integrations"),
            "instruments": product.get("instruments"),
            "tools": product.get("tools"),
        },
        "workflow": {
            "project_name": product.get("project_name"),
            "run_id": unit.get("workflow_run_id"),
            "target_path": unit.get("target_path"),
            "resolved_repos": unit.get("resolved_repos"),
            "unresolved_repos": unit.get("unresolved_repos"),
            "status": unit.get("status"),
            "missing_artifacts": missing,
        },
        "existing_artifact_payload": existing.get("payload", {}),
    }

    system = (
        "You are producing one planning artifact for a portfolio rollout workflow.\n"
        "Inspect and rely on the current repository state in the working directory.\n"
        "You may update planning files in the target repo when that materially improves planning evidence.\n"
        "Do not invent implementations or integrations that are not evidenced by the provided context or repo state.\n"
        "Return only a single JSON object matching the requested schema. No markdown fences."
    )
    prompts = {
        "inventory.json": (
            "Produce `inventory.json` with keys: "
            "`target_path` (string), `current_state_summary` (string), `top_level_entries` (array of strings), "
            "`risks` (array of strings). Summarize current state conservatively from the provided context."
        ),
        "research_report.json": (
            "Produce `research_report.json` with keys: `implemented_now` (array of strings), "
            "`gaps` (array of strings), `recommended_references` (array of strings). "
            "Focus on what is implemented today, what remains undefined, and what references the operator should review."
        ),
        "definition_of_done.json": (
            "Produce `definition_of_done.json` with keys: `functional_requirements`, `tests_required`, "
            "`quality_gates`, `security_requirements`, `observability_requirements`, `rollback_requirements`, "
            "`release_evidence`. Each key must map to an array of concrete strings."
        ),
        "execution_plan.json": (
            "Produce `execution_plan.json` with keys: `task_slices` (array of objects), `integrator` (string), "
            "`approvals_required` (array of strings). Each task slice object should include `title`, `owner`, "
            "`acceptance_criteria` (array of strings), and optionally `write_scope` (array of strings)."
        ),
        "linear_plan.json": (
            "Produce `linear_plan.json` with keys: `parent_issue` (object with `title` and `description`), "
            "`child_issues` (array of objects with `title` and `description`)."
        ),
    }
    message = (
        f"{prompts[artifact_name]}\n\n"
        f"Prompt version: {PROMPT_VERSION}\n"
        "Context JSON:\n"
        f"{json.dumps(context_blob, indent=2, sort_keys=True)}"
    )
    return system, message


async def _run_codex_job(system: str, message: str, working_dir: str) -> tuple[str, dict[str, Any]]:
    prompt = f"{system}\n\n{message}"
    executable = _resolve_external_executable("codex")
    cmd = [
        executable,
        "exec",
        "--sandbox",
        "workspace-write",
        "--skip-git-repo-check",
        "--color",
        "never",
        prompt,
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=working_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise OperatorActionRequired(
            f"codex executable not found ({exc.filename}). Install Codex CLI or configure CODEX_CLI_PATH."
        ) from exc
    except Exception as exc:
        raise OperatorActionRequired(f"Unable to start codex CLI: {exc}") from exc

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=900)
    except TimeoutError as exc:
        with contextlib.suppress(ProcessLookupError):
            process.kill()
        raise RuntimeError("codex timed out after 900s") from exc

    out = (stdout or b"").decode(errors="replace").strip()
    err = (stderr or b"").decode(errors="replace").strip()
    if process.returncode != 0:
        raise RuntimeError(err or out or f"codex exited with code {process.returncode}")
    if not out:
        raise RuntimeError("codex returned empty output")
    return out, {
        "provider": "openai",
        "model": "codex-cli",
        "runtime": "codex_cli",
        "executable": executable,
        "command": [*cmd[:-1], "<prompt>"],
        "exit_code": process.returncode,
        "stderr": err,
    }


async def _run_claude_job(system: str, message: str, working_dir: str) -> tuple[str, dict[str, Any]]:
    manager = ClaudeSDKManager()
    prompt = f"{system}\n\n{message}"
    if manager.sdk_available:
        result = await manager.simple_query(prompt, {"system_prompt": system})
        if "error" in result:
            raise RuntimeError(str(result["error"]))
        response = "\n".join(
            str(item.get("content", "")) for item in result.get("responses", []) if str(item.get("content", "")).strip()
        ).strip()
        if response:
            return response, {"provider": "anthropic", "model": "claude-sdk", "runtime": "claude_sdk"}
    cli_result = manager.run_cli_command(prompt, working_dir=working_dir, timeout=300)
    if cli_result.get("error"):
        raise RuntimeError(str(cli_result["error"]))
    return str(cli_result.get("output", "")).strip(), {
        "provider": "anthropic",
        "model": "claude-cli",
        "runtime": "claude_cli",
        "exit_code": cli_result.get("exit_code", 0),
    }


async def _run_provider(
    agent_provider: str,
    system: str,
    message: str,
    working_dir: str,
) -> tuple[str, dict[str, Any]]:
    if agent_provider == "claude":
        return await _run_claude_job(system, message, working_dir)
    return await _run_codex_job(system, message, working_dir)


def _invalidate_review_state(
    project_name: str, run_id: str, artifact_name: str, clear_bundle_only: bool = False
) -> None:
    review_path = folder_delivery_workflow.get_run_root(project_name, run_id) / "planning_review.json"
    if not review_path.exists():
        return
    review_state = json.loads(review_path.read_text(encoding="utf-8"))
    if not isinstance(review_state, dict):
        return
    artifacts = review_state.get("artifacts", {}) if isinstance(review_state.get("artifacts"), dict) else {}
    if not clear_bundle_only:
        artifacts.pop(artifact_name, None)
        review_state["artifacts"] = artifacts
    review_state["bundle"] = {}
    review_path.write_text(json.dumps(review_state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git_capture(working_dir: str) -> dict[str, Any]:
    root = Path(working_dir)
    if not root.exists():
        return {"available": False, "reason": f"Working directory does not exist: {working_dir}"}
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return {"available": False, "reason": inside.stderr.strip() or "Not a git repository"}

    def _run_git(args: list[str]) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return (result.stdout or result.stderr or "").strip()

    status_text = _run_git(["status", "--short"])
    diff_stat = _run_git(["diff", "--stat", "--no-ext-diff"])
    diff_text = _run_git(["diff", "--binary", "--no-color", "--no-ext-diff"])
    return {
        "available": True,
        "status_text": status_text,
        "status_lines": [line for line in status_text.splitlines() if line.strip()],
        "diff_stat": diff_stat,
        "diff_text": diff_text,
    }


def _status_map(snapshot: dict[str, Any]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in snapshot.get("status_lines", []):
        raw = str(line)
        if len(raw) < 4:
            continue
        mapping[raw[3:].strip()] = raw[:2]
    return mapping


def _persist_repo_diff(
    project_name: str,
    run_id: str,
    job_id: str,
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, Any]:
    root = get_jobs_root(project_name, run_id)
    files.create_dir(str(root))
    before_map = _status_map(before)
    after_map = _status_map(after)
    changed_files = sorted(
        {path for path in set(before_map) | set(after_map) if before_map.get(path) != after_map.get(path)}
    )
    state_changed = before.get("diff_text", "") != after.get("diff_text", "") or before_map != after_map
    if state_changed and not changed_files:
        changed_files = sorted(after_map.keys())
    summary = {
        "available": bool(after.get("available")),
        "state_changed": state_changed,
        "changed_files": changed_files,
        "changed_file_count": len(changed_files),
        "baseline_dirty": bool(before.get("status_lines")),
        "before_status": before.get("status_lines", []),
        "after_status": after.get("status_lines", []),
        "after_diff_stat": after.get("diff_stat", ""),
    }
    payload_path = root / f"{job_id}.repo_diff.json"
    payload_path.write_text(
        json.dumps({"summary": summary, "before": before, "after": after}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    patch_path = root / f"{job_id}.repo_diff.patch"
    patch_path.write_text(str(after.get("diff_text", "")), encoding="utf-8")
    return {
        "summary": summary,
        "path": str(payload_path),
        "patch_path": str(patch_path),
    }


def _artifact_step(
    *,
    job: dict[str, Any],
    artifact_name: str,
    project_name: str,
    run_id: str,
    working_dir: str,
) -> dict[str, Any]:
    latest = get_job(project_name, run_id, str(job["job_id"]))
    if latest.get("cancel_requested"):
        raise RuntimeError("Canceled before provider execution")
    _invalidate_review_state(project_name, run_id, artifact_name)
    workspace_context = _workspace_context_for_prompt(job)
    product_context = job.get("product_context", {})
    system, message = _prompt_contract(artifact_name, product_context, workspace_context)
    raw_output, runtime_meta = asyncio.run(
        _run_provider(str(job["agent_provider"]), system=system, message=message, working_dir=working_dir)
    )
    payload = _parse_structured_output(raw_output)
    errors = _artifact_completion_errors(artifact_name, payload)
    if errors:
        raise ValueError("; ".join(errors))
    latest = get_job(project_name, run_id, str(job["job_id"]))
    if latest.get("cancel_requested"):
        raise RuntimeError("Canceled before artifact write")
    envelope = folder_delivery_workflow.write_system_artifact(
        project_name=project_name,
        run_id=run_id,
        artifact_name=artifact_name,
        payload=payload,
        stage_family="planning",
        producer=f"{job['agent_provider']}-agent",
        inputs={"job_id": job["job_id"], "prompt_version": job.get("prompt_version", PROMPT_VERSION)},
        source_refs=[working_dir],
    )
    return {
        "artifact_name": artifact_name,
        "artifact_hash": envelope.get("bundle_hash", ""),
        "payload": payload,
        "raw_output": raw_output,
        "runtime_meta": runtime_meta,
        "stderr": runtime_meta.get("stderr", "") if isinstance(runtime_meta, dict) else "",
        "validation_errors": [],
    }


def _run_artifact_job(job: dict[str, Any], project_name: str, run_id: str, working_dir: str) -> dict[str, Any]:
    step_result = _artifact_step(
        job=job,
        artifact_name=str(job["artifact_name"]),
        project_name=project_name,
        run_id=run_id,
        working_dir=working_dir,
    )
    job["status"] = "completed"
    job["finished_at"] = _now_iso()
    job["output_artifact_hash"] = step_result["artifact_hash"]
    job["validated_payload"] = step_result["payload"]
    job["raw_output"] = step_result["raw_output"]
    job["runtime_meta"] = step_result["runtime_meta"]
    job["agent_model"] = str(step_result["runtime_meta"].get("model", ""))
    job["stderr"] = step_result["stderr"]
    job["validation_errors"] = step_result["validation_errors"]
    return job


def _run_product_job(job: dict[str, Any], project_name: str, run_id: str, working_dir: str) -> dict[str, Any]:
    sequence = [str(item) for item in job.get("artifact_sequence", PRODUCT_ARTIFACT_SEQUENCE)]
    step_results: list[dict[str, Any]] = []
    for index, artifact_name in enumerate(sequence):
        latest = get_job(project_name, run_id, str(job["job_id"]))
        if latest.get("cancel_requested"):
            latest["status"] = "canceled"
            latest["finished_at"] = _now_iso()
            latest["error"] = "Canceled before completing product planning"
            return latest
        latest["current_artifact"] = artifact_name
        latest["current_step_index"] = index
        _write_job(project_name, run_id, latest)
        step_result = _artifact_step(
            job=latest,
            artifact_name=artifact_name,
            project_name=project_name,
            run_id=run_id,
            working_dir=working_dir,
        )
        step_results.append(
            {
                "artifact_name": artifact_name,
                "artifact_hash": step_result["artifact_hash"],
                "runtime_meta": step_result["runtime_meta"],
                "status": "completed",
            }
        )
        latest = get_job(project_name, run_id, str(job["job_id"]))
        latest["step_results"] = step_results
        latest["raw_output"] = step_result["raw_output"]
        latest["runtime_meta"] = step_result["runtime_meta"]
        latest["agent_model"] = str(step_result["runtime_meta"].get("model", ""))
        latest["stderr"] = step_result["stderr"]
        latest["current_artifact"] = artifact_name
        latest["current_step_index"] = index
        _write_job(project_name, run_id, latest)

    latest = get_job(project_name, run_id, str(job["job_id"]))
    latest["status"] = "completed"
    latest["finished_at"] = _now_iso()
    latest["output_artifact_hash"] = step_results[-1]["artifact_hash"] if step_results else ""
    latest["step_results"] = step_results
    latest["current_artifact"] = sequence[-1] if sequence else ""
    latest["current_step_index"] = len(step_results) - 1
    return latest


def _run_job_thread(project_name: str, run_id: str, job_id: str, working_dir: str) -> None:
    job = get_job(project_name, run_id, job_id)
    before_repo = _git_capture(working_dir)
    job["status"] = "running"
    job["started_at"] = _now_iso()
    _write_job(project_name, run_id, job)
    try:
        if str(job.get("job_type", JOB_TYPE_ARTIFACT)) == JOB_TYPE_PRODUCT:
            job = _run_product_job(job, project_name, run_id, working_dir)
        else:
            job = _run_artifact_job(job, project_name, run_id, working_dir)
    except OperatorActionRequired as exc:
        job["status"] = "attention_required"
        job["finished_at"] = _now_iso()
        job["error"] = str(exc)
    except Exception as exc:
        job["status"] = "failed"
        job["finished_at"] = _now_iso()
        job["error"] = str(exc)
        if str(job.get("job_type", JOB_TYPE_ARTIFACT)) == JOB_TYPE_PRODUCT and job.get("current_artifact"):
            job["failed_artifact"] = job.get("current_artifact", "")
    finally:
        after_repo = _git_capture(working_dir)
        diff_meta = _persist_repo_diff(project_name, run_id, job_id, before_repo, after_repo)
        if diff_meta["summary"].get("state_changed"):
            _invalidate_review_state(project_name, run_id, str(job.get("artifact_name", "")), clear_bundle_only=True)
        job["repo_diff_summary"] = diff_meta["summary"]
        job["repo_diff_path"] = diff_meta["path"]
        job["repo_diff_patch_path"] = diff_meta["patch_path"]
        _write_job(project_name, run_id, job)
        _ACTIVE_THREADS.pop(job_id, None)


def _active_jobs(project_name: str, run_id: str) -> list[dict[str, Any]]:
    return [job for job in list_jobs(project_name, run_id) if str(job.get("status", "")) in {"queued", "running"}]


def start_artifact_job(
    *,
    product_slug: str,
    project_name: str,
    run_id: str,
    artifact_name: str,
    working_dir: str,
    requested_by: str,
    agent_provider: str,
    product_context: dict[str, Any],
    resolved_repos: list[dict[str, str]] | None = None,
    unresolved_repos: list[str] | None = None,
) -> dict[str, Any]:
    if agent_provider not in JOB_PROVIDER_OPTIONS:
        raise Exception(f"Unsupported agent provider: {agent_provider}")
    active = _active_jobs(project_name, run_id)
    if active:
        raise Exception("A planning job is already active for this product")

    job_id = f"planjob_{uuid4().hex[:12]}"
    job = {
        "job_id": job_id,
        "job_type": JOB_TYPE_ARTIFACT,
        "schema_version": JOB_SCHEMA_VERSION,
        "product_slug": product_slug,
        "project_name": project_name,
        "run_id": run_id,
        "artifact_name": artifact_name,
        "artifact_sequence": [artifact_name],
        "current_artifact": artifact_name,
        "current_step_index": 0,
        "agent_provider": agent_provider,
        "agent_model": "",
        "status": "queued",
        "requested_by": requested_by,
        "started_at": "",
        "finished_at": "",
        "error": "",
        "prompt_version": PROMPT_VERSION,
        "output_artifact_hash": "",
        "source_refs": [working_dir],
        "working_dir": working_dir,
        "product_context": product_context,
        "resolved_repos": resolved_repos or [],
        "unresolved_repos": unresolved_repos or [],
        "cancel_requested": False,
        "raw_output": "",
        "runtime_meta": {},
        "validation_errors": [],
        "stderr": "",
        "step_results": [],
        "repo_diff_summary": {},
        "repo_diff_path": "",
        "repo_diff_patch_path": "",
    }
    _write_job(project_name, run_id, job)
    thread = threading.Thread(
        target=_run_job_thread,
        kwargs={
            "project_name": project_name,
            "run_id": run_id,
            "job_id": job_id,
            "working_dir": working_dir,
        },
        daemon=True,
        name=f"rollout-{job_id}",
    )
    _ACTIVE_THREADS[job_id] = thread
    thread.start()
    return get_job(project_name, run_id, job_id)


def start_product_job(
    *,
    product_slug: str,
    project_name: str,
    run_id: str,
    working_dir: str,
    requested_by: str,
    agent_provider: str,
    product_context: dict[str, Any],
    resolved_repos: list[dict[str, str]] | None = None,
    unresolved_repos: list[str] | None = None,
) -> dict[str, Any]:
    if agent_provider not in JOB_PROVIDER_OPTIONS:
        raise Exception(f"Unsupported agent provider: {agent_provider}")
    active = _active_jobs(project_name, run_id)
    if active:
        raise Exception("A planning job is already active for this product")

    job_id = f"planjob_{uuid4().hex[:12]}"
    job = {
        "job_id": job_id,
        "job_type": JOB_TYPE_PRODUCT,
        "schema_version": JOB_SCHEMA_VERSION,
        "product_slug": product_slug,
        "project_name": project_name,
        "run_id": run_id,
        "artifact_name": "",
        "artifact_sequence": PRODUCT_ARTIFACT_SEQUENCE,
        "current_artifact": PRODUCT_ARTIFACT_SEQUENCE[0],
        "current_step_index": 0,
        "agent_provider": agent_provider,
        "agent_model": "",
        "status": "queued",
        "requested_by": requested_by,
        "started_at": "",
        "finished_at": "",
        "error": "",
        "prompt_version": PROMPT_VERSION,
        "output_artifact_hash": "",
        "source_refs": [working_dir],
        "working_dir": working_dir,
        "product_context": product_context,
        "resolved_repos": resolved_repos or [],
        "unresolved_repos": unresolved_repos or [],
        "cancel_requested": False,
        "raw_output": "",
        "runtime_meta": {},
        "validation_errors": [],
        "stderr": "",
        "step_results": [],
        "repo_diff_summary": {},
        "repo_diff_path": "",
        "repo_diff_patch_path": "",
        "failed_artifact": "",
    }
    _write_job(project_name, run_id, job)
    thread = threading.Thread(
        target=_run_job_thread,
        kwargs={
            "project_name": project_name,
            "run_id": run_id,
            "job_id": job_id,
            "working_dir": working_dir,
        },
        daemon=True,
        name=f"rollout-{job_id}",
    )
    _ACTIVE_THREADS[job_id] = thread
    thread.start()
    return get_job(project_name, run_id, job_id)


def start_job(**kwargs) -> dict[str, Any]:
    return start_artifact_job(**kwargs)


def rerun_job(
    project_name: str,
    run_id: str,
    job_id: str,
    requested_by: str,
    agent_provider: str = "",
) -> dict[str, Any]:
    job = get_job(project_name, run_id, job_id)
    provider = agent_provider or str(job.get("agent_provider", "codex"))
    common = {
        "product_slug": str(job.get("product_slug", "")),
        "project_name": project_name,
        "run_id": run_id,
        "working_dir": str(job.get("working_dir", "")),
        "requested_by": requested_by,
        "agent_provider": provider,
        "product_context": job.get("product_context", {}),
        "resolved_repos": job.get("resolved_repos", []),
        "unresolved_repos": job.get("unresolved_repos", []),
    }
    if str(job.get("job_type", JOB_TYPE_ARTIFACT)) == JOB_TYPE_PRODUCT:
        return start_product_job(**common)
    return start_artifact_job(artifact_name=str(job.get("artifact_name", "")), **common)


def cancel_job(project_name: str, run_id: str, job_id: str, requested_by: str) -> dict[str, Any]:
    job = get_job(project_name, run_id, job_id)
    if str(job.get("status", "")) in STATUS_TERMINAL:
        return job
    job["cancel_requested"] = True
    job["canceled_by"] = requested_by
    if str(job.get("status", "")) == "queued":
        job["status"] = "canceled"
        job["finished_at"] = _now_iso()
    _write_job(project_name, run_id, job)
    return job
