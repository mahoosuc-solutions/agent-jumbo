from python.helpers.api import ApiHandler, Input, Request, Response
from python.helpers.work_mode.manager import WorkModeManager


class WorkModeGetHandler(ApiHandler):
    route_name = "work_mode"

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    async def process(self, input: Input, request: Request) -> dict | Response:
        mgr = WorkModeManager.get_instance()
        profile = mgr.get_profile()
        return {
            "mode": mgr.get_mode().value,
            "profile": {
                "ram_gb": round(profile.ram_gb, 1),
                "vram_gb": round(profile.vram_gb, 1),
                "has_gpu": profile.has_gpu,
                "local_inference_eligible": profile.local_inference_eligible,
                "has_network": profile.has_network,
                "suggested_mode": profile.suggested_mode.value,
            },
        }
