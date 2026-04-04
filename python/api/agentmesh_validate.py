"""POST /agentmesh_validate

Validates Agent Mesh Redis connectivity and AIOS bridge reachability.
Never returns a 500 — all exceptions are caught and surfaced as degraded status.
"""

from python.helpers.api import ApiHandler, Request, Response


def _ping_redis(redis_url: str) -> str:
    """Return 'connected' or 'unreachable'."""
    try:
        import redis as redis_lib

        r = redis_lib.from_url(redis_url, socket_connect_timeout=3)
        r.ping()
        r.close()
        return "connected"
    except Exception:
        return "unreachable"


def _check_aios(aios_base_url: str) -> str:
    """Return 'reachable' or 'unreachable'."""
    try:
        import requests

        url = aios_base_url.rstrip("/") + "/api/platform/agent-jumbo/status"
        requests.get(url, timeout=3)
        return "reachable"
    except Exception:
        return "unreachable"


def _overall_status(redis_result: str, aios_result: str) -> str:
    ok_redis = redis_result == "connected"
    ok_aios = aios_result == "reachable"
    unconfigured_redis = redis_result == "unconfigured"
    unconfigured_aios = aios_result == "unconfigured"

    if ok_redis and ok_aios:
        return "ok"
    if ok_redis and unconfigured_aios:
        return "ok"
    if unconfigured_redis and ok_aios:
        return "ok"
    if unconfigured_redis and unconfigured_aios:
        return "offline"
    if redis_result == "unreachable" and aios_result == "unreachable":
        return "offline"
    return "degraded"


class AgentmeshValidate(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        import os
        from datetime import datetime, timezone

        try:
            redis_url = os.environ.get("AGENTMESH_REDIS_URL", "").strip()
            aios_base_url = os.environ.get("AIOS_BASE_URL", "").strip()

            # Redis check
            if redis_url:
                agentmesh_redis = _ping_redis(redis_url)
            else:
                agentmesh_redis = "unconfigured"

            # AIOS bridge check
            if aios_base_url:
                aios_bridge = _check_aios(aios_base_url)
            else:
                aios_bridge = "unconfigured"

            status = _overall_status(agentmesh_redis, aios_bridge)

            return {
                "status": status,
                "agentmesh_redis": agentmesh_redis,
                "aios_bridge": aios_bridge,
                "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        except Exception as exc:
            from datetime import datetime, timezone

            return {
                "status": "degraded",
                "agentmesh_redis": "unreachable",
                "aios_bridge": "unreachable",
                "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "error": str(exc),
            }
