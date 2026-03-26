from unittest.mock import patch


def test_register_mos_schedules_skips_incompatible_scheduler():
    from python.helpers.mos_scheduler_init import register_mos_schedules

    result = register_mos_schedules()

    assert result == {"registered": [], "count": 0}


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
