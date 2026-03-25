from __future__ import annotations

from typing import Any

from python.helpers import files

from .opportunities_db import OpportunitiesDatabase

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


class OpportunitiesManager:
    def __init__(self, db_path: str):
        self.db = OpportunitiesDatabase(db_path)

    def dashboard(self) -> dict[str, Any]:
        data = self.db.territory_dashboard()
        opportunities = self.db.list_opportunities()
        lane_counts = dict.fromkeys(VALID_LANES, 0)
        for opportunity in opportunities:
            lane_counts[opportunity["lane"]] = lane_counts.get(opportunity["lane"], 0) + 1
        data["lane_counts"] = lane_counts
        data["recent"] = opportunities[:8]
        return data

    def list_territories(self, status: str | None = None) -> list[dict[str, Any]]:
        return self.db.list_territories(status=status)

    def set_territory_status(self, territory_id: int, status: str) -> bool:
        if status not in {"planned", "active", "covered", "refresh", "paused"}:
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

        lane = str(payload.get("lane", "discovery")).strip() or "discovery"
        if lane not in VALID_LANES:
            raise ValueError(f"invalid lane: {lane}")

        return self.db.create_opportunity(
            {
                "territory_id": territory_id,
                "title": title,
                "buyer_name": buyer_name,
                "source_type": str(payload.get("source_type", "manual")).strip() or "manual",
                "source_url": payload.get("source_url"),
                "external_id": payload.get("external_id"),
                "zip_code": str(payload.get("zip_code", "")).strip(),
                "city": str(payload.get("city", "")).strip(),
                "state": str(payload.get("state", "")).strip(),
                "stage": "discovered",
                "lane": lane,
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
        )

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
