# python/helpers/work_mode/profiler.py
from __future__ import annotations

import logging
import socket
import subprocess

import psutil

from python.helpers.work_mode.types import HardwareProfile, WorkMode

log = logging.getLogger(__name__)

_MIN_VRAM_GB = 2.0
_NETWORK_HOST = "1.1.1.1"
_NETWORK_PORT = 443
_NETWORK_TIMEOUT = 2.0
_NVIDIA_TIMEOUT = 3


class ResourceProfiler:
    """Probes hardware and network to produce a HardwareProfile."""

    def probe(self) -> HardwareProfile:
        ram_gb = psutil.virtual_memory().total / (1024**3)
        has_gpu, vram_gb = self._probe_gpu()
        local_inference_eligible = has_gpu and vram_gb >= _MIN_VRAM_GB
        has_network = self._probe_network()
        suggested_mode = self._suggest_mode(ram_gb, local_inference_eligible, has_network)
        return HardwareProfile(
            ram_gb=ram_gb,
            vram_gb=vram_gb,
            has_gpu=has_gpu,
            local_inference_eligible=local_inference_eligible,
            has_network=has_network,
            suggested_mode=suggested_mode,
        )

    def _probe_gpu(self) -> tuple[bool, float]:
        """Return (has_gpu, vram_gb). Never raises; timeout-safe for WSL2."""
        try:
            result = subprocess.run(  # nosec B603 B607 — fixed args, no user input
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=_NVIDIA_TIMEOUT,
            )
            if result.returncode == 0:
                lines = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
                if lines:
                    vram_mb = float(lines[0])
                    return True, vram_mb / 1024.0
        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError, OSError) as e:
            log.debug("nvidia-smi probe: %s", e)

        # Fallback: check torch if available
        try:
            import torch

            if torch.cuda.is_available():
                vram_bytes = torch.cuda.get_device_properties(0).total_memory
                return True, vram_bytes / (1024**3)
        except Exception as e:
            log.debug("torch GPU probe: %s", e)

        return False, 0.0

    def _probe_network(self) -> bool:
        """Return True if external network is reachable via TCP to 1.1.1.1:443."""
        try:
            with socket.create_connection((_NETWORK_HOST, _NETWORK_PORT), timeout=_NETWORK_TIMEOUT):
                return True
        except OSError:
            return False

    def _suggest_mode(self, ram_gb: float, local_inference_eligible: bool, has_network: bool) -> WorkMode:
        if has_network and ram_gb >= 8.0:
            return WorkMode.CLOUD
        if local_inference_eligible:
            return WorkMode.SELECTIVE
        return WorkMode.LOCAL
