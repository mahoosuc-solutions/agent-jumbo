from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time

from python.helpers import dotenv, runtime, runtime_mode

SUPERVISOR_SOCKET = "/var/run/supervisor.sock"
SUPERVISORCTL = shutil.which("supervisorctl") or "/usr/bin/supervisorctl"
RUN_UI_PROGRAM = "run_ui"
SERVICE_ORDER = [
    RUN_UI_PROGRAM,
    "run_searxng",
    "run_cron",
    "run_sshd",
    "run_tunnel_api",
]
SERVICE_LABELS = {
    RUN_UI_PROGRAM: "Web UI",
    "run_searxng": "SearXNG",
    "run_cron": "Scheduler Cron",
    "run_sshd": "SSH Runtime",
    "run_tunnel_api": "Tunnel API",
}
PROFILE_DEFINITIONS = {
    "full": {
        "label": "Full",
        "description": "All local services enabled.",
        "services": list(SERVICE_ORDER),
    },
    "local-lite": {
        "label": "Local Lite",
        "description": "UI only for the lightest local workflow.",
        "services": [RUN_UI_PROGRAM],
    },
    "research": {
        "label": "Research",
        "description": "UI plus search, without operational daemons.",
        "services": [RUN_UI_PROGRAM, "run_searxng"],
    },
}
VALID_PROFILES = set(PROFILE_DEFINITIONS.keys())

_CACHE_LOCK = threading.Lock()
_CACHE_TTL_SECONDS = 2.0
_STATE_CACHE = {"ts": 0.0, "data": None}


def normalize_profile(profile: str | None) -> str:
    if profile in VALID_PROFILES:
        return str(profile)
    return runtime_mode.get_run_mode()


def is_valid_profile(profile: str | None) -> bool:
    return str(profile or "").strip().lower() in VALID_PROFILES


def get_profile_services(profile: str) -> list[str]:
    normalized = normalize_profile(profile)
    if normalized not in VALID_PROFILES:
        raise ValueError(f"Unsupported profile: {profile}")
    return list(PROFILE_DEFINITIONS[normalized]["services"])


def profile_metadata() -> list[dict]:
    profiles = []
    for profile_id, config in PROFILE_DEFINITIONS.items():
        profiles.append(
            {
                "id": profile_id,
                "label": config["label"],
                "description": config["description"],
                "services": [
                    {"id": service_id, "label": SERVICE_LABELS[service_id]} for service_id in config["services"]
                ],
            }
        )
    return profiles


def is_supported() -> bool:
    return runtime.is_dockerized() and os.path.exists(SUPERVISOR_SOCKET) and os.path.exists(SUPERVISORCTL)


def get_autostart_flags(profile: str) -> dict[str, str]:
    enabled = set(get_profile_services(profile))
    return {
        "RUN_UI_AUTOSTART": "true",
        "RUN_SEARXNG_AUTOSTART": "true" if "run_searxng" in enabled else "false",
        "RUN_CRON_AUTOSTART": "true" if "run_cron" in enabled else "false",
        "RUN_SSHD_AUTOSTART": "true" if "run_sshd" in enabled else "false",
        "RUN_TUNNEL_API_AUTOSTART": "true" if "run_tunnel_api" in enabled else "false",
    }


def persist_profile(profile: str) -> str:
    if not is_valid_profile(profile):
        raise ValueError(f"Unsupported profile: {profile}")
    normalized = normalize_profile(profile)
    dotenv.save_dotenv_value("AGENT_MAHOO_RUN_MODE", normalized)
    dotenv.save_dotenv_value("AGENT_MAHOO_LAPTOP_MODE", "true" if normalized == "local-lite" else "false")
    os.environ["AGENT_MAHOO_RUN_MODE"] = normalized
    os.environ["AGENT_MAHOO_LAPTOP_MODE"] = "true" if normalized == "local-lite" else "false"
    invalidate_cache()
    return normalized


def get_current_profile() -> str:
    return runtime_mode.get_run_mode()


def snapshot(force_refresh: bool = False) -> dict:
    now = time.time()
    with _CACHE_LOCK:
        cached = _STATE_CACHE["data"]
        if cached and not force_refresh and now - _STATE_CACHE["ts"] < _CACHE_TTL_SECONDS:
            return _clone(cached)

    current_profile = get_current_profile()
    desired_services = set(get_profile_services(current_profile))
    runtime_states = get_runtime_states() if is_supported() else {}
    services = []
    for service_id in SERVICE_ORDER:
        services.append(
            {
                "id": service_id,
                "label": SERVICE_LABELS[service_id],
                "enabled": service_id in desired_services,
                "runtime_state": runtime_states.get(service_id, "unknown"),
            }
        )

    supported = is_supported()
    data = {
        "supported": supported,
        "current_profile": current_profile,
        "profiles": profile_metadata(),
        "services": services,
        "can_apply": supported,
        "restart_strategy": "managed_restart",
    }
    with _CACHE_LOCK:
        _STATE_CACHE["ts"] = now
        _STATE_CACHE["data"] = data
    return _clone(data)


def get_runtime_states() -> dict[str, str]:
    if not is_supported():
        return {}
    try:
        result = _run_supervisorctl("status")
    except Exception:
        return {}
    states: dict[str, str] = {}
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in SERVICE_ORDER:
            states[parts[0]] = parts[1].lower()
    return states


def diff_profile(target_profile: str) -> dict[str, list[str]]:
    current_enabled = set(get_profile_services(get_current_profile()))
    target_enabled = set(get_profile_services(target_profile))
    return {
        "start": [service for service in SERVICE_ORDER if service in target_enabled and service not in current_enabled],
        "stop": [service for service in SERVICE_ORDER if service in current_enabled and service not in target_enabled],
        "unchanged": [service for service in SERVICE_ORDER if service in current_enabled and service in target_enabled],
    }


def apply_profile(target_profile: str) -> dict:
    if not is_supported():
        raise RuntimeError("Service profiles are supported only in dockerized supervisor runs.")
    normalized = normalize_profile(target_profile)
    transitions = diff_profile(normalized)
    normalized = persist_profile(normalized)
    started: list[str] = []
    stopped: list[str] = []

    for service in transitions["stop"]:
        if service == RUN_UI_PROGRAM:
            continue
        _run_supervisorctl("stop", service)
        stopped.append(service)

    for service in transitions["start"]:
        if service == RUN_UI_PROGRAM:
            continue
        _run_supervisorctl("start", service)
        started.append(service)

    invalidate_cache()
    return {
        "selected_profile": normalized,
        "started": started,
        "stopped": stopped,
        "unchanged": [service for service in transitions["unchanged"] if service != RUN_UI_PROGRAM],
    }


def schedule_run_ui_restart(delay_seconds: float = 1.5) -> None:
    if not is_supported():
        return
    shell = (
        f"sleep {max(0.5, float(delay_seconds)):.1f}; "
        f"{SUPERVISORCTL} -s unix://{SUPERVISOR_SOCKET} restart {RUN_UI_PROGRAM} >/dev/null 2>&1"
    )
    subprocess.Popen(
        ["/bin/bash", "-lc", shell],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def invalidate_cache() -> None:
    with _CACHE_LOCK:
        _STATE_CACHE["ts"] = 0.0
        _STATE_CACHE["data"] = None


def _run_supervisorctl(*args: str) -> subprocess.CompletedProcess[str]:
    command = [SUPERVISORCTL, "-s", f"unix://{SUPERVISOR_SOCKET}", *args]
    result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=15)
    allowed_returncodes = {0}
    if args and args[0] == "status":
        # supervisorctl exits 3 when one or more programs are intentionally stopped.
        allowed_returncodes.add(3)
    if result.returncode not in allowed_returncodes:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "supervisorctl command failed")
    return result


def _clone(data: dict) -> dict:
    return {
        **data,
        "profiles": [
            dict(profile, services=[dict(service) for service in profile["services"]]) for profile in data["profiles"]
        ],
        "services": [dict(service) for service in data["services"]],
    }
