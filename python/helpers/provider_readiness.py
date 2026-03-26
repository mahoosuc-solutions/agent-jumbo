from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import models
from instruments.custom.claude_sdk.sdk_manager import ClaudeSDKManager

LOCAL_PROVIDERS = {"ollama", "huggingface", "local", "lmstudio", "lm_studio"}
DEFAULT_CONTAINER_NAME = os.getenv("AGENT_JUMBO_CONTAINER_NAME", "agent-jumbo").strip() or "agent-jumbo"


def current_runtime_scope() -> str:
    return "container" if Path("/.dockerenv").exists() else "host"


def available_runtime_scopes() -> list[str]:
    current = current_runtime_scope()
    scopes = [current]
    if current == "host" and _container_is_available(DEFAULT_CONTAINER_NAME):
        scopes.append("container")
    return scopes


def _resolve_external_executable(backend: str) -> str:
    candidates: list[str] = []
    if backend == "claude_code":
        env_path = os.getenv("CLAUDE_CLI_PATH", "").strip()
        if env_path:
            candidates.append(env_path)
        candidates.extend(
            [
                "claude",
                "claude-code",
                os.path.expanduser("~/dev/tools/claude-code/bin/claude"),
            ]
        )
    elif backend == "codex":
        env_path = os.getenv("CODEX_CLI_PATH", "").strip()
        if env_path:
            candidates.append(env_path)
        candidates.extend(
            [
                "codex",
                "codex-cli",
                os.path.expanduser("~/dev/tools/claude-code/bin/codex"),
            ]
        )
    else:
        return ""

    for candidate in candidates:
        if os.path.isabs(candidate) and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return ""


def _container_is_available(container_name: str) -> bool:
    if not shutil.which("docker"):
        return False
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return False
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


def _run_local_command(command: list[str], timeout: int, cwd: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd or None,
        check=False,
    )


def _run_container_shell(command: str, timeout: int, container_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", "exec", container_name, "sh", "-lc", command],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _command_result(ok: bool, detail: str, **extra: Any) -> dict[str, Any]:
    return {"ok": ok, "detail": detail, **extra}


def _is_missing_key(value: str | None) -> bool:
    token = (value or "").strip()
    return token in {"", "None", "NA"}


def _provider_check(provider: str, api_base: str) -> dict[str, Any]:
    name = (provider or "").strip().lower()
    if not name or name in LOCAL_PROVIDERS:
        return _command_result(True, f"Local or implicit provider '{name or 'none'}'")
    key = str(models.get_api_key(name) or "").strip()
    if _is_missing_key(key):
        return _command_result(False, f"Missing API key for provider '{name}'", failure_class="auth_required")
    return _command_result(True, f"API key configured for provider '{name}'")


def _classify_failure(detail: str, default: str = "runtime_misconfigured") -> str:
    text = (detail or "").strip().lower()
    if not text:
        return default
    if any(
        token in text
        for token in (
            "401",
            "unauthorized",
            "authentication",
            "missing bearer",
            "missing basic authentication",
            "api key",
            "login",
            "not logged in",
            "forbidden",
        )
    ):
        return "auth_required"
    if any(token in text for token in ("not found", "not installed", "no such file", "executable")):
        return "missing_executable"
    if any(token in text for token in ("timed out", "unreachable", "connection refused", "econnreset", "dns")):
        return "provider_unreachable"
    if "sdk" in text:
        return "sdk_unavailable"
    return default


def _fix_hint(backend: str, failure_class: str, runtime_scope: str) -> str:
    if failure_class == "missing_executable":
        if backend == "codex":
            return f"Install Codex CLI or set CODEX_CLI_PATH in the {runtime_scope} runtime."
        if backend == "claude_code":
            return f"Install Claude Code CLI or SDK in the {runtime_scope} runtime."
    if failure_class == "auth_required":
        if backend == "codex":
            return f"Authenticate Codex CLI in the {runtime_scope} runtime before starting rollout jobs."
        if backend == "claude_code":
            return f"Configure Claude CLI or SDK credentials in the {runtime_scope} runtime."
    if failure_class == "provider_unreachable":
        return f"Verify outbound connectivity and provider availability in the {runtime_scope} runtime."
    if failure_class == "sdk_unavailable":
        return "Install or configure the Claude SDK, or use the Claude CLI fallback."
    return f"Review {backend} runtime configuration in the {runtime_scope} environment."


def _codex_smoke_local(executable: str, cwd: str) -> dict[str, Any]:
    result = _run_local_command(
        [
            executable,
            "exec",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
            "--color",
            "never",
            'Return only a JSON object: {"ok": true}',
        ],
        timeout=30,
        cwd=cwd,
    )
    detail = (result.stderr or result.stdout or "").strip()
    return _command_result(
        result.returncode == 0,
        detail or "Codex CLI smoke run succeeded",
        returncode=result.returncode,
    )


def _codex_smoke_container(container_name: str) -> dict[str, Any]:
    shell = """
set -eu
if [ -n "${CODEX_CLI_PATH:-}" ] && [ -x "${CODEX_CLI_PATH}" ]; then
  exe="${CODEX_CLI_PATH}"
elif command -v codex >/dev/null 2>&1; then
  exe="$(command -v codex)"
elif command -v codex-cli >/dev/null 2>&1; then
  exe="$(command -v codex-cli)"
else
  echo "codex executable not found"
  exit 127
fi
"${exe}" exec --sandbox read-only --skip-git-repo-check --color never 'Return only a JSON object: {"ok": true}'
"""
    result = _run_container_shell(shell, timeout=30, container_name=container_name)
    detail = (result.stderr or result.stdout or "").strip()
    return _command_result(
        result.returncode == 0,
        detail or "Codex CLI smoke run succeeded",
        returncode=result.returncode,
    )


async def _claude_sdk_smoke(manager: ClaudeSDKManager) -> dict[str, Any]:
    result = await asyncio.wait_for(manager.simple_query("Return only: OK", {"system_prompt": "Return only OK"}), 20)
    if result.get("error"):
        return _command_result(False, str(result.get("error", "")).strip())
    responses = result.get("responses", []) if isinstance(result.get("responses"), list) else []
    text = "\n".join(str(item.get("content", "")).strip() for item in responses if isinstance(item, dict)).strip()
    return _command_result(bool(text), text or "Claude SDK returned empty output")


def _run_async_sync(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict[str, Any] = {}
    error: list[BaseException] = []

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - passthrough
            error.append(exc)

    import threading

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return result.get("value")


def _claude_cli_smoke_local(executable: str, cwd: str) -> dict[str, Any]:
    result = _run_local_command([executable, "-p", "Return only: OK"], timeout=30, cwd=cwd)
    detail = (result.stderr or result.stdout or "").strip()
    return _command_result(
        result.returncode == 0 and bool((result.stdout or "").strip()),
        detail or "Claude CLI smoke run succeeded",
        returncode=result.returncode,
    )


def _claude_cli_smoke_container(container_name: str) -> dict[str, Any]:
    shell = """
set -eu
if [ -n "${CLAUDE_CLI_PATH:-}" ] && [ -x "${CLAUDE_CLI_PATH}" ]; then
  exe="${CLAUDE_CLI_PATH}"
elif command -v claude >/dev/null 2>&1; then
  exe="$(command -v claude)"
elif command -v claude-code >/dev/null 2>&1; then
  exe="$(command -v claude-code)"
else
  echo "claude executable not found"
  exit 127
fi
"${exe}" -p 'Return only: OK'
"""
    result = _run_container_shell(shell, timeout=30, container_name=container_name)
    detail = (result.stderr or result.stdout or "").strip()
    return _command_result(
        result.returncode == 0 and bool((result.stdout or "").strip()),
        detail or "Claude CLI smoke run succeeded",
        returncode=result.returncode,
    )


def check_backend_readiness(
    backend: str,
    provider: str = "",
    api_base: str = "",
    runtime_scope: str = "current",
) -> dict[str, Any]:
    scope = (runtime_scope or "current").strip().lower() or "current"
    current_scope = current_runtime_scope()
    resolved_scope = current_scope if scope == "current" else scope
    checks: list[dict[str, Any]] = []
    response: dict[str, Any] = {
        "backend": backend,
        "provider": provider,
        "runtime_scope": resolved_scope,
        "current_runtime_scope": current_scope,
        "ready": False,
        "status": "runtime_misconfigured",
        "checks": checks,
        "fix_hint": "",
        "runtime": "",
    }

    if resolved_scope not in {"host", "container"}:
        response["status"] = "runtime_misconfigured"
        response["fix_hint"] = f"Unsupported runtime scope '{resolved_scope}'."
        return response

    if resolved_scope != current_scope:
        if resolved_scope == "container" and current_scope == "host":
            if not _container_is_available(DEFAULT_CONTAINER_NAME):
                detail = f"Container runtime '{DEFAULT_CONTAINER_NAME}' is not available from host."
                response["status"] = "provider_unreachable"
                response["fix_hint"] = detail
                checks.append(_command_result(False, detail, id="runtime_scope"))
                return response
        else:
            detail = f"{resolved_scope} readiness cannot be checked from the current {current_scope} runtime."
            response["status"] = "runtime_misconfigured"
            response["fix_hint"] = detail
            checks.append(_command_result(False, detail, id="runtime_scope"))
            return response

    if backend == "native":
        provider_check = _provider_check(provider, api_base)
        checks.append({"id": "provider", **provider_check})
        response["ready"] = bool(provider_check["ok"])
        response["status"] = "ready" if response["ready"] else str(provider_check.get("failure_class", "auth_required"))
        response["fix_hint"] = "" if response["ready"] else _fix_hint(backend, response["status"], resolved_scope)
        response["runtime"] = "native"
        return response

    if backend == "codex":
        executable = _resolve_external_executable("codex") if resolved_scope == current_scope else "docker-exec"
        checks.append(
            {
                "id": "executable",
                "ok": bool(executable),
                "detail": f"codex executable {'found' if executable else 'not found'}",
                "executable": executable,
            }
        )
        if not executable:
            response["status"] = "missing_executable"
            response["fix_hint"] = _fix_hint("codex", response["status"], resolved_scope)
            return response
        smoke = (
            _codex_smoke_local(executable, os.getcwd())
            if resolved_scope == current_scope
            else _codex_smoke_container(DEFAULT_CONTAINER_NAME)
        )
        checks.append({"id": "smoke", **smoke})
        response["ready"] = bool(smoke["ok"])
        response["status"] = (
            "ready" if response["ready"] else _classify_failure(str(smoke["detail"]), "runtime_misconfigured")
        )
        response["fix_hint"] = "" if response["ready"] else _fix_hint("codex", response["status"], resolved_scope)
        response["runtime"] = "codex_cli"
        response["executable"] = executable
        return response

    if backend == "claude_code":
        manager = ClaudeSDKManager() if resolved_scope == current_scope else None
        sdk_available = bool(manager and manager.sdk_available)
        checks.append(
            {
                "id": "sdk",
                "ok": sdk_available,
                "detail": "Claude SDK available" if sdk_available else "Claude SDK unavailable",
            }
        )
        if sdk_available and manager is not None:
            sdk_smoke = _run_async_sync(_claude_sdk_smoke(manager))
            checks.append({"id": "sdk_smoke", **sdk_smoke})
            if sdk_smoke["ok"]:
                response["ready"] = True
                response["status"] = "ready"
                response["runtime"] = "claude_sdk"
                return response
        executable = _resolve_external_executable("claude_code") if resolved_scope == current_scope else "docker-exec"
        checks.append(
            {
                "id": "cli",
                "ok": bool(executable),
                "detail": f"claude executable {'found' if executable else 'not found'}",
                "executable": executable,
            }
        )
        if not executable:
            last_detail = ""
            for check in checks:
                if not check.get("ok"):
                    last_detail = str(check.get("detail", "")).strip()
            response["status"] = _classify_failure(last_detail, "missing_executable")
            response["fix_hint"] = _fix_hint("claude_code", response["status"], resolved_scope)
            return response
        smoke = (
            _claude_cli_smoke_local(executable, os.getcwd())
            if resolved_scope == current_scope
            else _claude_cli_smoke_container(DEFAULT_CONTAINER_NAME)
        )
        checks.append({"id": "cli_smoke", **smoke})
        response["ready"] = bool(smoke["ok"])
        response["status"] = (
            "ready" if response["ready"] else _classify_failure(str(smoke["detail"]), "runtime_misconfigured")
        )
        response["fix_hint"] = "" if response["ready"] else _fix_hint("claude_code", response["status"], resolved_scope)
        response["runtime"] = "claude_cli"
        response["executable"] = executable
        return response

    response["status"] = "runtime_misconfigured"
    response["fix_hint"] = f"Unsupported backend '{backend}'."
    return response
