from python.helpers.api import ApiHandler, Request, Response


class HealthAgentmesh(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        import os

        from python.helpers.agentmesh_task_handler import _get_bridge

        bridge = _get_bridge()
        if not bridge:
            redis_url = os.environ.get("AGENTMESH_REDIS_URL")
            if not redis_url:
                return {"status": "disabled", "reason": "AGENTMESH_REDIS_URL not set"}
            return {"status": "disconnected", "reason": "bridge failed to connect", "redis_url": redis_url}
        return {"status": "ok", **bridge.health()}
