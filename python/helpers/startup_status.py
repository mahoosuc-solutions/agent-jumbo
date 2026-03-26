import threading
import time
from copy import deepcopy

from python.helpers import runtime_mode

_lock = threading.Lock()
_state = {
    "run_mode": runtime_mode.get_run_mode(),
    "critical_subsystems": [
        "http_server",
        "api_routes",
        "auth_session",
        "chat_request_path",
    ],
    "optional_subsystems": [
        "chat_restore",
        "mcp_client",
        "job_loop",
        "preload",
        "mos_scheduler",
        "searxng",
        "gateway",
    ],
    "chat_restore": {
        "status": "idle",
        "active": False,
        "started_at": None,
        "finished_at": None,
        "error": None,
    },
    "mos_scheduler": {
        "status": "unknown",
        "reason": "",
        "registered": [],
        "count": 0,
    },
}


def _update_run_mode() -> None:
    _state["run_mode"] = runtime_mode.get_run_mode()


def mark_chat_restore_started() -> None:
    with _lock:
        _update_run_mode()
        _state["chat_restore"] = {
            "status": "running",
            "active": True,
            "started_at": time.time(),
            "finished_at": None,
            "error": None,
        }


def mark_chat_restore_success() -> None:
    with _lock:
        _update_run_mode()
        started_at = _state["chat_restore"].get("started_at")
        _state["chat_restore"] = {
            "status": "success",
            "active": False,
            "started_at": started_at,
            "finished_at": time.time(),
            "error": None,
        }


def mark_chat_restore_error(error: str) -> None:
    with _lock:
        _update_run_mode()
        started_at = _state["chat_restore"].get("started_at")
        _state["chat_restore"] = {
            "status": "error",
            "active": False,
            "started_at": started_at,
            "finished_at": time.time(),
            "error": error or None,
        }


def set_mos_scheduler_status(
    *, status: str, reason: str = "", registered: list[str] | None = None, count: int | None = None
) -> None:
    with _lock:
        _update_run_mode()
        registered = registered or []
        _state["mos_scheduler"] = {
            "status": status,
            "reason": reason,
            "registered": list(registered),
            "count": len(registered) if count is None else count,
        }


def snapshot() -> dict:
    with _lock:
        _update_run_mode()
        return deepcopy(_state)
