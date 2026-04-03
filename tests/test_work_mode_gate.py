# tests/test_work_mode_gate.py
import time

import pytest

from python.helpers.work_mode.gate import ModeGate, ModeViolationError
from python.helpers.work_mode.types import Capability, ModeContext, WorkMode


def _ctx(mode: WorkMode, consents: set[str] | None = None) -> ModeContext:
    return ModeContext(
        mode=mode,
        selective_consents=frozenset(consents or []),
        captured_at=time.monotonic(),
    )


# LOCAL mode blocks all EXTERNAL_* capabilities
@pytest.mark.parametrize(
    "cap",
    [
        Capability.EXTERNAL_LLM,
        Capability.EXTERNAL_STORAGE,
        Capability.STRIPE,
        Capability.GMAIL,
        Capability.GENERIC_OUTBOUND,
    ],
)
def test_local_blocks_external(cap):
    ctx = _ctx(WorkMode.LOCAL)
    with pytest.raises(ModeViolationError) as exc_info:
        ModeGate.require(cap, ctx)
    assert exc_info.value.capability == cap
    assert exc_info.value.mode == WorkMode.LOCAL


# CLOUD mode allows all capabilities
@pytest.mark.parametrize("cap", list(Capability))
def test_cloud_allows_all(cap):
    ctx = _ctx(WorkMode.CLOUD)
    ModeGate.require(cap, ctx)  # must not raise


# SELECTIVE blocks integration if not in consents
def test_selective_blocks_unconsented():
    ctx = _ctx(WorkMode.SELECTIVE, consents={"gmail"})
    with pytest.raises(ModeViolationError) as exc_info:
        ModeGate.require(Capability.STRIPE, ctx)
    assert exc_info.value.capability == Capability.STRIPE


# SELECTIVE allows integration if in consents
def test_selective_allows_consented():
    ctx = _ctx(WorkMode.SELECTIVE, consents={"gmail"})
    ModeGate.require(Capability.GMAIL, ctx)  # must not raise


# SELECTIVE allows EXTERNAL_LLM only if external_llm is consented
def test_selective_blocks_external_llm_without_consent():
    ctx = _ctx(WorkMode.SELECTIVE, consents=set())
    with pytest.raises(ModeViolationError):
        ModeGate.require(Capability.EXTERNAL_LLM, ctx)


def test_mode_violation_error_has_structured_fields():
    ctx = _ctx(WorkMode.LOCAL)
    try:
        ModeGate.require(Capability.GMAIL, ctx)
    except ModeViolationError as e:
        assert e.mode == WorkMode.LOCAL
        assert e.capability == Capability.GMAIL
        assert "not_available_in_local_mode" in str(e)
