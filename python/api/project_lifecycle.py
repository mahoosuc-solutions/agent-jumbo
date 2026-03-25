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
