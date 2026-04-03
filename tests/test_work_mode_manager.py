# tests/test_work_mode_manager.py
import threading
from unittest.mock import MagicMock, patch

from python.helpers.work_mode.manager import WorkModeManager
from python.helpers.work_mode.types import HardwareProfile, ModeContext, WorkMode


def _make_manager() -> WorkModeManager:
    mgr = WorkModeManager.__new__(WorkModeManager)
    mgr._mode = WorkMode.LOCAL
    mgr._selective_consents = frozenset()
    mgr._profile = HardwareProfile()
    mgr._listeners = []
    mgr._drain = MagicMock()
    mgr._switch_lock = threading.Lock()
    mgr._loop = None
    mgr._profiler = MagicMock()
    mgr._profiler.probe.return_value = HardwareProfile(ram_gb=16.0, has_network=True, suggested_mode=WorkMode.CLOUD)
    return mgr


def test_get_mode_returns_current_mode():
    mgr = _make_manager()
    mgr._mode = WorkMode.CLOUD
    assert mgr.get_mode() == WorkMode.CLOUD


def test_get_snapshot_is_frozen():
    mgr = _make_manager()
    snap = mgr.get_snapshot()
    assert isinstance(snap, ModeContext)
    assert snap.mode == WorkMode.LOCAL


def test_snapshot_is_immutable():
    """Snapshot taken before request_switch() is unaffected by the switch."""
    mgr = _make_manager()
    mgr._drain.drain.return_value = True
    snap_before = mgr.get_snapshot()
    assert snap_before.mode == WorkMode.LOCAL

    with patch.object(mgr, "_persist_mode"), patch.object(mgr, "_reload_llm_router"):
        mgr.request_switch(WorkMode.CLOUD)

    snap_after = mgr.get_snapshot()
    assert snap_before.mode == WorkMode.LOCAL  # pre-switch snapshot unaffected
    assert snap_after.mode == WorkMode.CLOUD


def test_drain_called_with_correct_timeout():
    """request_switch() drains with 60s timeout before applying the new mode."""
    mgr = _make_manager()
    mgr._drain.drain.return_value = True

    with patch.object(mgr, "_persist_mode"), patch.object(mgr, "_reload_llm_router"):
        mgr.request_switch(WorkMode.CLOUD)

    mgr._drain.drain.assert_called_once_with(timeout=60.0)


def test_switch_listener_called_on_confirm():
    mgr = _make_manager()
    received = []
    mgr.add_switch_listener(received.append)
    mgr._drain.drain.return_value = True

    with patch.object(mgr, "_persist_mode"), patch.object(mgr, "_reload_llm_router"):
        mgr.request_switch(WorkMode.CLOUD)

    assert WorkMode.CLOUD in received


def test_switch_updates_mode():
    mgr = _make_manager()
    mgr._drain.drain.return_value = True

    with patch.object(mgr, "_persist_mode"), patch.object(mgr, "_reload_llm_router"):
        mgr.request_switch(WorkMode.CLOUD)

    assert mgr.get_mode() == WorkMode.CLOUD


def test_get_snapshot_includes_selective_consents():
    mgr = _make_manager()
    mgr._mode = WorkMode.SELECTIVE
    mgr._selective_consents = frozenset({"gmail", "stripe"})
    snap = mgr.get_snapshot()
    assert "gmail" in snap.selective_consents
    assert "stripe" in snap.selective_consents
