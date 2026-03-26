from __future__ import annotations

import traceback

from python.helpers import files
from python.helpers.api import ApiHandler


class OpportunitiesUpdate(ApiHandler):
    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.opportunities.opportunities_manager import OpportunitiesManager

            db_path = files.get_abs_path("./instruments/custom/opportunities/data/opportunities.db")
            manager = OpportunitiesManager(db_path)

            action = input.get("action", "create")
            if action == "create":
                opportunity = manager.create_opportunity(input.get("opportunity", {}))
                return {"success": True, "opportunity": opportunity}
            if action == "ingest":
                result = manager.import_opportunities(
                    input.get("opportunities", []),
                    auto_qualify=bool(input.get("auto_qualify", True)),
                )
                return {"success": True, **result}
            if action == "run_collectors":
                result = manager.run_collectors(
                    input.get("collectors", []),
                    auto_qualify=bool(input.get("auto_qualify", True)),
                )
                return {"success": True, **result}
            if action == "schedule_collectors":
                result = await manager.schedule_collectors(
                    str(input.get("cron", "0 */6 * * *")),
                    input.get("collectors", []),
                )
                return result
            if action == "unschedule_collectors":
                return await manager.unschedule_collectors()

            if action == "set_territory_status":
                territory_id = int(input.get("territory_id", 0))
                if territory_id <= 0:
                    return {"success": False, "error": "territory_id is required"}
                updated = manager.set_territory_status(territory_id, str(input.get("status", "")))
                return {"success": updated, "updated": updated}

            opportunity_id = int(input.get("opportunity_id", 0))
            if opportunity_id <= 0:
                return {"success": False, "error": "opportunity_id is required"}

            if action == "update":
                opportunity = manager.update_opportunity(opportunity_id, input.get("updates", {}))
                return {"success": True, "opportunity": opportunity}
            if action == "estimate":
                estimate = manager.save_estimate(opportunity_id, input.get("estimate", {}))
                opportunity = manager.get_opportunity(opportunity_id)
                return {"success": True, "estimate": estimate, "opportunity": opportunity}
            if action == "qualify":
                opportunity = manager.qualify_opportunity(opportunity_id)
                return {"success": True, "opportunity": opportunity}
            if action == "approve":
                opportunity = manager.approve_for_solutioning(opportunity_id)
                return {"success": True, "opportunity": opportunity}
            if action == "handoff":
                return manager.handoff_to_solutioning(opportunity_id)
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
