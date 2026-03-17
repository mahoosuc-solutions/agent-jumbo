"""Debug metrics endpoint for E2E performance testing."""

import time

import psutil

from python.helpers.api import ApiHandler, Request, Response

_boot_time = time.time()


class DebugMetrics(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return True

    @classmethod
    def requires_loopback(cls) -> bool:
        return True

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        proc = psutil.Process()
        mem = proc.memory_info()
        return {
            "rss_bytes": mem.rss,
            "cpu_percent": proc.cpu_percent(interval=0.1),
            "open_files": len(proc.open_files()),
            "uptime_seconds": round(time.time() - _boot_time, 1),
        }
