# tests/test_work_mode_profiler.py
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from python.helpers.work_mode.profiler import ResourceProfiler
from python.helpers.work_mode.types import WorkMode


def _make_profiler():
    return ResourceProfiler()


def test_probe_low_ram_no_gpu_no_network():
    profiler = _make_profiler()
    with (
        patch("psutil.virtual_memory") as vm,
        patch.object(profiler, "_probe_gpu", return_value=(False, 0.0)),
        patch.object(profiler, "_probe_network", return_value=False),
    ):
        vm.return_value = MagicMock(total=4 * 1024**3)  # 4 GB
        profile = profiler.probe()

    assert profile.ram_gb == pytest.approx(4.0, abs=0.1)
    assert profile.has_gpu is False
    assert profile.local_inference_eligible is False
    assert profile.has_network is False
    assert profile.suggested_mode == WorkMode.LOCAL


def test_probe_high_ram_gpu_with_network():
    profiler = _make_profiler()
    with (
        patch("psutil.virtual_memory") as vm,
        patch.object(profiler, "_probe_gpu", return_value=(True, 8.0)),
        patch.object(profiler, "_probe_network", return_value=True),
    ):
        vm.return_value = MagicMock(total=32 * 1024**3)
        profile = profiler.probe()

    assert profile.ram_gb == pytest.approx(32.0, abs=0.1)
    assert profile.has_gpu is True
    assert profile.vram_gb == pytest.approx(8.0)
    assert profile.local_inference_eligible is True
    assert profile.has_network is True
    assert profile.suggested_mode == WorkMode.CLOUD


def test_probe_gpu_insufficient_vram():
    profiler = _make_profiler()
    with (
        patch("psutil.virtual_memory") as vm,
        patch.object(profiler, "_probe_gpu", return_value=(True, 1.5)),
        patch.object(profiler, "_probe_network", return_value=False),
    ):
        vm.return_value = MagicMock(total=16 * 1024**3)
        profile = profiler.probe()

    assert profile.has_gpu is True
    assert profile.local_inference_eligible is False  # VRAM < 2GB


def test_nvidia_smi_timeout_is_caught():
    """subprocess.TimeoutExpired from nvidia-smi is caught and returns (False, 0.0)."""
    profiler = _make_profiler()
    with (
        patch(
            "python.helpers.work_mode.profiler.subprocess.run",
            side_effect=subprocess.TimeoutExpired("nvidia-smi", 3),
        ),
        patch.dict("sys.modules", {"torch": None}),
    ):
        has_gpu, vram_gb = profiler._probe_gpu()
    assert has_gpu is False
    assert vram_gb == 0.0


def test_suggest_mode_selective_when_gpu_eligible_no_network():
    """GPU-eligible machine with no network should suggest SELECTIVE mode."""
    profiler = _make_profiler()
    with (
        patch("psutil.virtual_memory") as vm,
        patch.object(profiler, "_probe_gpu", return_value=(True, 4.0)),
        patch.object(profiler, "_probe_network", return_value=False),
    ):
        vm.return_value = MagicMock(total=16 * 1024**3)
        profile = profiler.probe()

    assert profile.local_inference_eligible is True
    assert profile.has_network is False
    assert profile.suggested_mode == WorkMode.SELECTIVE


def test_network_probe_unreachable():
    profiler = _make_profiler()
    with patch("socket.create_connection", side_effect=OSError("unreachable")):
        assert profiler._probe_network() is False


def test_network_probe_reachable():
    profiler = _make_profiler()
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)
    with patch("socket.create_connection", return_value=mock_sock):
        assert profiler._probe_network() is True
