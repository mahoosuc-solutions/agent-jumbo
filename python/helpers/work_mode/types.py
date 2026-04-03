# python/helpers/work_mode/types.py
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class WorkMode(Enum):
    LOCAL = "local"
    SELECTIVE = "selective"
    CLOUD = "cloud"


class Capability(Enum):
    EXTERNAL_LLM = "external_llm"
    EXTERNAL_STORAGE = "external_storage"
    STRIPE = "stripe"
    GOOGLE_CALENDAR = "google_calendar"
    GMAIL = "gmail"
    LINEAR = "linear"
    NOTION = "notion"
    TELEGRAM = "telegram"
    GENERIC_OUTBOUND = "generic_outbound"


@dataclass
class HardwareProfile:
    ram_gb: float = 0.0
    vram_gb: float = 0.0
    has_gpu: bool = False
    local_inference_eligible: bool = False
    has_network: bool = False
    suggested_mode: WorkMode = WorkMode.LOCAL


@dataclass(frozen=True)
class ModeContext:
    mode: WorkMode
    selective_consents: frozenset[str]
    captured_at: float = field(default_factory=time.monotonic)
