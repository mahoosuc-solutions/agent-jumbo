from python.helpers.api import ApiHandler, Request, Response


def _safe_host_only(url: str | None) -> str | None:
    """Return only the host[:port] portion of a URL, stripping credentials and path."""
    if not url:
        return None
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.port:
            host = f"{host}:{parsed.port}"
        return host or None
    except Exception:
        return None


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

        redis_url = os.environ.get("AGENTMESH_REDIS_URL")
        aios_base_url = os.environ.get("AIOS_BASE_URL", "").strip()

        bridge = _get_bridge()

        # Base response from bridge.health() if available
        base: dict[str, object]
        if bridge:
            base = {"status": "ok", **bridge.health()}
            base["agentmesh_redis"] = "connected"
            consumer_active: bool = bridge.health().get("running", False)
        else:
            if not redis_url:
                base = {"status": "disabled", "reason": "AGENTMESH_REDIS_URL not set"}
                base["agentmesh_redis"] = "unconfigured"
            else:
                base = {"status": "disconnected", "reason": "bridge failed to connect", "redis_url": redis_url}
                base["agentmesh_redis"] = "unreachable"
            consumer_active = False

        # Extend with new fields
        base["aios_bridge_enabled"] = bool(aios_base_url)
        base["aios_base_url"] = _safe_host_only(aios_base_url) if aios_base_url else None
        base["consumer_active"] = consumer_active
        base["agentmesh_redis_url"] = _safe_host_only(redis_url) if redis_url else None

        return base
