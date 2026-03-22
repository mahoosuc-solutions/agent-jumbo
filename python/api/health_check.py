"""
Health Check API - Monitor model availability and critical dependencies
"""

import os
import shutil
import sqlite3

from python.helpers.api import ApiHandler, Request, Response
from python.helpers.files import get_abs_path
from python.helpers.llm_router import get_router

# SQLite databases to check
_DB_PATHS = [
    "instruments/custom/workflow_engine/data/workflow.db",
    "instruments/custom/work_queue/data/work_queue.db",
]


def _check_databases() -> dict:
    """Try SELECT 1 on each critical SQLite database."""
    accessible: list[str] = []
    errors: list[str] = []
    for rel_path in _DB_PATHS:
        db_file = get_abs_path(rel_path)
        db_name = os.path.basename(db_file)
        try:
            conn = sqlite3.connect(db_file, timeout=3)
            conn.execute("SELECT 1")
            conn.close()
            accessible.append(db_name)
        except Exception as e:
            errors.append(f"{db_name}: {e!s}")

    if errors:
        return {
            "status": "error",
            "detail": f"Failed: {'; '.join(errors)}",
        }
    return {
        "status": "ok",
        "detail": f"{', '.join(accessible)} accessible",
    }


def _check_redis() -> dict:
    """Ping Redis if AGENTMESH_REDIS_URL is configured."""
    redis_url = os.environ.get("AGENTMESH_REDIS_URL")
    if not redis_url:
        return {"status": "not_configured", "detail": "AGENTMESH_REDIS_URL not set"}
    try:
        import redis as redis_lib

        r = redis_lib.from_url(redis_url, socket_connect_timeout=3)
        r.ping()
        r.close()
        return {"status": "ok", "detail": "ping successful"}
    except Exception as e:
        return {"status": "error", "detail": f"Redis ping failed: {e!s}"}


def _check_disk() -> dict:
    """Check free disk space on the working directory mount."""
    try:
        path = get_abs_path()
        usage = shutil.disk_usage(path)
        free_mb = usage.free // (1024 * 1024)
        if free_mb < 500:
            return {
                "status": "warning",
                "free_mb": free_mb,
                "detail": f"Low disk space: {free_mb} MB free",
            }
        return {"status": "ok", "free_mb": free_mb}
    except Exception as e:
        return {"status": "error", "free_mb": 0, "detail": f"Disk check failed: {e!s}"}


def _overall_status(checks: dict) -> str:
    """Derive overall status from individual check results."""
    statuses = {c.get("status") for c in checks.values()}
    if "error" in statuses:
        return "unhealthy"
    if "warning" in statuses:
        return "degraded"
    return "healthy"


class HealthCheck(ApiHandler):
    """API handler for comprehensive system health"""

    async def process(self, input: dict, request: Request) -> dict | Response:
        """
        Get health status of all critical dependencies.

        Input:
            providers: Optional list of LLM providers to check (default: all)

        Returns structured JSON:
            status: "healthy" | "degraded" | "unhealthy"
            checks:
                llm:       LLM provider availability
                databases: SQLite connectivity
                redis:     Redis connectivity (or not_configured)
                disk:      Free disk space
        """
        router = get_router()
        providers = input.get("providers")

        checks: dict[str, dict] = {}

        # 1. LLM providers
        try:
            llm_status = await router.health_check_models(providers=providers)
            checks["llm"] = {"status": "ok", "detail": llm_status}
        except Exception as e:
            checks["llm"] = {"status": "error", "detail": f"LLM check failed: {e!s}"}

        # 2. SQLite databases
        checks["databases"] = _check_databases()

        # 3. Redis
        checks["redis"] = _check_redis()

        # 4. Disk space
        checks["disk"] = _check_disk()

        return {
            "status": _overall_status(checks),
            "checks": checks,
        }


class BaselineStatus(ApiHandler):
    """API handler for checking baseline model status"""

    async def process(self, input: dict, request: Request) -> dict | Response:
        """
        Get baseline model status

        Returns:
            available: Whether baseline model is available
            model: Model display name (if available)
            provider: Provider name (if available)
            size_gb: Model size in GB (if available)
            is_local: Whether model is local (if available)
        """
        router = get_router()

        try:
            baseline = router.get_baseline_model()

            if baseline:
                return {
                    "available": True,
                    "model": baseline.display_name,
                    "provider": baseline.provider,
                    "size_gb": baseline.size_gb,
                    "is_local": baseline.is_local,
                }
            else:
                return {"available": False, "message": "No baseline model configured"}
        except Exception as e:
            return {"success": False, "error": f"Failed to get baseline status: {e!s}"}
