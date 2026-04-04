"""Backup and platform readiness verification endpoint.

GET /backup_verify — lightweight health probe designed for automated GA readiness
checks. Reports platform health, disk space, dead-letter queue depth, and
scheduler task count without triggering a full backup (which downloads a file).
"""

import datetime
import os

from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers.files import get_abs_path


class BackupVerify(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False  # readable by health-monitor scheduler task (loopback)

    @classmethod
    def requires_loopback(cls) -> bool:
        return True

    async def process(self, input: Input, request: Request) -> Output:
        checks: dict[str, object] = {}
        overall = "ok"

        # ── 1. Disk space ──────────────────────────────────────────────────
        try:
            stat = os.statvfs(get_abs_path(""))
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) / (1024**3)
            used_pct = round((1 - stat.f_bavail / stat.f_blocks) * 100, 1) if stat.f_blocks else 0
            disk_status = "ok" if free_gb >= 5 else ("warn" if free_gb >= 1 else "critical")
            if disk_status != "ok":
                overall = "degraded"
            checks["disk"] = {
                "status": disk_status,
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_pct": used_pct,
            }
        except Exception as e:
            checks["disk"] = {"status": "error", "error": str(e)}
            overall = "degraded"

        # ── 2. Dead-letter queue depth ─────────────────────────────────────
        try:
            dl_path = get_abs_path("logs/dead_letters.jsonl")
            if os.path.exists(dl_path):
                with open(dl_path) as f:
                    count = sum(1 for _ in f)
            else:
                count = 0
            dl_status = "ok" if count < 50 else ("warn" if count < 200 else "critical")
            if dl_status == "critical":
                overall = "degraded"
            checks["dead_letters"] = {"status": dl_status, "count": count}
        except Exception as e:
            checks["dead_letters"] = {"status": "error", "error": str(e)}

        # ── 3. Scheduler task count ────────────────────────────────────────
        try:
            from python.helpers.task_scheduler import TaskScheduler

            scheduler = TaskScheduler.get()
            await scheduler.reload()
            tasks = scheduler.get_tasks()
            active = sum(1 for t in tasks if getattr(t, "state", None) and t.state.value == "idle")
            checks["scheduler"] = {"status": "ok", "total_tasks": len(tasks), "active_tasks": active}
        except ImportError:
            checks["scheduler"] = {"status": "unavailable"}
        except Exception as e:
            checks["scheduler"] = {"status": "error", "error": str(e)}

        # ── 4. Core data directories ───────────────────────────────────────
        required_dirs = ["data", "logs", "tmp"]
        missing = [d for d in required_dirs if not os.path.isdir(get_abs_path(d))]
        checks["data_dirs"] = {
            "status": "ok" if not missing else "warn",
            "missing": missing,
        }
        if missing:
            overall = "degraded"

        # ── 5. Auth config sanity ──────────────────────────────────────────
        flask_secret = os.environ.get("FLASK_SECRET_KEY", "")
        auth_status = "ok" if len(flask_secret) >= 32 else "warn"
        checks["auth_config"] = {"status": auth_status, "flask_secret_set": bool(flask_secret)}
        if auth_status != "ok":
            overall = "degraded"

        return {
            "ok": overall == "ok",
            "status": overall,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "checks": checks,
        }
