#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMENT_MARKER = "<!-- folder-workflow-evidence-summary -->"


def _discover_artifact_roots(repo_root: Path, provided_roots: list[str]) -> list[Path]:
    if provided_roots:
        return [Path(root).resolve() for root in provided_roots]
    return sorted(
        path.parent.resolve() for path in repo_root.rglob("release_bundle.json") if path.parent.name == "artifacts"
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _load_payload(path: Path) -> dict[str, Any]:
    envelope = _load_json(path)
    payload = envelope.get("payload", envelope)
    return payload if isinstance(payload, dict) else {}


def _bool_icon(value: Any) -> str:
    return "PASS" if value is True else "FAIL" if value is False else "UNKNOWN"


def _fmt_list(items: list[str]) -> str:
    return ", ".join(item for item in items if item) or "none"


def _render_root_summary(artifact_root: Path) -> str:
    run_root = artifact_root.parent
    run_record = _load_json(run_root / "run_record.json")
    release_bundle = _load_payload(artifact_root / "release_bundle.json")
    release_readiness = _load_payload(artifact_root / "release_readiness.json")
    linear_plan = _load_payload(artifact_root / "linear_plan.json")
    deploy_run = _load_payload(artifact_root / "deploy_run.json")
    post_deploy = _load_payload(artifact_root / "post_deploy_report.json")

    project_name = str(run_record.get("project_name", "")).strip() or "unknown-project"
    run_id = str(run_record.get("run_id", "")).strip() or run_root.name
    lines = [
        f"### `{project_name}` / `{run_id}`",
        "",
        f"- Status: `{run_record.get('status', 'unknown')}`",
        f"- Target: `{run_record.get('target_path', '')}`",
        f"- Commit: `{release_bundle.get('commit_sha', '') or 'n/a'}`",
        f"- PR: `{release_bundle.get('pr_number', '') or 'n/a'}`",
        f"- Linear: `{_fmt_list([str(item) for item in release_bundle.get('linear_issue_keys', [])])}`",
        f"- Release ready: `{release_readiness.get('ready', False)}`",
    ]

    blocking = release_readiness.get("blocking_checks", [])
    if blocking:
        lines.append(f"- Blocking checks: `{_fmt_list([str(item) for item in blocking])}`")

    deploy_ref = release_bundle.get("deployment_reference", {})
    if isinstance(deploy_ref, dict) and any(
        str(deploy_ref.get(key, "")).strip() for key in ("workflow_run_id", "build_id", "deployment_url")
    ):
        lines.extend(
            [
                f"- Deploy run: `{deploy_ref.get('workflow_run_id', '') or 'n/a'}`",
                f"- Build id: `{deploy_ref.get('build_id', '') or 'n/a'}`",
                f"- Deploy status: `{deploy_ref.get('status', '') or 'n/a'}`",
            ]
        )

    if linear_plan:
        parent_issue = linear_plan.get("parent_issue") or {}
        lines.append(
            f"- Linear plan: parent `{parent_issue.get('identifier', '') or 'n/a'}`, child issues `{len(linear_plan.get('child_issues', []))}`"
        )

    if deploy_run:
        lines.append(f"- Deployment system: `{deploy_run.get('deployment_system', '') or 'n/a'}`")

    if post_deploy:
        checks = post_deploy.get("checks", {})
        if isinstance(checks, dict) and checks:
            check_summary = ", ".join(f"{key}={_bool_icon(value)}" for key, value in sorted(checks.items()))
            lines.append(f"- Post deploy: `{post_deploy.get('status', 'n/a')}`")
            lines.append(f"- Post-deploy checks: `{check_summary}`")

    return "\n".join(lines)


def build_summary(artifact_roots: list[Path]) -> str:
    if not artifact_roots:
        return f"{COMMENT_MARKER}\n## Folder Workflow Evidence\n\nNo folder workflow artifacts found."

    sections = [COMMENT_MARKER, "## Folder Workflow Evidence", ""]
    for artifact_root in artifact_roots:
        sections.append(_render_root_summary(artifact_root))
        sections.append("")
    return "\n".join(sections).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render folder workflow evidence summary markdown.")
    parser.add_argument("--artifact-root", action="append", default=[], help="Explicit artifact root to summarize.")
    parser.add_argument("--output-file", default="", help="Optional markdown output file.")
    parser.add_argument("--write-step-summary", action="store_true", help="Append markdown to GITHUB_STEP_SUMMARY.")
    args = parser.parse_args(argv)

    artifact_roots = _discover_artifact_roots(REPO_ROOT, args.artifact_root)
    markdown = build_summary(artifact_roots)

    if args.output_file:
        Path(args.output_file).write_text(markdown, encoding="utf-8")

    if args.write_step_summary:
        step_summary_path = os.getenv("GITHUB_STEP_SUMMARY", "").strip()
        if step_summary_path:
            summary_path = Path(step_summary_path)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(markdown, encoding="utf-8")

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
