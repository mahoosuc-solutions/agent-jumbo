#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

AUTOMATION_ACTOR = "system"


def _discover_artifact_roots(repo_root: Path, provided_roots: list[str]) -> list[Path]:
    if provided_roots:
        return [Path(root).resolve() for root in provided_roots]
    return sorted(
        path.parent.resolve() for path in repo_root.rglob("release_bundle.json") if path.parent.name == "artifacts"
    )


def _load_event_payload(event_path: str) -> dict[str, Any]:
    if not event_path:
        return {}
    path = Path(event_path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _resolve_pr_number(event_payload: dict[str, Any]) -> str:
    pull_request = event_payload.get("pull_request")
    if isinstance(pull_request, dict):
        number = pull_request.get("number")
        return str(number).strip() if number is not None else ""
    issue = event_payload.get("issue")
    if isinstance(issue, dict):
        number = issue.get("number")
        return str(number).strip() if number is not None else ""
    return ""


def _resolve_run_binding(artifact_root: Path) -> dict[str, str]:
    run_root = artifact_root.parent
    run_record_path = run_root / "run_record.json"
    if not run_record_path.exists():
        raise FileNotFoundError(f"run_record.json not found for artifact root {artifact_root}")
    run_record = json.loads(run_record_path.read_text(encoding="utf-8"))
    if not isinstance(run_record, dict):
        raise ValueError(f"Invalid run_record.json in {run_root}")
    project_name = str(run_record.get("project_name", "")).strip()
    run_id = str(run_record.get("run_id", "")).strip() or run_root.name
    if not project_name or not run_id:
        raise ValueError(f"Could not resolve project_name/run_id for artifact root {artifact_root}")
    return {"project_name": project_name, "run_id": run_id}


def _run_ci_mode(binding: dict[str, str], args, event_payload: dict[str, Any]) -> dict[str, Any]:
    from python.helpers import project_lifecycle

    project_name = binding["project_name"]
    run_id = binding["run_id"]
    results: dict[str, Any] = {"project_name": project_name, "run_id": run_id, "mode": "ci"}

    if args.sync_linear and os.getenv("LINEAR_API_KEY", "").strip():
        try:
            linear_plan = project_lifecycle.sync_folder_linear_plan(
                project_name=project_name,
                run_id=run_id,
                actor=AUTOMATION_ACTOR,
                team_id=str(args.team_id or "").strip(),
                default_priority=int(args.priority or 0),
                project_id=str(args.project_id or "").strip(),
                state_id=str(args.state_id or "").strip(),
            )
            results["linear_plan"] = {
                "created_count": linear_plan.get("created_count", 0),
                "parent_issue": ((linear_plan.get("parent_issue") or {}).get("identifier") or ""),
            }
        except Exception as exc:
            results["linear_plan_error"] = str(exc)

    release_bundle = project_lifecycle.build_folder_release_bundle(
        project_name=project_name,
        run_id=run_id,
        actor=AUTOMATION_ACTOR,
        commit_sha=os.getenv("GITHUB_SHA", "").strip(),
        pr_number=_resolve_pr_number(event_payload),
        deploy_target=str(
            args.environment or os.getenv("GITHUB_BASE_REF") or os.getenv("GITHUB_REF_NAME") or ""
        ).strip(),
    )
    results["release_bundle"] = {
        "commit_sha": release_bundle.get("commit_sha", ""),
        "pr_number": release_bundle.get("pr_number", ""),
        "deploy_target": release_bundle.get("deploy_target", ""),
    }
    return results


def _run_deploy_mode(binding: dict[str, str], args) -> dict[str, Any]:
    from python.helpers import project_lifecycle

    project_name = binding["project_name"]
    run_id = binding["run_id"]
    environment = str(args.environment or os.getenv("GITHUB_REF_NAME") or "").strip()
    run_id_env = os.getenv("GITHUB_RUN_ID", "").strip()
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    deployment_url = str(args.deployment_url or "").strip()
    if not deployment_url and repository and run_id_env:
        deployment_url = f"https://github.com/{repository}/actions/runs/{run_id_env}"

    deploy_run = project_lifecycle.record_folder_deploy_run(
        project_name=project_name,
        run_id=run_id,
        actor=AUTOMATION_ACTOR,
        deployment_system=str(args.deployment_system or "github_actions").strip(),
        repository=repository,
        workflow_file=str(args.workflow_file or os.getenv("GITHUB_WORKFLOW", "")).strip(),
        workflow_run_id=run_id_env,
        build_id=str(args.build_id or os.getenv("GITHUB_RUN_ATTEMPT", "")).strip(),
        environment=environment,
        status=str(args.status or "in_progress").strip(),
        deployment_url=deployment_url,
        started_at=str(args.started_at or "").strip(),
        completed_at=str(args.completed_at or "").strip(),
        commit_sha=os.getenv("GITHUB_SHA", "").strip(),
        pr_number=str(args.pr_number or "").strip(),
    )
    return {
        "project_name": project_name,
        "run_id": run_id,
        "mode": "deploy",
        "deploy_run": {
            "workflow_run_id": deploy_run.get("workflow_run_id", ""),
            "build_id": deploy_run.get("build_id", ""),
            "status": deploy_run.get("status", ""),
            "environment": deploy_run.get("environment", ""),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update folder workflow evidence from CI/deploy context.")
    parser.add_argument("--artifact-root", action="append", default=[], help="Explicit artifact root to update.")
    parser.add_argument("--event-path", default="", help="GitHub event payload path.")
    parser.add_argument("--mode", choices=["ci", "deploy"], default="ci")
    parser.add_argument("--sync-linear", action="store_true", help="Create Linear issues from execution_plan.json.")
    parser.add_argument("--team-id", default="")
    parser.add_argument("--priority", type=int, default=0)
    parser.add_argument("--project-id", default="")
    parser.add_argument("--state-id", default="")
    parser.add_argument("--environment", default="")
    parser.add_argument("--deployment-system", default="github_actions")
    parser.add_argument("--workflow-file", default="")
    parser.add_argument("--build-id", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--deployment-url", default="")
    parser.add_argument("--started-at", default="")
    parser.add_argument("--completed-at", default="")
    parser.add_argument("--pr-number", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    artifact_roots = _discover_artifact_roots(REPO_ROOT, args.artifact_root)
    if not artifact_roots:
        print("Folder workflow evidence update skipped: no artifact roots provided.")
        return 0

    event_payload = _load_event_payload(args.event_path)
    summaries: list[dict[str, Any]] = []
    failures: list[str] = []

    for artifact_root in artifact_roots:
        try:
            binding = _resolve_run_binding(artifact_root)
            if args.mode == "deploy":
                summaries.append(_run_deploy_mode(binding, args))
            else:
                summaries.append(_run_ci_mode(binding, args, event_payload))
        except Exception as exc:
            failures.append(f"{artifact_root}: {exc}")

    print(json.dumps({"updated": summaries, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
