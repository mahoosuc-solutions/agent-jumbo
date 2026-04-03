# python/helpers/work_mode/gate.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from python.helpers.work_mode.types import Capability, WorkMode

if TYPE_CHECKING:
    from python.helpers.work_mode.types import ModeContext

log = logging.getLogger(__name__)

# Capabilities that map to integration IDs in selective_consents
_CAPABILITY_TO_CONSENT_KEY: dict[Capability, str] = {
    Capability.EXTERNAL_LLM: "external_llm",
    Capability.EXTERNAL_STORAGE: "external_storage",
    Capability.STRIPE: "stripe",
    Capability.GOOGLE_CALENDAR: "google_calendar",
    Capability.GMAIL: "gmail",
    Capability.LINEAR: "linear",
    Capability.NOTION: "notion",
    Capability.TELEGRAM: "telegram",
    Capability.GENERIC_OUTBOUND: "generic_outbound",
}


class ModeViolationError(Exception):
    """Raised when an operation is blocked by the current WorkMode."""

    def __init__(self, capability: Capability, mode: WorkMode) -> None:
        self.capability = capability
        self.mode = mode
        super().__init__(f"not_available_in_{mode.value}_mode: capability={capability.name}")


class ModeGate:
    """Enforces data sovereignty at the callsite level."""

    @staticmethod
    def require(capability: Capability, context: ModeContext) -> None:
        """Raise ModeViolationError if *capability* is blocked in *context*."""
        mode = context.mode

        if mode == WorkMode.CLOUD:
            return  # all capabilities allowed

        if mode == WorkMode.LOCAL:
            raise ModeViolationError(capability, mode)

        # SELECTIVE: check per-integration consent
        consent_key = _CAPABILITY_TO_CONSENT_KEY.get(capability)
        if consent_key is None or consent_key not in context.selective_consents:
            log.warning("ModeGate: blocked %s in SELECTIVE mode (not consented)", capability.name)
            raise ModeViolationError(capability, mode)
