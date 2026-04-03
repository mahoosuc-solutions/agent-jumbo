# tests/test_work_mode_types.py
import dataclasses
import time

import pytest

from python.helpers.work_mode.types import (
    Capability,
    HardwareProfile,
    ModeContext,
    WorkMode,
)


def test_work_mode_enum_values():
    assert WorkMode.LOCAL.value == "local"
    assert WorkMode.SELECTIVE.value == "selective"
    assert WorkMode.CLOUD.value == "cloud"


def test_capability_enum_has_required_values():
    required = {
        "EXTERNAL_LLM",
        "EXTERNAL_STORAGE",
        "STRIPE",
        "GOOGLE_CALENDAR",
        "GMAIL",
        "LINEAR",
        "NOTION",
        "TELEGRAM",
        "GENERIC_OUTBOUND",
    }
    actual = {c.name for c in Capability}
    assert required.issubset(actual)


def test_hardware_profile_defaults():
    hp = HardwareProfile()
    assert hp.ram_gb == 0.0
    assert hp.vram_gb == 0.0
    assert hp.has_gpu is False
    assert hp.local_inference_eligible is False
    assert hp.has_network is False
    assert hp.suggested_mode == WorkMode.LOCAL


def test_mode_context_is_frozen():
    ctx = ModeContext(
        mode=WorkMode.LOCAL,
        selective_consents=frozenset(),
        captured_at=time.monotonic(),
    )
    assert dataclasses.fields(ctx)  # is a dataclass
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.mode = WorkMode.CLOUD  # type: ignore[misc]


def test_mode_context_selective_consents_immutable():
    ctx = ModeContext(
        mode=WorkMode.SELECTIVE,
        selective_consents=frozenset({"gmail", "stripe"}),
        captured_at=0.0,
    )
    assert "gmail" in ctx.selective_consents
    assert "stripe" in ctx.selective_consents
    # frozenset is immutable — attempting mutation raises AttributeError
    with pytest.raises(AttributeError):
        ctx.selective_consents.add("linear")  # type: ignore[attr-defined]
