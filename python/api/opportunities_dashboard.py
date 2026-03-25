from __future__ import annotations

import traceback

from python.helpers import files
from python.helpers.api import ApiHandler


class OpportunitiesDashboard(ApiHandler):
    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.opportunities.opportunities_manager import OpportunitiesManager

            db_path = files.get_abs_path("./instruments/custom/opportunities/data/opportunities.db")
            manager = OpportunitiesManager(db_path)

            action = input.get("action", "dashboard")
            if action == "dashboard":
                return {"success": True, **manager.dashboard()}
            if action == "territories":
                return {"success": True, "territories": manager.list_territories(status=input.get("status"))}
            if action == "list":
                territory_id = input.get("territory_id")
                return {
                    "success": True,
                    "opportunities": manager.list_opportunities(
                        territory_id=int(territory_id) if territory_id else None,
                        stage=input.get("stage"),
                        lane=input.get("lane"),
                        search=input.get("search"),
                    ),
                }
            if action == "get":
                opportunity_id = int(input.get("opportunity_id", 0))
                if opportunity_id <= 0:
                    return {"success": False, "error": "opportunity_id is required"}
                opportunity = manager.get_opportunity(opportunity_id)
                if not opportunity:
                    return {"success": False, "error": f"opportunity {opportunity_id} not found"}
                return {"success": True, "opportunity": opportunity}
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
