import threading
from unittest.mock import patch

import pytest


def test_register_mos_schedules_skips_incompatible_scheduler():
    from python.helpers.mos_scheduler_init import register_mos_schedules

    result = register_mos_schedules()

    assert result["registered"] == []
    assert result["count"] == 0
    assert result["status"] == "skipped"
    assert result["skipped_reason"]


def test_initialize_keys_skips_missing_ecdsa_without_warning():
    from python.helpers.security import SecurityVaultManager

    original_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "ecdsa":
            raise ImportError("ecdsa unavailable")
        return original_import(name, *args, **kwargs)

    with patch.object(SecurityVaultManager, "get_secret", return_value=None):
        with patch("builtins.__import__", side_effect=fake_import):
            with patch("builtins.print") as mock_print:
                SecurityVaultManager.initialize_keys()

    mock_print.assert_not_called()


def test_init_a0_restores_chats_fully_in_background(monkeypatch):
    import run_ui

    recorded: list[tuple[str, str, str | None]] = []
    timeouts: list[object] = []

    class FakeTask:
        def result_sync(self, timeout=None):
            timeouts.append(timeout)
            return None

    class ImmediateThread:
        def __init__(self, target=None, daemon=None, name=None):
            self._target = target

        def start(self):
            if self._target:
                self._target()

    monkeypatch.setattr(run_ui.initialize, "initialize_chats", lambda: FakeTask())
    monkeypatch.setattr(run_ui.initialize, "initialize_mcp", lambda: None)
    monkeypatch.setattr(run_ui.initialize, "initialize_job_loop", lambda: None)
    monkeypatch.setattr(run_ui.initialize, "initialize_preload", lambda: None)
    monkeypatch.setattr(run_ui.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(
        run_ui.perf_metrics,
        "record_startup_phase",
        lambda name, duration_ms, status="success", error=None: recorded.append((name, status, error)),
    )
    monkeypatch.setattr(run_ui.PrintStyle, "print", lambda self, *args, **kwargs: None)
    run_ui._startup_tasks.clear()

    run_ui.init_a0()

    assert timeouts == [None]
    assert ("initialize_chats", "success", None) in recorded
    assert not any(status == "deferred" for _, status, _ in recorded)


def test_research_mode_skips_optional_startup_services(monkeypatch):
    import initialize

    monkeypatch.setattr("initialize.runtime_mode.get_run_mode", lambda: "research")
    monkeypatch.setattr("initialize.runtime_mode.is_reduced_startup_mode", lambda: True)
    monkeypatch.setattr(initialize.PrintStyle, "print", lambda self, *args, **kwargs: None)

    assert initialize.initialize_mcp() is None
    assert initialize.initialize_job_loop() is None
    assert initialize.initialize_preload() is None


@pytest.mark.asyncio
async def test_poll_exposes_startup_status(monkeypatch):
    from flask import Flask

    from agent import AgentContext
    from python.api.poll import Poll

    class FakeNotifications:
        guid = "guid"
        updates = []

        def output(self, start=0):
            return []

    monkeypatch.setattr(AgentContext, "_contexts", {})
    monkeypatch.setattr(AgentContext, "get_notification_manager", lambda: FakeNotifications())
    monkeypatch.setattr(
        "python.api.poll.get_settings",
        lambda: {
            "cowork_enabled": False,
            "cowork_allowed_paths": [],
            "chat_queue_wait_warn_seconds": 60,
        },
    )
    monkeypatch.setattr(
        "python.api.poll.startup_status.snapshot",
        lambda: {
            "run_mode": "local-lite",
            "chat_restore": {
                "status": "running",
                "active": True,
                "started_at": 123.0,
                "finished_at": None,
                "error": None,
            },
        },
    )
    monkeypatch.setattr(
        "python.api.poll.service_profile.snapshot",
        lambda: {
            "current_profile": "research",
            "supported": True,
            "restart_strategy": "managed_restart",
            "services": [],
        },
    )

    handler = Poll(Flask(__name__), threading.Lock())
    payload = await handler.process({}, None)

    assert payload["startup"]["run_mode"] == "local-lite"
    assert payload["startup"]["chat_restore"]["status"] == "running"
    assert payload["startup"]["chat_restore"]["active"] is True
    assert payload["service_profile"]["current_profile"] == "research"


@pytest.mark.asyncio
async def test_health_exposes_startup_status(monkeypatch):
    from flask import Flask

    from python.api.health import HealthCheck

    monkeypatch.setattr(
        "python.api.health.startup_status.snapshot",
        lambda: {
            "run_mode": "local-lite",
            "chat_restore": {
                "status": "success",
                "active": False,
                "started_at": 123.0,
                "finished_at": 124.0,
                "error": None,
            },
        },
    )
    monkeypatch.setattr(
        "python.api.health.service_profile.snapshot",
        lambda: {
            "current_profile": "local-lite",
            "supported": True,
            "restart_strategy": "managed_restart",
            "services": [],
        },
    )
    monkeypatch.setattr("python.api.health.git.get_git_info", lambda: {"version": "test"})
    monkeypatch.setattr("python.api.health.perf_metrics.snapshot", lambda: {"boot": "ok"})

    handler = HealthCheck(Flask(__name__), threading.Lock())
    payload = await handler.process({}, None)

    assert payload["checks"]["startup"]["run_mode"] == "local-lite"
    assert payload["checks"]["startup"]["chat_restore"]["status"] == "success"
    assert payload["checks"]["service_profile"]["current_profile"] == "local-lite"
