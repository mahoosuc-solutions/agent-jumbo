import threading

import pytest


def test_profile_mappings_and_autostart_flags():
    from python.helpers import service_profile

    assert service_profile.get_profile_services("full") == [
        "run_ui",
        "run_searxng",
        "run_cron",
        "run_sshd",
        "run_tunnel_api",
    ]
    assert service_profile.get_profile_services("local-lite") == ["run_ui"]
    assert service_profile.get_profile_services("research") == ["run_ui", "run_searxng"]

    assert service_profile.get_autostart_flags("full") == {
        "RUN_UI_AUTOSTART": "true",
        "RUN_SEARXNG_AUTOSTART": "true",
        "RUN_CRON_AUTOSTART": "true",
        "RUN_SSHD_AUTOSTART": "true",
        "RUN_TUNNEL_API_AUTOSTART": "true",
    }
    assert service_profile.get_autostart_flags("local-lite") == {
        "RUN_UI_AUTOSTART": "true",
        "RUN_SEARXNG_AUTOSTART": "false",
        "RUN_CRON_AUTOSTART": "false",
        "RUN_SSHD_AUTOSTART": "false",
        "RUN_TUNNEL_API_AUTOSTART": "false",
    }
    assert service_profile.get_autostart_flags("research") == {
        "RUN_UI_AUTOSTART": "true",
        "RUN_SEARXNG_AUTOSTART": "true",
        "RUN_CRON_AUTOSTART": "false",
        "RUN_SSHD_AUTOSTART": "false",
        "RUN_TUNNEL_API_AUTOSTART": "false",
    }


def test_snapshot_reports_supported_runtime_state(monkeypatch):
    from python.helpers import service_profile

    service_profile.invalidate_cache()
    monkeypatch.setattr(service_profile, "get_current_profile", lambda: "research")
    monkeypatch.setattr(service_profile, "is_supported", lambda: True)
    monkeypatch.setattr(
        service_profile,
        "get_runtime_states",
        lambda: {
            "run_ui": "running",
            "run_searxng": "stopped",
            "run_cron": "exited",
            "run_sshd": "running",
            "run_tunnel_api": "fatal",
        },
    )

    payload = service_profile.snapshot(force_refresh=True)

    assert payload["current_profile"] == "research"
    assert payload["supported"] is True
    assert payload["can_apply"] is True
    assert payload["restart_strategy"] == "managed_restart"
    states = {entry["id"]: entry for entry in payload["services"]}
    assert states["run_ui"]["enabled"] is True
    assert states["run_searxng"]["enabled"] is True
    assert states["run_cron"]["enabled"] is False
    assert states["run_ui"]["runtime_state"] == "running"
    assert states["run_tunnel_api"]["runtime_state"] == "fatal"


def test_snapshot_reports_unknown_runtime_state_when_unsupported(monkeypatch):
    from python.helpers import service_profile

    service_profile.invalidate_cache()
    monkeypatch.setattr(service_profile, "get_current_profile", lambda: "local-lite")
    monkeypatch.setattr(service_profile, "is_supported", lambda: False)

    payload = service_profile.snapshot(force_refresh=True)

    assert payload["supported"] is False
    assert payload["can_apply"] is False
    states = {entry["id"]: entry for entry in payload["services"]}
    assert states["run_ui"]["enabled"] is True
    assert states["run_searxng"]["enabled"] is False
    assert all(entry["runtime_state"] == "unknown" for entry in payload["services"])


def test_apply_profile_reconciles_only_non_ui_services(monkeypatch):
    from python.helpers import service_profile

    executed = []

    monkeypatch.setattr(service_profile, "persist_profile", lambda profile: profile)
    monkeypatch.setattr(service_profile, "is_supported", lambda: True)
    monkeypatch.setattr(service_profile, "get_current_profile", lambda: "local-lite")
    monkeypatch.setattr(service_profile, "invalidate_cache", lambda: None)
    monkeypatch.setattr(
        service_profile,
        "_run_supervisorctl",
        lambda *args: executed.append(args),
    )

    result = service_profile.apply_profile("full")

    assert executed == [
        ("start", "run_searxng"),
        ("start", "run_cron"),
        ("start", "run_sshd"),
        ("start", "run_tunnel_api"),
    ]
    assert result == {
        "selected_profile": "full",
        "started": ["run_searxng", "run_cron", "run_sshd", "run_tunnel_api"],
        "stopped": [],
        "unchanged": [],
    }
    assert all("run_ui" not in command for command in executed)


def test_apply_profile_raises_when_unsupported(monkeypatch):
    from python.helpers import service_profile

    persist_calls = []

    monkeypatch.setattr(service_profile, "persist_profile", lambda profile: persist_calls.append(profile) or profile)
    monkeypatch.setattr(service_profile, "is_supported", lambda: False)

    with pytest.raises(RuntimeError, match="supported only in dockerized supervisor runs"):
        service_profile.apply_profile("research")

    assert persist_calls == []


def test_persist_profile_rejects_invalid_profile():
    from python.helpers import service_profile

    with pytest.raises(ValueError, match="Unsupported profile"):
        service_profile.persist_profile("invalid")


def test_schedule_run_ui_restart_uses_supervisorctl(monkeypatch):
    from python.helpers import service_profile

    popen_calls = []

    class FakePopen:
        def __init__(self, args, **kwargs):
            popen_calls.append((args, kwargs))

    monkeypatch.setattr(service_profile, "is_supported", lambda: True)
    monkeypatch.setattr(service_profile.subprocess, "Popen", FakePopen)

    service_profile.schedule_run_ui_restart(delay_seconds=2.0)

    assert len(popen_calls) == 1
    args, kwargs = popen_calls[0]
    assert args[:2] == ["/bin/bash", "-lc"]
    assert "sleep 2.0" in args[2]
    assert "unix:///var/run/supervisor.sock" in args[2]
    assert "restart run_ui" in args[2]
    assert kwargs["start_new_session"] is True


def test_schedule_run_ui_restart_skips_when_unsupported(monkeypatch):
    from python.helpers import service_profile

    monkeypatch.setattr(service_profile, "is_supported", lambda: False)
    monkeypatch.setattr(
        service_profile.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("Popen should not be called"),
    )

    service_profile.schedule_run_ui_restart()


def test_get_runtime_states_accepts_supervisor_status_exit_code_three(monkeypatch):
    from python.helpers import service_profile

    monkeypatch.setattr(service_profile, "is_supported", lambda: True)
    monkeypatch.setattr(
        service_profile.subprocess,
        "run",
        lambda *args, **kwargs: service_profile.subprocess.CompletedProcess(
            args=args[0],
            returncode=3,
            stdout="\n".join(
                [
                    "run_ui                           RUNNING   pid 1720, uptime 0:01:00",
                    "run_searxng                      RUNNING   pid 27, uptime 0:15:04",
                    "run_cron                         STOPPED   Mar 26 03:06 AM",
                    "run_sshd                         STOPPED   Mar 26 03:06 AM",
                    "run_tunnel_api                   STOPPED   Mar 26 03:06 AM",
                ]
            ),
            stderr="",
        ),
    )

    states = service_profile.get_runtime_states()

    assert states == {
        "run_ui": "running",
        "run_searxng": "running",
        "run_cron": "stopped",
        "run_sshd": "stopped",
        "run_tunnel_api": "stopped",
    }


@pytest.mark.asyncio
async def test_service_profile_get_handler_forces_refresh(monkeypatch):
    from flask import Flask

    from python.api.service_profile_get import GetServiceProfile

    monkeypatch.setattr(
        "python.api.service_profile_get.service_profile.snapshot",
        lambda force_refresh=False: {"force_refresh": force_refresh},
    )

    handler = GetServiceProfile(Flask(__name__), threading.Lock())
    payload = await handler.process({}, None)

    assert payload == {"force_refresh": True}


@pytest.mark.asyncio
async def test_service_profile_set_handler_applies_and_restarts(monkeypatch):
    from flask import Flask

    from python.api.service_profile_set import SetServiceProfile

    calls = []

    monkeypatch.setattr(
        "python.api.service_profile_set.service_profile.is_valid_profile",
        lambda profile: profile == "research",
    )
    monkeypatch.setattr(
        "python.api.service_profile_set.service_profile.apply_profile",
        lambda profile: (
            calls.append(("apply", profile))
            or {"selected_profile": profile, "started": ["run_searxng"], "stopped": [], "unchanged": []}
        ),
    )
    monkeypatch.setattr(
        "python.api.service_profile_set.service_profile.schedule_run_ui_restart",
        lambda: calls.append(("restart", None)),
    )

    handler = SetServiceProfile(Flask(__name__), threading.Lock())
    payload = await handler.process({"profile": "research"}, None)

    assert payload == {
        "ok": True,
        "selected_profile": "research",
        "started": ["run_searxng"],
        "stopped": [],
        "unchanged": [],
        "restart_scheduled": True,
    }
    assert calls == [("apply", "research"), ("restart", None)]


@pytest.mark.asyncio
async def test_service_profile_set_handler_rejects_invalid_profile(monkeypatch):
    from flask import Flask

    from python.api.service_profile_set import SetServiceProfile

    monkeypatch.setattr(
        "python.api.service_profile_set.service_profile.is_valid_profile",
        lambda profile: False,
    )

    handler = SetServiceProfile(Flask(__name__), threading.Lock())

    with pytest.raises(ValueError, match="Unsupported profile"):
        await handler.process({"profile": "invalid"}, None)


def test_snapshot_uses_cache_until_force_refresh(monkeypatch):
    from python.helpers import service_profile

    runtime_states_calls = []
    fake_times = iter([100.0, 100.5, 103.0])

    service_profile.invalidate_cache()
    monkeypatch.setattr(service_profile.time, "time", lambda: next(fake_times))
    monkeypatch.setattr(service_profile, "get_current_profile", lambda: "research")
    monkeypatch.setattr(service_profile, "is_supported", lambda: True)
    monkeypatch.setattr(
        service_profile,
        "get_runtime_states",
        lambda: runtime_states_calls.append("called") or {"run_ui": "running"},
    )

    first = service_profile.snapshot()
    second = service_profile.snapshot()
    third = service_profile.snapshot(force_refresh=True)

    assert len(runtime_states_calls) == 2
    assert first["services"][0]["runtime_state"] == "running"
    assert second["services"][0]["runtime_state"] == "running"
    assert third["services"][0]["runtime_state"] == "running"
