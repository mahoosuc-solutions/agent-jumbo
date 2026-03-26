from __future__ import annotations

import json
from typing import Any

from python.helpers import files

from .opportunities_db import OpportunitiesDatabase
from .source_adapters import get_adapter
from .territory_seed import TERRITORY_PROFILES

VALID_STAGES = {
    "discovered",
    "normalized",
    "qualified",
    "estimated",
    "approved_for_solutioning",
    "solutioning",
    "proposal_ready",
    "submitted",
    "won",
    "lost",
    "archived",
}
VALID_LANES = {"discovery", "qualification", "estimation", "solutioning"}
VALID_RECOMMENDATIONS = {"pursue", "watch", "pass"}
VALID_APPROVAL = {"pending", "approved", "rejected"}
TERRITORY_STATUSES = {"planned", "active", "covered", "refresh", "paused"}

MUST_HAVE_RULES = [
    ("FHIR interoperability", ("fhir", "hl7", "interoperability")),
    ("Security and compliance", ("security", "secure", "hipaa", "compliance", "soc 2", "audit")),
    ("Analytics and reporting", ("dashboard", "analytics", "reporting", "quality measure")),
    ("Workflow automation", ("workflow", "case management", "automation", "operator")),
    ("Integrations", ("integration", "api", "data exchange", "interface")),
]


def _clamp(value: float, lower: float = 0, upper: float = 100) -> float:
    return max(lower, min(upper, value))


class OpportunitiesManager:
    def __init__(self, db_path: str):
        self.db = OpportunitiesDatabase(db_path)

    def dashboard(self) -> dict[str, Any]:
        data = self.db.territory_dashboard()
        opportunities = self.db.list_opportunities()
        collector_runs = self.db.list_collector_runs(limit=50)
        for territory in data["territories"]:
            self._enrich_territory_profile(territory, collector_runs)
            territory["next_action"] = self._territory_next_action(territory)
        lane_counts = dict.fromkeys(VALID_LANES, 0)
        for opportunity in opportunities:
            lane_counts[opportunity["lane"]] = lane_counts.get(opportunity["lane"], 0) + 1
        data["lane_counts"] = lane_counts
        data["lane_board"] = {
            lane: {
                "count": lane_counts.get(lane, 0),
                "items": [opportunity for opportunity in opportunities if opportunity["lane"] == lane][:5],
            }
            for lane in VALID_LANES
        }
        data["collector_schedule"] = self.get_collector_schedule()
        data["collector_runs"] = self.db.list_collector_runs(limit=8)
        data["recent"] = opportunities[:8]
        return data

    def list_territories(self, status: str | None = None) -> list[dict[str, Any]]:
        territories = self.db.territory_dashboard()["territories"]
        if status:
            territories = [territory for territory in territories if territory.get("status") == status]
        collector_runs = self.db.list_collector_runs(limit=50)
        for territory in territories:
            self._enrich_territory_profile(territory, collector_runs)
        return territories

    def set_territory_status(self, territory_id: int, status: str) -> bool:
        if status not in TERRITORY_STATUSES:
            raise ValueError(f"invalid territory status: {status}")
        return self.db.update_territory_status(territory_id, status)

    def list_opportunities(
        self,
        territory_id: int | None = None,
        stage: str | None = None,
        lane: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.db.list_opportunities(territory_id=territory_id, stage=stage, lane=lane, search=search)

    def get_opportunity(self, opportunity_id: int) -> dict[str, Any] | None:
        return self.db.get_opportunity(opportunity_id)

    def create_opportunity(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._validate_payload(payload, stage="discovered", lane_default="discovery")

    def import_opportunities(self, payloads: list[dict[str, Any]], auto_qualify: bool = True) -> dict[str, Any]:
        created = 0
        updated = 0
        qualified = 0
        imported: list[dict[str, Any]] = []

        for payload in payloads:
            opportunity_payload = self._build_payload(payload, stage="discovered", lane_default="discovery")
            opportunity, was_created = self.db.create_or_update_opportunity(opportunity_payload)
            if auto_qualify:
                opportunity = self.qualify_opportunity(opportunity["id"])
                qualified += 1
            imported.append(opportunity)
            if was_created:
                created += 1
            else:
                updated += 1

        return {
            "created": created,
            "updated": updated,
            "qualified": qualified,
            "opportunities": imported,
        }

    def run_collectors(self, collectors: list[dict[str, Any]], auto_qualify: bool = True) -> dict[str, Any]:
        runs: list[dict[str, Any]] = []
        total_created = 0
        total_updated = 0
        total_qualified = 0
        imported: list[dict[str, Any]] = []

        for collector in collectors:
            source_type = str(collector.get("adapter", "")).strip()
            collector_name = str(collector.get("name", "")).strip()
            run_id = self.db.start_collector_run(source_type, collector_name=collector_name)
            try:
                adapter = get_adapter(source_type)
                items = adapter.collect(collector.get("config", {}))
                result = self.import_opportunities(items, auto_qualify=auto_qualify)
                total_created += result["created"]
                total_updated += result["updated"]
                total_qualified += result["qualified"]
                imported.extend(result["opportunities"])
                self.db.finish_collector_run(
                    run_id,
                    status="ok",
                    items_received=len(items),
                    created_count=result["created"],
                    updated_count=result["updated"],
                    qualified_count=result["qualified"],
                )
                runs.append(
                    {
                        "adapter": source_type,
                        "collector_name": collector_name,
                        "status": "ok",
                        "items_received": len(items),
                        "created": result["created"],
                        "updated": result["updated"],
                        "qualified": result["qualified"],
                    }
                )
            except Exception as exc:
                self.db.finish_collector_run(run_id, status="error", error=str(exc))
                runs.append(
                    {
                        "adapter": source_type,
                        "collector_name": collector_name,
                        "status": "error",
                        "items_received": 0,
                        "created": 0,
                        "updated": 0,
                        "qualified": 0,
                        "error": str(exc),
                    }
                )

        return {
            "runs": runs,
            "created": total_created,
            "updated": total_updated,
            "qualified": total_qualified,
            "opportunities": imported,
            "errors": [run for run in runs if run["status"] == "error"],
        }

    def get_collector_schedule(self) -> dict[str, Any]:
        enabled = self.db.get_setting("collector_schedule_enabled", "false") == "true"
        cron = self.db.get_setting("collector_schedule_cron", "0 */6 * * *")
        task_uuid = self.db.get_setting("collector_schedule_task_uuid", "")
        raw_collectors = self.db.get_setting("collector_schedule_collectors", "[]")
        try:
            collectors = json.loads(raw_collectors)
        except Exception:
            collectors = []
        return {
            "enabled": enabled,
            "cron": cron,
            "task_uuid": task_uuid,
            "collectors": collectors if isinstance(collectors, list) else [],
        }

    async def schedule_collectors(self, cron: str, collectors: list[dict[str, Any]]) -> dict[str, Any]:
        try:
            from python.helpers.task_scheduler import ScheduledTask, TaskSchedule, TaskScheduler
        except ImportError:
            return {"success": False, "error": "Scheduler not available (crontab not installed)"}

        await self.unschedule_collectors()

        parts = cron.split()
        if len(parts) != 5:
            return {"success": False, "error": f"Invalid cron expression: {cron} (need 5 fields)"}

        schedule = TaskSchedule(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            weekday=parts[4],
        )
        collectors_json = json.dumps(collectors)
        prompt = (
            "Run the opportunities_update API with action='run_collectors' and auto_qualify=true. "
            f"Use collectors={collectors_json}. Report created, updated, and qualified counts."
        )
        task = ScheduledTask.create(
            name="Opportunity Collector Run",
            system_prompt=(
                "You are an intake automation agent. When triggered, run the configured opportunity "
                "collectors, feed normalized results into the opportunity dashboard, and report a concise summary."
            ),
            prompt=prompt,
            schedule=schedule,
        )

        scheduler = TaskScheduler.get()
        await scheduler.reload()
        await scheduler.add_task(task)

        self.db.set_setting("collector_schedule_enabled", "true")
        self.db.set_setting("collector_schedule_cron", cron)
        self.db.set_setting("collector_schedule_collectors", collectors_json)
        self.db.set_setting("collector_schedule_task_uuid", task.uuid)
        return {"success": True, "cron": cron, "task_uuid": task.uuid, "collectors": collectors}

    async def unschedule_collectors(self) -> dict[str, Any]:
        task_uuid = self.db.get_setting("collector_schedule_task_uuid", "")
        if task_uuid:
            try:
                from python.helpers.task_scheduler import TaskScheduler

                scheduler = TaskScheduler.get()
                await scheduler.reload()
                await scheduler.remove_task_by_uuid(task_uuid)
            except ImportError:
                pass
            except Exception as exc:
                return {"success": False, "error": f"Failed to remove collector schedule: {exc}"}

        self.db.set_setting("collector_schedule_enabled", "false")
        self.db.set_setting("collector_schedule_task_uuid", "")
        return {"success": True}

    def _validate_payload(self, payload: dict[str, Any], stage: str, lane_default: str) -> dict[str, Any]:
        return self.db.create_opportunity(self._build_payload(payload, stage=stage, lane_default=lane_default))

    def _build_payload(self, payload: dict[str, Any], stage: str, lane_default: str) -> dict[str, Any]:
        territory_id = int(payload.get("territory_id") or 0)
        if territory_id <= 0:
            raise ValueError("territory_id is required")
        if not self.db.get_territory(territory_id):
            raise ValueError(f"territory {territory_id} not found")
        title = str(payload.get("title", "")).strip()
        if not title:
            raise ValueError("title is required")
        buyer_name = str(payload.get("buyer_name", "")).strip()
        if not buyer_name:
            raise ValueError("buyer_name is required")

        recommendation = str(payload.get("recommendation", "watch")).strip() or "watch"
        if recommendation not in VALID_RECOMMENDATIONS:
            raise ValueError(f"invalid recommendation: {recommendation}")

        lane = str(payload.get("lane", lane_default)).strip() or lane_default
        if lane not in VALID_LANES:
            raise ValueError(f"invalid lane: {lane}")

        return {
            "territory_id": territory_id,
            "title": title,
            "buyer_name": buyer_name,
            "source_type": str(payload.get("source_type", "manual")).strip() or "manual",
            "source_url": payload.get("source_url"),
            "external_id": payload.get("external_id"),
            "zip_code": str(payload.get("zip_code", "")).strip(),
            "city": str(payload.get("city", "")).strip(),
            "state": str(payload.get("state", "")).strip(),
            "stage": stage,
            "lane": lane or lane_default,
            "recommendation": recommendation,
            "approval_status": "pending",
            "raw_requirements": str(payload.get("raw_requirements", "")).strip(),
            "normalized_summary": str(payload.get("normalized_summary", "")).strip(),
            "must_have_requirements": payload.get("must_have_requirements", []),
            "due_date": payload.get("due_date"),
            "strategic_fit_score": float(payload.get("strategic_fit_score", 0)),
            "delivery_risk_score": float(payload.get("delivery_risk_score", 0)),
            "estimated_contract_value": float(payload.get("estimated_contract_value", 0)),
            "confidence_score": float(payload.get("confidence_score", 0)),
        }

    def update_opportunity(self, opportunity_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        if "stage" in updates and updates["stage"] not in VALID_STAGES:
            raise ValueError(f"invalid stage: {updates['stage']}")
        if "lane" in updates and updates["lane"] not in VALID_LANES:
            raise ValueError(f"invalid lane: {updates['lane']}")
        if "recommendation" in updates and updates["recommendation"] not in VALID_RECOMMENDATIONS:
            raise ValueError(f"invalid recommendation: {updates['recommendation']}")
        if "approval_status" in updates and updates["approval_status"] not in VALID_APPROVAL:
            raise ValueError(f"invalid approval_status: {updates['approval_status']}")
        ok = self.db.update_opportunity(opportunity_id, updates)
        if not ok:
            raise ValueError(f"opportunity {opportunity_id} not found or no valid updates provided")
        updated = self.db.get_opportunity(opportunity_id)
        if not updated:
            raise RuntimeError(f"failed to reload opportunity {opportunity_id}")
        return updated

    def save_estimate(self, opportunity_id: int, estimate: dict[str, Any]) -> dict[str, Any]:
        opportunity = self.db.get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError(f"opportunity {opportunity_id} not found")
        total_hours = float(estimate.get("total_hours", 0))
        timeline_weeks = int(estimate.get("timeline_weeks", 0))
        estimated_cost = float(estimate.get("estimated_cost", 0))
        roles = estimate.get("roles", [])
        milestones = estimate.get("milestones", [])
        if total_hours <= 0:
            raise ValueError("total_hours is required")
        if timeline_weeks <= 0:
            raise ValueError("timeline_weeks is required")
        if estimated_cost <= 0:
            raise ValueError("estimated_cost is required")
        if not roles:
            raise ValueError("roles are required")
        if not milestones:
            raise ValueError("milestones are required")

        saved = self.db.upsert_estimate(
            opportunity_id,
            {
                "total_hours": total_hours,
                "timeline_weeks": timeline_weeks,
                "estimated_cost": estimated_cost,
                "roles": roles,
                "milestones": milestones,
                "assumptions": estimate.get("assumptions", []),
                "risks": estimate.get("risks", []),
                "pricing_notes": str(estimate.get("pricing_notes", "")).strip(),
            },
        )
        self.db.update_opportunity(opportunity_id, {"stage": "estimated", "lane": "estimation"})
        return saved

    def qualify_opportunity(self, opportunity_id: int) -> dict[str, Any]:
        opportunity = self.db.get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError(f"opportunity {opportunity_id} not found")

        summary = self._normalized_summary(opportunity)
        must_haves = self._extract_must_haves(
            " ".join(
                filter(
                    None,
                    [
                        opportunity.get("title"),
                        opportunity.get("normalized_summary"),
                        opportunity.get("raw_requirements"),
                    ],
                )
            )
        )
        strategic_fit = self._strategic_fit_score(opportunity)
        delivery_risk = self._delivery_risk_score(opportunity)
        confidence = self._confidence_score(strategic_fit, delivery_risk, opportunity)
        recommendation = self._recommendation(strategic_fit, delivery_risk)

        stage = "qualified"
        lane = "qualification"
        if recommendation == "pursue" and strategic_fit >= 70:
            lane = "estimation"

        return self.update_opportunity(
            opportunity_id,
            {
                "normalized_summary": summary,
                "must_have_requirements": must_haves,
                "strategic_fit_score": strategic_fit,
                "delivery_risk_score": delivery_risk,
                "confidence_score": confidence,
                "recommendation": recommendation,
                "stage": stage,
                "lane": lane,
            },
        )

    def approve_for_solutioning(self, opportunity_id: int) -> dict[str, Any]:
        opportunity = self.db.get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError(f"opportunity {opportunity_id} not found")
        estimate = self.db.get_estimate(opportunity_id)
        if not estimate:
            raise ValueError("detailed estimate is required before approval")
        updated = self.update_opportunity(
            opportunity_id,
            {
                "approval_status": "approved",
                "stage": "approved_for_solutioning",
                "lane": "solutioning",
                "recommendation": "pursue" if opportunity["recommendation"] != "pass" else "pass",
            },
        )
        return updated

    def handoff_to_solutioning(self, opportunity_id: int) -> dict[str, Any]:
        opportunity = self.db.get_opportunity(opportunity_id)
        if not opportunity:
            raise ValueError(f"opportunity {opportunity_id} not found")
        if opportunity["approval_status"] != "approved":
            raise ValueError("opportunity must be approved before handoff")
        estimate = self.db.get_estimate(opportunity_id)
        if not estimate:
            raise ValueError("detailed estimate is required before handoff")

        from instruments.custom.ideas.ideas_manager import IdeasManager
        from instruments.custom.sales_generator.sales_manager import SalesGeneratorManager

        ideas_manager = IdeasManager(files.get_abs_path("./instruments/custom/ideas/data/ideas.db"))
        sales_manager = SalesGeneratorManager(files.get_abs_path("./instruments/custom/sales_generator/data/sales.db"))

        brief_lines = [
            f"Buyer: {opportunity['buyer_name']}",
            f"Metro cluster: {opportunity['metro_name']} / {opportunity['cluster_name']}",
            f"Territory zip: {opportunity.get('zip_code') or 'n/a'}",
            "",
            "Normalized requirements:",
            opportunity.get("normalized_summary") or "(none yet)",
            "",
            "Raw requirements:",
            opportunity.get("raw_requirements") or "(none yet)",
        ]
        idea = ideas_manager.create_idea(
            {
                "title": opportunity["title"],
                "raw_note": "\n".join(brief_lines).strip(),
                "summary": opportunity.get("normalized_summary") or opportunity["title"],
                "priority": "high" if opportunity.get("strategic_fit_score", 0) >= 70 else "medium",
                "theme": opportunity.get("metro_name", ""),
                "source": "opportunity",
            }
        )
        promoted = ideas_manager.promote_to_project(idea["id"])

        proposal_items = []
        for role in estimate["roles"]:
            proposal_items.append(
                {
                    "name": role.get("role", "Delivery Role"),
                    "description": role.get("description") or f"{role.get('hours', 0)}h delivery capacity",
                    "quantity": 1,
                    "unit_price": float(role.get("cost", 0)),
                    "type": "service",
                }
            )
        proposal = sales_manager.generate_proposal(
            title=f"{opportunity['title']} Proposal",
            customer_name=opportunity["buyer_name"],
            solution_summary=opportunity.get("normalized_summary") or opportunity["title"],
            items=proposal_items,
        )

        updated = self.update_opportunity(
            opportunity_id,
            {
                "linked_idea_id": idea["id"],
                "linked_project_name": promoted["idea"]["project_name"],
                "linked_workflow_name": promoted["workflow"]["name"],
                "linked_proposal_id": proposal["proposal_id"],
                "stage": "proposal_ready",
                "lane": "solutioning",
            },
        )
        return {
            "success": True,
            "opportunity": updated,
            "idea": idea,
            "project": promoted["project"],
            "workflow": promoted["workflow"],
            "proposal": proposal,
            "work_items_created": promoted["work_items_created"],
        }

    def _normalized_summary(self, opportunity: dict[str, Any]) -> str:
        existing = str(opportunity.get("normalized_summary") or "").strip()
        if existing:
            return existing
        raw_requirements = str(opportunity.get("raw_requirements") or "").strip()
        if raw_requirements:
            collapsed = " ".join(raw_requirements.split())
            return collapsed[:280]
        return opportunity["title"]

    def _extract_must_haves(self, text: str) -> list[str]:
        lowered = text.lower()
        matches = [label for label, keywords in MUST_HAVE_RULES if any(keyword in lowered for keyword in keywords)]
        if not matches:
            return ["Requirements review needed"]
        return matches

    def _strategic_fit_score(self, opportunity: dict[str, Any]) -> float:
        text = " ".join(
            filter(
                None,
                [
                    opportunity.get("title"),
                    opportunity.get("buyer_name"),
                    opportunity.get("normalized_summary"),
                    opportunity.get("raw_requirements"),
                ],
            )
        ).lower()
        score = 45.0
        if any(keyword in text for keyword in ("health", "public health", "medicaid", "care", "clinical")):
            score += 18
        if any(keyword in text for keyword in ("city", "county", "state", "public", "department", "government")):
            score += 10
        if any(keyword in text for keyword in ("fhir", "hl7", "interoperability", "integration", "api")):
            score += 12
        if any(keyword in text for keyword in ("dashboard", "analytics", "reporting", "workflow", "automation")):
            score += 8
        if any(keyword in text for keyword in ("security", "compliance", "hipaa", "audit")):
            score += 7
        return _clamp(score)

    def _delivery_risk_score(self, opportunity: dict[str, Any]) -> float:
        text = " ".join(
            filter(
                None,
                [
                    opportunity.get("title"),
                    opportunity.get("normalized_summary"),
                    opportunity.get("raw_requirements"),
                ],
            )
        ).lower()
        score = 28.0
        if not opportunity.get("raw_requirements"):
            score += 18
        if not opportunity.get("zip_code"):
            score += 6
        if any(keyword in text for keyword in ("legacy", "migration", "replace", "procurement", "compliance review")):
            score += 12
        if any(keyword in text for keyword in ("urgent", "immediate", "asap", "expedited", "rapid turnaround")):
            score += 14
        if any(keyword in text for keyword in ("pilot", "discovery", "assessment")):
            score -= 6
        return _clamp(score)

    def _confidence_score(
        self,
        strategic_fit_score: float,
        delivery_risk_score: float,
        opportunity: dict[str, Any],
    ) -> float:
        score = 48 + (strategic_fit_score * 0.4) - (delivery_risk_score * 0.35)
        if opportunity.get("raw_requirements"):
            score += 8
        if opportunity.get("normalized_summary"):
            score += 4
        return _clamp(score)

    def _recommendation(self, strategic_fit_score: float, delivery_risk_score: float) -> str:
        if strategic_fit_score >= 70 and delivery_risk_score <= 55:
            return "pursue"
        if strategic_fit_score < 45 or delivery_risk_score >= 78:
            return "pass"
        return "watch"

    def _territory_next_action(self, territory: dict[str, Any]) -> str:
        status = territory.get("status")
        by_stage = territory.get("by_stage", {})
        coverage = territory.get("coverage_evidence", {})
        if status == "planned":
            return "Activate this metro cluster and start discovery coverage."
        if status == "paused":
            return "Resume territory work or keep paused until capacity opens."
        if status == "covered":
            return "Refresh sources on cadence and watch for new opportunities."
        if coverage and not coverage.get("bundle_ready", False):
            return "Run the metro collector bundle until required sources have succeeded."
        if by_stage.get("discovered", 0):
            return "Normalize and qualify newly discovered opportunities."
        if by_stage.get("qualified", 0):
            return "Generate detailed estimates for qualified opportunities."
        if by_stage.get("estimated", 0):
            return "Review estimates and approve the best pursuits."
        if by_stage.get("approved_for_solutioning", 0):
            return "Hand approved pursuits into ideas, projects, and proposals."
        if territory.get("coverage_complete"):
            return "Mark this cluster covered and move to the next metro."
        return "Continue lane review until the cluster reaches coverage."

    def _enrich_territory_profile(self, territory: dict[str, Any], collector_runs: list[dict[str, Any]]) -> None:
        profile = TERRITORY_PROFILES.get((territory["state"], territory["metro_name"], territory["cluster_name"]), {})
        bundle = profile.get("collector_bundle", [])
        thresholds = profile.get(
            "coverage_thresholds",
            {"required_successful_collectors": 1, "max_discovered_backlog": 0},
        )
        territory["collector_bundle"] = bundle
        territory["coverage_thresholds"] = thresholds

        required_names = [collector["name"] for collector in bundle if collector.get("name")]
        successful_names = {
            run.get("collector_name")
            for run in collector_runs
            if run.get("status") == "ok" and run.get("collector_name") in required_names
        }
        bundle_ready = len(successful_names) >= int(
            thresholds.get("required_successful_collectors", len(required_names) or 1)
        )
        discovered_backlog = int(territory.get("by_stage", {}).get("discovered", 0))
        backlog_ready = discovered_backlog <= int(thresholds.get("max_discovered_backlog", 0))
        prior_stage_ready = (
            bool(territory.get("opportunity_total", 0))
            and discovered_backlog == 0
            and int(territory.get("by_stage", {}).get("normalized", 0)) == 0
        )
        territory["coverage_evidence"] = {
            "required_collectors": required_names,
            "successful_collectors": sorted(name for name in successful_names if name),
            "successful_collector_count": len(successful_names),
            "bundle_ready": bundle_ready,
            "backlog_ready": backlog_ready,
            "discovered_backlog": discovered_backlog,
        }
        territory["coverage_complete"] = bundle_ready and backlog_ready and prior_stage_ready
