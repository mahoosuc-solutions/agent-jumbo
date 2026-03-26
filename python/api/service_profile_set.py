from python.helpers import service_profile
from python.helpers.api import ApiHandler, Request, Response


class SetServiceProfile(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        profile = str(input.get("profile") or "").strip().lower()
        if not service_profile.is_valid_profile(profile):
            raise ValueError(f"Unsupported profile: {profile}")

        result = service_profile.apply_profile(profile)
        service_profile.schedule_run_ui_restart()
        return {
            "ok": True,
            **result,
            "restart_scheduled": True,
        }
