import shutil
import time

from python.helpers import errors, git, perf_metrics, service_profile, startup_status
from python.helpers.api import ApiHandler, Request, Response

_boot_time = time.time()


class HealthCheck(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    @classmethod
    def get_methods(cls) -> list[str]:
        return ["GET", "POST"]

    async def process(self, input: dict, request: Request) -> dict | Response:
        checks: dict = {}
        overall_ok = True

        # 1. Git info (existing)
        try:
            checks["git"] = {"ok": True, "info": git.get_git_info()}
        except Exception as e:
            checks["git"] = {"ok": False, "error": errors.error_text(e)}

        # 2. Disk space
        usage = shutil.disk_usage("/")
        free_gb = round(usage.free / (1024**3), 2)
        disk_ok = free_gb > 1.0
        checks["disk"] = {"ok": disk_ok, "free_gb": free_gb}
        if not disk_ok:
            overall_ok = False

        # 3. Memory (RSS via resource module)
        try:
            import resource

            rss_mb = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
            checks["memory"] = {"ok": True, "rss_mb": rss_mb}
        except Exception:
            checks["memory"] = {"ok": True, "note": "resource module unavailable"}

        # 4. Uptime
        checks["uptime_seconds"] = round(time.time() - _boot_time, 1)

        # 5. Runtime metrics (existing)
        checks["runtime_metrics"] = perf_metrics.snapshot()

        # 6. Startup/runtime status
        checks["startup"] = startup_status.snapshot()
        checks["service_profile"] = service_profile.snapshot()

        return {
            "ok": overall_ok,
            "status": "healthy" if overall_ok else "degraded",
            "checks": checks,
        }
