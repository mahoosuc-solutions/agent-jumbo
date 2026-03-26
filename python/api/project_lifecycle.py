from __future__ import annotations

from python.helpers import project_lifecycle
from python.helpers.api import ApiHandler, Input, Output, Request


class ProjectLifecycle(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        action = str(input.get("action", "")).strip().lower()
        project_name = str(input.get("project_name", "")).strip()
        actor = str(input.get("actor", "system")).strip() or "system"

        if not project_name:
            return {"ok": False, "error": "project_name is required"}

        try:
            if action == "get":
                data = project_lifecycle.load_lifecycle(project_name)
            elif action == "upsert":
                patch = input.get("lifecycle")
                if not isinstance(patch, dict):
                    raise Exception("lifecycle is required and must be an object")
                data = project_lifecycle.upsert_lifecycle(project_name, patch=patch, actor=actor)
            elif action == "set_phase":
                phase = str(input.get("phase", "")).strip()
                if not phase:
                    raise Exception("phase is required")
                data = project_lifecycle.set_phase(project_name, phase=phase, actor=actor)
            elif action == "set_access":
                owner = input.get("owner")
                collaborators = input.get("collaborators")
                if collaborators is not None and not isinstance(collaborators, list):
                    raise Exception("collaborators must be an array of usernames")
                data = project_lifecycle.set_access(
                    project_name,
                    owner=str(owner) if owner is not None else None,
                    collaborators=[str(c) for c in collaborators] if isinstance(collaborators, list) else None,
                    actor=actor,
                )
            elif action == "link_subproject":
                subproject_name = str(input.get("subproject_name", "")).strip()
                if not subproject_name:
                    raise Exception("subproject_name is required")
                data = project_lifecycle.link_subproject(
                    project_name,
                    subproject_name=subproject_name,
                    actor=actor,
                )
            elif action == "run_phase":
                phase = str(input.get("phase", "")).strip()
                if not phase:
                    raise Exception("phase is required")
                options = project_lifecycle.PhaseRunOptions(
                    run_visual=bool(input.get("run_visual", True)),
                    actor=actor,
                )
                data = project_lifecycle.run_phase(project_name, phase=phase, options=options)
            elif action == "list_phase_runs":
                phase = str(input.get("phase", "")).strip()
                limit = int(input.get("limit", 25) or 25)
                data = project_lifecycle.list_phase_runs(project_name, phase=phase, limit=limit)
            elif action == "start_folder_workflow":
                target_path = str(input.get("target_path", "")).strip()
                if not target_path:
                    raise Exception("target_path is required")
                scope = input.get("scope")
                constraints = input.get("constraints")
                if scope is not None and not isinstance(scope, dict):
                    raise Exception("scope must be an object when provided")
                if constraints is not None and not isinstance(constraints, dict):
                    raise Exception("constraints must be an object when provided")
                data = project_lifecycle.start_folder_workflow(
                    project_name=project_name,
                    target_path=target_path,
                    actor=actor,
                    scope=scope if isinstance(scope, dict) else None,
                    constraints=constraints if isinstance(constraints, dict) else None,
                    deploy_environment=str(input.get("deploy_environment", "")).strip(),
                    branch_ref=str(input.get("branch_ref", "")).strip(),
                    max_parallelism=int(input.get("max_parallelism", 1) or 1),
                )
            elif action == "approve_folder_gate":
                run_id = str(input.get("run_id", "")).strip()
                gate_name = str(input.get("gate_name", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                if not gate_name:
                    raise Exception("gate_name is required")
                evidence_refs = input.get("evidence_refs")
                if evidence_refs is not None and not isinstance(evidence_refs, list):
                    raise Exception("evidence_refs must be an array when provided")
                data = project_lifecycle.approve_folder_gate(
                    project_name=project_name,
                    run_id=run_id,
                    gate_name=gate_name,
                    approved_by=actor,
                    approved=bool(input.get("approved", True)),
                    evidence_refs=[str(item) for item in evidence_refs] if isinstance(evidence_refs, list) else None,
                    rejection_reason=str(input.get("rejection_reason", "")).strip(),
                )
            elif action == "build_folder_release_bundle":
                run_id = str(input.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                linear_issue_keys = input.get("linear_issue_keys")
                if linear_issue_keys is not None and not isinstance(linear_issue_keys, list):
                    raise Exception("linear_issue_keys must be an array when provided")
                data = project_lifecycle.build_folder_release_bundle(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    commit_sha=str(input.get("commit_sha", "")).strip(),
                    pr_number=str(input.get("pr_number", "")).strip(),
                    linear_issue_keys=[str(item) for item in linear_issue_keys]
                    if isinstance(linear_issue_keys, list)
                    else None,
                    deploy_target=str(input.get("deploy_target", "")).strip(),
                    pre_deploy_checks=input.get("pre_deploy_checks")
                    if isinstance(input.get("pre_deploy_checks"), dict)
                    else None,
                    post_deploy_checks=input.get("post_deploy_checks")
                    if isinstance(input.get("post_deploy_checks"), dict)
                    else None,
                    monitoring_snapshot=input.get("monitoring_snapshot")
                    if isinstance(input.get("monitoring_snapshot"), dict)
                    else None,
                    rollback_plan=input.get("rollback_plan") if isinstance(input.get("rollback_plan"), dict) else None,
                )
            elif action == "sync_folder_linear_plan":
                run_id = str(input.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                data = project_lifecycle.sync_folder_linear_plan(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    team_id=str(input.get("team_id", "")).strip(),
                    default_priority=int(input.get("priority", 0) or 0),
                    project_id=str(input.get("project_id", "")).strip(),
                    state_id=str(input.get("state_id", "")).strip(),
                )
            elif action == "validate_folder_release_readiness":
                run_id = str(input.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                required_observers = input.get("required_observers")
                if required_observers is not None and not isinstance(required_observers, list):
                    raise Exception("required_observers must be an array when provided")
                data = project_lifecycle.validate_folder_release_readiness(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    required_observers=[str(item) for item in required_observers]
                    if isinstance(required_observers, list)
                    else None,
                )
            elif action == "record_folder_deploy_run":
                run_id = str(input.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                data = project_lifecycle.record_folder_deploy_run(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    deployment_system=str(input.get("deployment_system", "")).strip(),
                    repository=str(input.get("repository", "")).strip(),
                    workflow_file=str(input.get("workflow_file", "")).strip(),
                    workflow_run_id=str(input.get("workflow_run_id", "")).strip(),
                    build_id=str(input.get("build_id", "")).strip(),
                    environment=str(input.get("environment", "")).strip(),
                    status=str(input.get("status", "")).strip(),
                    deployment_url=str(input.get("deployment_url", "")).strip(),
                    started_at=str(input.get("started_at", "")).strip(),
                    completed_at=str(input.get("completed_at", "")).strip(),
                    commit_sha=str(input.get("commit_sha", "")).strip(),
                    pr_number=str(input.get("pr_number", "")).strip(),
                )
            elif action == "record_folder_post_deploy":
                run_id = str(input.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                data = project_lifecycle.record_folder_post_deploy(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    checks=input.get("checks") if isinstance(input.get("checks"), dict) else None,
                    status=str(input.get("status", "healthy")).strip() or "healthy",
                    rollback_triggered=bool(input.get("rollback_triggered", False)),
                    observation_window=input.get("observation_window")
                    if isinstance(input.get("observation_window"), dict)
                    else None,
                    monitoring_snapshot=input.get("monitoring_snapshot")
                    if isinstance(input.get("monitoring_snapshot"), dict)
                    else None,
                )
            elif action == "finalize_folder_workflow":
                run_id = str(input.get("run_id", "")).strip()
                if not run_id:
                    raise Exception("run_id is required")
                data = project_lifecycle.finalize_folder_workflow(
                    project_name=project_name,
                    run_id=run_id,
                    actor=actor,
                    status=str(input.get("status", "completed")).strip() or "completed",
                )
            elif action == "add_phase_schedule":
                phase = str(input.get("phase", "")).strip()
                cron = str(input.get("cron", "")).strip()
                if not phase:
                    raise Exception("phase is required")
                if not cron:
                    raise Exception("cron is required")
                timezone_name = str(input.get("timezone", "")).strip() or None
                run_visual = bool(input.get("run_visual", True))
                data = await project_lifecycle.add_phase_schedule(
                    project_name,
                    phase=phase,
                    cron=cron,
                    timezone_name=timezone_name,
                    run_visual=run_visual,
                    actor=actor,
                )
            elif action == "remove_phase_schedule":
                phase = str(input.get("phase", "")).strip()
                if not phase:
                    raise Exception("phase is required")
                data = await project_lifecycle.remove_phase_schedule(
                    project_name,
                    phase=phase,
                    actor=actor,
                )
            else:
                raise Exception("Invalid action")

            return {"ok": True, "data": data}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
