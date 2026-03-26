from __future__ import annotations

from python.helpers import portfolio_rollout
from python.helpers.api import ApiHandler, Input, Output, Request


class PortfolioRollout(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        action = str(input.get("action", "dashboard")).strip().lower() or "dashboard"
        actor = str(input.get("actor", "system")).strip() or "system"

        try:
            if action == "dashboard":
                data = portfolio_rollout.get_rollout_dashboard()
            elif action == "product_workspace":
                product_slug = str(input.get("product_slug", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                data = portfolio_rollout.get_product_workspace(product_slug=product_slug, actor=actor)
            elif action == "resolve_target":
                product_slug = str(input.get("product_slug", "")).strip()
                target_path = str(input.get("target_path", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                if not target_path:
                    raise Exception("target_path is required")
                data = portfolio_rollout.set_product_target(
                    product_slug=product_slug,
                    target_path=target_path,
                    actor=actor,
                )
            elif action == "start_planning":
                product_slug = str(input.get("product_slug", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                data = portfolio_rollout.start_product_planning(
                    product_slug=product_slug,
                    actor=actor,
                    branch_ref=str(input.get("branch_ref", "")).strip(),
                    deploy_environment=str(input.get("deploy_environment", "")).strip(),
                )
            elif action == "draft_artifact":
                product_slug = str(input.get("product_slug", "")).strip()
                artifact_name = str(input.get("artifact_name", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                if not artifact_name:
                    raise Exception("artifact_name is required")
                data = portfolio_rollout.start_artifact_draft_job(
                    product_slug=product_slug,
                    artifact_name=artifact_name,
                    actor=actor,
                    agent_provider=str(input.get("agent_provider", "codex")).strip().lower() or "codex",
                )
            elif action == "start_product_planning_job":
                product_slug = str(input.get("product_slug", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                data = portfolio_rollout.start_product_planning_job(
                    product_slug=product_slug,
                    actor=actor,
                    agent_provider=str(input.get("agent_provider", "codex")).strip().lower() or "codex",
                )
            elif action == "get_artifact_draft_job":
                product_slug = str(input.get("product_slug", "")).strip()
                job_id = str(input.get("job_id", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                if not job_id:
                    raise Exception("job_id is required")
                data = portfolio_rollout.get_artifact_draft_job(
                    product_slug=product_slug,
                    job_id=job_id,
                    actor=actor,
                )
            elif action == "get_planning_job":
                product_slug = str(input.get("product_slug", "")).strip()
                job_id = str(input.get("job_id", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                if not job_id:
                    raise Exception("job_id is required")
                data = portfolio_rollout.get_planning_job(
                    product_slug=product_slug,
                    job_id=job_id,
                    actor=actor,
                )
            elif action == "list_planning_jobs":
                product_slug = str(input.get("product_slug", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                data = portfolio_rollout.list_planning_jobs(
                    product_slug=product_slug,
                    actor=actor,
                )
            elif action == "cancel_artifact_draft_job":
                product_slug = str(input.get("product_slug", "")).strip()
                job_id = str(input.get("job_id", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                if not job_id:
                    raise Exception("job_id is required")
                data = portfolio_rollout.cancel_artifact_draft_job(
                    product_slug=product_slug,
                    job_id=job_id,
                    actor=actor,
                )
            elif action == "cancel_planning_job":
                product_slug = str(input.get("product_slug", "")).strip()
                job_id = str(input.get("job_id", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                if not job_id:
                    raise Exception("job_id is required")
                data = portfolio_rollout.cancel_planning_job(
                    product_slug=product_slug,
                    job_id=job_id,
                    actor=actor,
                )
            elif action == "rerun_planning_job":
                product_slug = str(input.get("product_slug", "")).strip()
                job_id = str(input.get("job_id", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                if not job_id:
                    raise Exception("job_id is required")
                data = portfolio_rollout.rerun_planning_job(
                    product_slug=product_slug,
                    job_id=job_id,
                    actor=actor,
                    agent_provider=str(input.get("agent_provider", "")).strip().lower(),
                )
            elif action == "save_artifact":
                product_slug = str(input.get("product_slug", "")).strip()
                artifact_name = str(input.get("artifact_name", "")).strip()
                payload = input.get("payload")
                if not product_slug:
                    raise Exception("product_slug is required")
                if not artifact_name:
                    raise Exception("artifact_name is required")
                if not isinstance(payload, dict):
                    raise Exception("payload must be an object")
                data = portfolio_rollout.save_planning_artifact(
                    product_slug=product_slug,
                    artifact_name=artifact_name,
                    payload=payload,
                    actor=actor,
                    producer=str(input.get("producer", "human")).strip() or "human",
                )
            elif action == "approve_artifact":
                product_slug = str(input.get("product_slug", "")).strip()
                artifact_name = str(input.get("artifact_name", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                if not artifact_name:
                    raise Exception("artifact_name is required")
                data = portfolio_rollout.approve_planning_artifact(
                    product_slug=product_slug,
                    artifact_name=artifact_name,
                    approved=bool(input.get("approved", True)),
                    actor=actor,
                    notes=str(input.get("notes", "")).strip(),
                )
            elif action == "approve_bundle":
                product_slug = str(input.get("product_slug", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                data = portfolio_rollout.approve_planning_bundle(
                    product_slug=product_slug,
                    approved=bool(input.get("approved", True)),
                    actor=actor,
                    notes=str(input.get("notes", "")).strip(),
                    acknowledge_repo_diff=bool(input.get("acknowledge_repo_diff", False)),
                )
            elif action == "sync_linear":
                product_slug = str(input.get("product_slug", "")).strip()
                if not product_slug:
                    raise Exception("product_slug is required")
                data = portfolio_rollout.sync_product_linear_plan(
                    product_slug=product_slug,
                    actor=actor,
                    team_id=str(input.get("team_id", "")).strip(),
                    project_id=str(input.get("project_id", "")).strip(),
                    state_id=str(input.get("state_id", "")).strip(),
                    default_priority=int(input.get("priority", 0) or 0),
                )
            else:
                raise Exception("Invalid action")
            return {"ok": True, "data": data}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
