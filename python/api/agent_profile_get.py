"""GET /agent_profile_get — list selectable agent profiles with display metadata."""

import os

import yaml

from python.helpers import files, settings_persistence
from python.helpers.api import ApiHandler, Request, Response


class GetAgentProfile(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        agents_dir = files.get_abs_path("agents")
        profiles: list[dict] = []

        for entry in sorted(os.listdir(agents_dir)):
            manifest_path = os.path.join(agents_dir, entry, "manifest.yaml")
            if not os.path.isfile(manifest_path):
                continue

            with open(manifest_path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}

            display = data.get("display", {})
            if not display.get("selectable", False):
                continue

            profiles.append(
                {
                    "id": entry,
                    "name": data.get("name", entry),
                    "description": (data.get("description") or "").strip(),
                    "display_name": display.get("display_name", entry),
                    "icon": display.get("icon", "🤖"),
                    "tier": display.get("tier", "utility"),
                    "inherits": data.get("inherits", ""),
                    "capabilities": data.get("capabilities", []),
                }
            )

        current = settings_persistence.get_settings().get("agent_profile", "agent-jumbo")

        return {
            "supported": True,
            "current_profile": current,
            "profiles": profiles,
        }
