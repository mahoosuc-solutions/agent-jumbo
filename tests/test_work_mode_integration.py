# tests/test_work_mode_integration.py
"""End-to-end integration tests for the Work Mode system.

Tests full startup sequence and mode switch flow without real hardware.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from python.helpers.work_mode.gate import ModeGate, ModeViolationError
from python.helpers.work_mode.manager import WorkModeManager
from python.helpers.work_mode.profiler import ResourceProfiler
from python.helpers.work_mode.types import Capability, HardwareProfile, ModeContext, WorkMode


@pytest.fixture(autouse=True)
def reset_manager():
    """Ensure each test gets a fresh WorkModeManager."""
    WorkModeManager._instance = None
    yield
    WorkModeManager._instance = None


def _mock_profile(mode: WorkMode) -> HardwareProfile:
    return HardwareProfile(
        ram_gb=16.0,
        has_network=(mode != WorkMode.LOCAL),
        suggested_mode=mode,
    )


def test_startup_local_mode_selected_when_no_network():
    with patch.object(ResourceProfiler, "probe", return_value=_mock_profile(WorkMode.LOCAL)):
        with patch(
            "python.helpers.work_mode.manager.WorkModeManager._load_persisted_mode",
            return_value=None,
        ):
            with patch("python.helpers.work_mode.manager.WorkModeManager._persist_mode"):
                with patch(
                    "python.helpers.work_mode.manager.WorkModeManager._load_persisted_consents",
                    return_value=[],
                ):
                    mgr = WorkModeManager.get_instance()
                    mgr._drain = MagicMock()
                    mgr.initialize()

    assert mgr.get_mode() == WorkMode.LOCAL


def test_persisted_mode_overrides_suggestion():
    with patch.object(ResourceProfiler, "probe", return_value=_mock_profile(WorkMode.LOCAL)):
        with patch(
            "python.helpers.work_mode.manager.WorkModeManager._load_persisted_mode",
            return_value=WorkMode.CLOUD,
        ):
            with patch("python.helpers.work_mode.manager.WorkModeManager._persist_mode"):
                with patch(
                    "python.helpers.work_mode.manager.WorkModeManager._load_persisted_consents",
                    return_value=[],
                ):
                    mgr = WorkModeManager.get_instance()
                    mgr._drain = MagicMock()
                    mgr.initialize()

    assert mgr.get_mode() == WorkMode.CLOUD


def test_snapshot_isolation_across_mode_switch():
    """Task captures LOCAL snapshot; switch to CLOUD; task snapshot unchanged."""
    mgr = WorkModeManager.get_instance()
    mgr._mode = WorkMode.LOCAL
    mgr._selective_consents = frozenset()
    mgr._drain = MagicMock()
    mgr._drain.drain.return_value = True
    mgr._profiler = MagicMock()
    mgr._profiler.probe.return_value = _mock_profile(WorkMode.CLOUD)

    # Task captures snapshot before switch
    task_snapshot = mgr.get_snapshot()
    assert task_snapshot.mode == WorkMode.LOCAL

    with patch.object(mgr, "_persist_mode"), patch.object(mgr, "_reload_llm_router"):
        mgr.request_switch(WorkMode.CLOUD)

    # Manager is now CLOUD
    assert mgr.get_mode() == WorkMode.CLOUD
    # Task snapshot is still LOCAL (immutable)
    assert task_snapshot.mode == WorkMode.LOCAL


def test_gate_blocks_external_in_local_snapshot():
    ctx = ModeContext(mode=WorkMode.LOCAL, selective_consents=frozenset(), captured_at=time.monotonic())
    with pytest.raises(ModeViolationError):
        ModeGate.require(Capability.GMAIL, ctx)


def test_gate_allows_after_switch_to_cloud():
    ctx_cloud = ModeContext(mode=WorkMode.CLOUD, selective_consents=frozenset(), captured_at=time.monotonic())
    ModeGate.require(Capability.GMAIL, ctx_cloud)  # must not raise


def test_selective_consent_roundtrip():
    mgr = WorkModeManager.get_instance()
    mgr._mode = WorkMode.SELECTIVE
    mgr._selective_consents = frozenset()

    with patch.object(mgr, "_persist_consents"):
        mgr.update_selective_consents({"gmail", "stripe"})

    snap = mgr.get_snapshot()
    assert "gmail" in snap.selective_consents
    ctx = ModeContext(
        mode=WorkMode.SELECTIVE,
        selective_consents=snap.selective_consents,
        captured_at=time.monotonic(),
    )
    ModeGate.require(Capability.GMAIL, ctx)  # allowed
    with pytest.raises(ModeViolationError):
        ModeGate.require(Capability.LINEAR, ctx)  # not consented
