from __future__ import annotations

from python.helpers import provider_readiness


def test_codex_readiness_reports_auth_required(monkeypatch):
    monkeypatch.setattr(provider_readiness, "current_runtime_scope", lambda: "host")
    monkeypatch.setattr(provider_readiness, "_resolve_external_executable", lambda backend: "/usr/bin/codex")
    monkeypatch.setattr(
        provider_readiness,
        "_codex_smoke_local",
        lambda executable, cwd: {"ok": False, "detail": "401 Unauthorized: Missing bearer authentication"},
    )

    result = provider_readiness.check_backend_readiness("codex", provider="openai", runtime_scope="host")

    assert result["ready"] is False
    assert result["status"] == "auth_required"
    assert "Authenticate Codex CLI" in result["fix_hint"]


def test_claude_readiness_uses_sdk_when_available(monkeypatch):
    class _Manager:
        sdk_available = True

    async def _fake_sdk_smoke(manager):
        return {"ok": True, "detail": "OK"}

    monkeypatch.setattr(provider_readiness, "current_runtime_scope", lambda: "host")
    monkeypatch.setattr(provider_readiness, "ClaudeSDKManager", lambda: _Manager())
    monkeypatch.setattr(provider_readiness, "_claude_sdk_smoke", _fake_sdk_smoke)

    result = provider_readiness.check_backend_readiness("claude_code", provider="anthropic", runtime_scope="host")

    assert result["ready"] is True
    assert result["status"] == "ready"
    assert result["runtime"] == "claude_sdk"


def test_container_scope_requires_running_container(monkeypatch):
    monkeypatch.setattr(provider_readiness, "current_runtime_scope", lambda: "host")
    monkeypatch.setattr(provider_readiness, "_container_is_available", lambda container_name: False)

    result = provider_readiness.check_backend_readiness("codex", provider="openai", runtime_scope="container")

    assert result["ready"] is False
    assert result["status"] == "provider_unreachable"
    assert "not available" in result["fix_hint"]
