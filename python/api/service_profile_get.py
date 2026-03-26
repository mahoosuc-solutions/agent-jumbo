from python.helpers import service_profile
from python.helpers.api import ApiHandler, Request, Response


class GetServiceProfile(ApiHandler):
    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        return service_profile.snapshot(force_refresh=True)
