import os

_TRUE_VALUES = {"1", "true", "yes", "on"}
_VALID_RUN_MODES = {"full", "local-lite", "research"}


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUE_VALUES


def get_run_mode() -> str:
    mode = os.getenv("AGENT_JUMBO_RUN_MODE", "").strip().lower()
    if mode in _VALID_RUN_MODES:
        return mode
    if _env_flag("AGENT_JUMBO_LAPTOP_MODE"):
        return "local-lite"
    return "full"


def is_laptop_mode() -> bool:
    return get_run_mode() == "local-lite"


def is_reduced_startup_mode() -> bool:
    return get_run_mode() in {"local-lite", "research"}
