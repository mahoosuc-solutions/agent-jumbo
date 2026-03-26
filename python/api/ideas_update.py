"""
Ideas Update API — create, mutate, and promote ideas.
"""

from __future__ import annotations

import traceback

from python.helpers import files
from python.helpers.api import ApiHandler


class IdeasUpdate(ApiHandler):
    async def process(self, input: dict, request) -> dict:
        try:
            from instruments.custom.ideas.ideas_manager import IdeasManager

            db_path = files.get_abs_path("./instruments/custom/ideas/data/ideas.db")
            manager = IdeasManager(db_path)

            action = input.get("action", "create")
            if action == "create":
                idea = manager.create_idea(input.get("idea", {}))
                return {"success": True, "idea": idea}

            idea_id = input.get("idea_id")
            if not idea_id:
                return {"success": False, "error": "idea_id is required"}

            if action == "update":
                idea = manager.update_idea(int(idea_id), input.get("updates", {}))
                return {"success": True, "idea": idea}
            if action == "promote_to_project":
                data = manager.promote_to_project(int(idea_id))
                return {"success": True, **data}
            return {"success": False, "error": f"Unknown action: {action}"}
        except Exception as e:
            traceback.print_exc()
            return {"success": False, "error": str(e)}
