"""Proxy WBM MCP edge health checks server-side.

The browser cannot reach localhost:3150/3151 directly when running on Windows
with WSL2 — those ports are only bound inside the WSL network. This endpoint
fetches from host.docker.internal (reachable from the container) and returns
the result, allowing the onboarding page to poll bridge status same-origin.
"""

import os

from python.helpers.api import ApiHandler, Request, Response


class WbmBridgeHealth(ApiHandler):
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
        import urllib.request

        env = request.args.get("env", "staging").lower()

        if env == "production":
            base_url = os.environ.get("WBM_PRODUCTION_MCP_URL", "").replace("/mcp", "")
        else:
            base_url = os.environ.get("WBM_STAGING_MCP_URL", "").replace("/mcp", "")

        if not base_url:
            return {"ok": False, "error": f"WBM_{env.upper()}_MCP_URL not configured"}

        health_url = f"{base_url}/health"
        try:
            with urllib.request.urlopen(health_url, timeout=4) as resp:
                import json

                body = json.loads(resp.read().decode())
                return {"ok": True, **body}
        except Exception as e:
            return {"ok": False, "error": str(e)}
