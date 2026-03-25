from __future__ import annotations

import json
from typing import Any

from python.helpers import project_lifecycle
from python.helpers.tool import Response, Tool


class ProjectLifecycle(Tool):
    """
    Project lifecycle automation across design/development/testing/validation/agent-eval phases.

    Actions:
    - get
    - upsert
    - set_phase
    - set_access
    - link_subproject
    - run_phase
    - list_phase_runs
    - start_folder_workflow
    - approve_folder_gate
    - build_folder_release_bundle
    - validate_folder_release_readiness
    - record_folder_post_deploy
    - finalize_folder_workflow
    - add_phase_schedule
    - remove_phase_schedule
    """

    async def execute(self, **kwargs) -> Response:
        action = str(self.args.get("action", "")).strip().lower()
        project_name = str(self.args.get("project_name", "")).strip()
        actor = str(self.args.get("actor", "system")).strip() or "system"
        if not project_name:
            return Response(message="Error: project_name is required", break_loop=False)

        try:
            if action == "get":
                data = project_lifecycle.load_lifecycle(project_name)
                return Response(
                    message=f"Loaded lifecycle for project '{project_name}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "lifecycle": data},
                )

            if action == "upsert":
                patch = self.args.get("lifecycle")
                patch_obj = self._parse_json_obj(patch)
                data = project_lifecycle.upsert_lifecycle(project_name, patch_obj, actor=actor)
                return Response(
                    message=f"Updated lifecycle for project '{project_name}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "lifecycle": data},
                )

            if action == "set_phase":
                phase = str(self.args.get("phase", "")).strip()
                if not phase:
                    raise Exception("phase is required")
                data = project_lifecycle.set_phase(project_name, phase=phase, actor=actor)
                return Response(
                    message=f"Set current phase to '{phase}' for '{project_name}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "lifecycle": data},
                )

            if action == "set_access":
                owner = self.args.get("owner")
                collaborators = self.args.get("collaborators")
                collab_list: list[str] | None = None
                if collaborators is not None:
                    if isinstance(collaborators, str):
                        collab_list = [c.strip() for c in collaborators.split(",") if c.strip()]
                    elif isinstance(collaborators, list):
                        collab_list = [str(c).strip() for c in collaborators if str(c).strip()]
                    else:
                        raise Exception("collaborators must be an array or comma-separated string")

                data = project_lifecycle.set_access(
                    project_name,
                    owner=str(owner).strip() if owner is not None else None,
                    collaborators=collab_list,
                    actor=actor,
                )
                return Response(
                    message=f"Updated access policy for project '{project_name}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "lifecycle": data},
                )

            if action == "link_subproject":
                subproject_name = str(self.args.get("subproject_name", "")).strip()
                if not subproject_name:
                    raise Exception("subproject_name is required")
                data = project_lifecycle.link_subproject(project_name, subproject_name=subproject_name, actor=actor)
                return Response(
                    message=f"Linked subproject '{subproject_name}' to '{project_name}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "lifecycle": data},
                )

            if action == "run_phase":
                phase = str(self.args.get("phase", "")).strip()
                if not phase:
                    raise Exception("phase is required")
                options = project_lifecycle.PhaseRunOptions(
                    run_visual=str(self.args.get("run_visual", "true")).strip().lower() in {"1", "true", "yes", "on"},
                    actor=actor,
                )
                run = project_lifecycle.run_phase(project_name, phase=phase, options=options)
                status = str(run.get("status", "")).strip().lower() or "unknown"
                message = (
                    f"Lifecycle phase run completed for '{project_name}' phase '{phase}'. "
                    f"Run ID: {run.get('run_id')} | Status: {status}"
                )
                if status == "failed" and run.get("error"):
                    message += f" | Error: {run.get('error')}"
                return Response(
                    message=message,
                    break_loop=False,
                    additional={"project_name": project_name, "run": run},
                )

            if action == "list_phase_runs":
                phase = str(self.args.get("phase", "")).strip()
                limit = int(self.args.get("limit", 25) or 25)
                runs = project_lifecycle.list_phase_runs(project_name, phase=phase, limit=limit)
                return Response(
                    message=f"Found {len(runs)} lifecycle runs for '{project_name}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "runs": runs},
                )

            if action == "start_folder_workflow":
                target_path = str(self.args.get("target_path", "")).strip()
                if not target_path:
                    raise Exception("target_path is required")
                scope = self.args.get("scope")
                constraints = self.args.get("constraints")
                if scope is not None and not isinstance(scope, dict):
                    raise Exception("scope must be an object when provided")
                if constraints is not None and not isinstance(constraints, dict):
                    raise Exception("constraints must be an object when provided")
                run = project_lifecycle.start_folder_workflow(
                    project_name=project_name,
                    target_path=target_path,
                    actor=actor,
                    scope=scope if isinstance(scope, dict) else None,
                    constraints=constraints if isinstance(constraints, dict) else None,
                    deploy_environment=str(self.args.get("deploy_environment", "")).strip(),
                    branch_ref=str(self.args.get("branch_ref", "")).strip(),
                    max_parallelism=int(self.args.get("max_parallelism", 1) or 1),
                )
                return Response(
                    message=(
                        f"Started folder delivery workflow '{run['run_id']}' for project '{project_name}' "
                        f"target '{run['target_path']}'."
                    ),
                    break_loop=False,
                    additional={"project_name": project_name, "run": run},
                )

            if action == "approve_folder_gate":
                run_id = str(self.args.get("run_id", "")).strip()
                gate_name = str(self.args.get("gate_name", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                if not gate_name:
                    raise Exception("gate_name is required")
                evidence_refs = self.args.get("evidence_refs")
                if evidence_refs is not None and not isinstance(evidence_refs, list):
                    raise Exception("evidence_refs must be an array when provided")
                decision = project_lifecycle.approve_folder_gate(
                    project_name=project_name,
                    run_id=run_id,
                    gate_name=gate_name,
                    approved_by=actor,
                    approved=self._to_bool(self.args.get("approved", True)),
                    evidence_refs=[str(item) for item in evidence_refs] if isinstance(evidence_refs, list) else None,
                    rejection_reason=str(self.args.get("rejection_reason", "")).strip(),
                )
                return Response(
                    message=f"Recorded gate decision for '{gate_name}' on workflow run '{run_id}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "gate_decision": decision},
                )

            if action == "build_folder_release_bundle":
                run_id = str(self.args.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                linear_issue_keys = self.args.get("linear_issue_keys")
                if linear_issue_keys is not None and not isinstance(linear_issue_keys, list):
                    raise Exception("linear_issue_keys must be an array when provided")
                data = project_lifecycle.build_folder_release_bundle(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    commit_sha=str(self.args.get("commit_sha", "")).strip(),
                    pr_number=str(self.args.get("pr_number", "")).strip(),
                    linear_issue_keys=[str(item).strip() for item in linear_issue_keys]
                    if isinstance(linear_issue_keys, list)
                    else None,
                    deploy_target=str(self.args.get("deploy_target", "")).strip(),
                    pre_deploy_checks=self.args.get("pre_deploy_checks")
                    if isinstance(self.args.get("pre_deploy_checks"), dict)
                    else None,
                    post_deploy_checks=self.args.get("post_deploy_checks")
                    if isinstance(self.args.get("post_deploy_checks"), dict)
                    else None,
                    monitoring_snapshot=self.args.get("monitoring_snapshot")
                    if isinstance(self.args.get("monitoring_snapshot"), dict)
                    else None,
                    rollback_plan=self.args.get("rollback_plan")
                    if isinstance(self.args.get("rollback_plan"), dict)
                    else None,
                )
                return Response(
                    message=f"Built release bundle for workflow run '{run_id}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "release_bundle": data},
                )

            if action == "validate_folder_release_readiness":
                run_id = str(self.args.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                required_observers = self.args.get("required_observers")
                if required_observers is not None and not isinstance(required_observers, list):
                    raise Exception("required_observers must be an array when provided")
                data = project_lifecycle.validate_folder_release_readiness(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    required_observers=[str(item).strip() for item in required_observers]
                    if isinstance(required_observers, list)
                    else None,
                )
                return Response(
                    message=f"Validated release readiness for workflow run '{run_id}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "release_readiness": data},
                )

            if action == "record_folder_post_deploy":
                run_id = str(self.args.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                data = project_lifecycle.record_folder_post_deploy(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    checks=self.args.get("checks") if isinstance(self.args.get("checks"), dict) else None,
                    status=str(self.args.get("status", "healthy")).strip() or "healthy",
                    rollback_triggered=self._to_bool(self.args.get("rollback_triggered", False)),
                    observation_window=self.args.get("observation_window")
                    if isinstance(self.args.get("observation_window"), dict)
                    else None,
                    monitoring_snapshot=self.args.get("monitoring_snapshot")
                    if isinstance(self.args.get("monitoring_snapshot"), dict)
                    else None,
                )
                return Response(
                    message=f"Recorded post-deploy evidence for workflow run '{run_id}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "post_deploy_report": data},
                )

            if action == "finalize_folder_workflow":
                run_id = str(self.args.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                run = project_lifecycle.finalize_folder_workflow(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    status=str(self.args.get("status", "completed")).strip() or "completed",
                )
                return Response(
                    message=f"Finalized workflow run '{run_id}' with status '{run['status']}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "run": run},
                )

            if action == "add_phase_schedule":
                phase = str(self.args.get("phase", "")).strip()
                cron = str(self.args.get("cron", "")).strip()
                if not phase:
                    raise Exception("phase is required")
                if not cron:
                    raise Exception("cron is required")
                run_visual = str(self.args.get("run_visual", "true")).strip().lower() in {"1", "true", "yes", "on"}
                timezone_name = str(self.args.get("timezone", "")).strip() or None
                data = await project_lifecycle.add_phase_schedule(
                    project_name,
                    phase=phase,
                    cron=cron,
                    timezone_name=timezone_name,
                    run_visual=run_visual,
                    actor=actor,
                )
                return Response(
                    message=f"Created schedule for '{project_name}' phase '{phase}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "schedule": data},
                )

            if action == "remove_phase_schedule":
                phase = str(self.args.get("phase", "")).strip()
                if not phase:
                    raise Exception("phase is required")
                data = await project_lifecycle.remove_phase_schedule(project_name, phase=phase, actor=actor)
                return Response(
                    message=f"Removed schedule for '{project_name}' phase '{phase}'.",
                    break_loop=False,
                    additional={"project_name": project_name, "schedule": data},
                )

            return Response(
                message=(
                    "Unknown action. Use one of: get, upsert, set_phase, set_access, "
                    "link_subproject, run_phase, list_phase_runs, start_folder_workflow, "
                    "approve_folder_gate, build_folder_release_bundle, validate_folder_release_readiness, "
                    "record_folder_post_deploy, finalize_folder_workflow, add_phase_schedule, remove_phase_schedule"
                ),
                break_loop=False,
            )
        except Exception as exc:
            return Response(message=f"Project lifecycle error: {exc}", break_loop=False)

    def _parse_json_obj(self, raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str) and raw.strip():
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        raise Exception("Expected JSON object payload")

    @staticmethod
    def _to_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)
