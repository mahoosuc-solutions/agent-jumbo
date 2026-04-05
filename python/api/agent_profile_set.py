"""POST /agent_profile_set — switch the active agent profile."""

import os

from python.helpers import files, settings_persistence
from python.helpers.api import ApiHandler, Request, Response


class SetAgentProfile(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        profile = str(input.get("profile") or "").strip()
        if not profile:
            raise ValueError("Missing required field: profile")

        manifest_path = files.get_abs_path("agents", profile, "manifest.yaml")
        if not os.path.isfile(manifest_path):
            raise ValueError(f"Unknown agent profile: {profile}")

        settings_persistence.set_settings_delta({"agent_profile": profile})

        return {
            "ok": True,
            "profile": profile,
            "reload_required": True,
        }
