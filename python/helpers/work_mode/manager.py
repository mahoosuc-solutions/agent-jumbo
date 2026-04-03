# python/helpers/work_mode/manager.py
from __future__ import annotations

import json
import logging
import threading
from typing import TYPE_CHECKING

from python.helpers.work_mode.drain import DrainCoordinator
from python.helpers.work_mode.profiler import ResourceProfiler
from python.helpers.work_mode.types import HardwareProfile, ModeContext, WorkMode

if TYPE_CHECKING:
    from collections.abc import Callable

log = logging.getLogger(__name__)

_SETTINGS_KEY_MODE = "work_mode"
_SETTINGS_KEY_CONSENTS = "selective_consents"


class WorkModeManager:
    """Single authoritative source of work mode truth.

    Consumers call get_snapshot() at task start and carry the immutable
    ModeContext for the lifetime of the task.
    """

    _instance: WorkModeManager | None = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._mode = WorkMode.LOCAL
        self._selective_consents: frozenset[str] = frozenset()
        self._profile = HardwareProfile()
        self._listeners: list[Callable[[WorkMode], None]] = []
        self._profiler = ResourceProfiler()
        self._drain = DrainCoordinator()
        self._switch_lock = threading.Lock()
        self._loop: object = None  # set by initialize() from async context

    @classmethod
    def get_instance(cls) -> WorkModeManager:
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def initialize(self) -> None:
        """Probe hardware, load persisted mode. Called once at startup."""
        import asyncio

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None  # not called from async context; reload will be best-effort

        self._profile = self._profiler.probe()
        persisted = self._load_persisted_mode()
        self._mode = persisted if persisted else self._profile.suggested_mode
        consents = self._load_persisted_consents()
        self._selective_consents = frozenset(consents)
        log.info(
            "WorkModeManager initialized: mode=%s suggested=%s",
            self._mode.value,
            self._profile.suggested_mode.value,
        )

    def get_mode(self) -> WorkMode:
        return self._mode

    def get_profile(self) -> HardwareProfile:
        return self._profile

    def get_snapshot(self) -> ModeContext:
        """Return an immutable snapshot for use by a task at spawn time."""
        return ModeContext(
            mode=self._mode,
            selective_consents=self._selective_consents,
        )

    def add_switch_listener(self, fn: Callable[[WorkMode], None]) -> None:
        self._listeners.append(fn)

    def request_switch(self, mode: WorkMode) -> None:
        """Staged mode switch: drain → re-probe → swap → notify. Synchronous."""
        with self._switch_lock:
            log.info("WorkModeManager: switching from %s to %s", self._mode.value, mode.value)
            drained = self._drain.drain(timeout=60.0)
            if not drained:
                log.warning("WorkModeManager: proceeding with switch despite incomplete drain")

            self._profile = self._profiler.probe()
            self._mode = mode
            self._persist_mode()
            self._reload_llm_router()

            for fn in self._listeners:
                try:
                    fn(mode)
                except Exception as e:
                    log.warning("WorkModeManager: listener error: %s", e)

    def update_selective_consents(self, consents: set[str]) -> None:
        self._selective_consents = frozenset(consents)
        self._persist_consents()

    def start_background_probe(self, interval: int = 300) -> None:
        """Start a daemon thread that re-probes network every interval seconds.

        Notifies listeners if network state changes. Does NOT auto-switch mode.
        """
        stop_event = threading.Event()
        self._probe_stop_event = stop_event

        def _probe_loop() -> None:
            while not stop_event.wait(timeout=interval):
                try:
                    new_profile = self._profiler.probe()
                    old_network = self._profile.has_network
                    self._profile = new_profile
                    if old_network != new_profile.has_network:
                        log.info(
                            "WorkModeManager: network state changed to %s",
                            new_profile.has_network,
                        )
                        for fn in self._listeners:
                            try:
                                fn(self._mode)
                            except Exception as e:
                                log.warning("WorkModeManager: listener error: %s", e)
                except Exception as e:
                    log.warning("WorkModeManager: background probe error: %s", e)

        t = threading.Thread(target=_probe_loop, daemon=True, name="work-mode-probe")
        t.start()

    def stop_background_probe(self) -> None:
        if hasattr(self, "_probe_stop_event"):
            self._probe_stop_event.set()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_persisted_mode(self) -> WorkMode | None:
        try:
            from python.helpers import dotenv

            raw = dotenv.get_dotenv_value(_SETTINGS_KEY_MODE)
            if raw:
                return WorkMode(raw)
        except Exception as e:
            log.debug("Could not load persisted mode: %s", e)
        return None

    def _persist_mode(self) -> None:
        try:
            from python.helpers import dotenv

            dotenv.save_dotenv_value(_SETTINGS_KEY_MODE, self._mode.value)
        except Exception as e:
            log.warning("Could not persist mode: %s", e)

    def _load_persisted_consents(self) -> list[str]:
        try:
            from python.helpers import dotenv

            raw = dotenv.get_dotenv_value(_SETTINGS_KEY_CONSENTS)
            if raw:
                return json.loads(raw)
        except Exception as e:
            log.debug("Could not load consents: %s", e)
        return []

    def _persist_consents(self) -> None:
        try:
            from python.helpers import dotenv

            dotenv.save_dotenv_value(_SETTINGS_KEY_CONSENTS, json.dumps(list(self._selective_consents)))
        except Exception as e:
            log.warning("Could not persist consents: %s", e)

    def _reload_llm_router(self) -> None:
        """Trigger LLM router re-discovery after mode switch.

        Schedules on the stored event loop (captured at initialize() time) so
        this is safe to call from any thread, including the drain worker thread.
        """
        try:
            import asyncio

            from python.helpers.llm_router import get_router

            loop = self._loop
            if loop is not None:
                loop.call_soon_threadsafe(  # type: ignore[union-attr]
                    lambda: asyncio.ensure_future(
                        get_router().discover_models(force=True),
                        loop=loop,  # type: ignore[arg-type]
                    )
                )
            else:
                log.debug("WorkModeManager: no event loop stored; skipping LLM router reload")
        except Exception as e:
            log.warning("WorkModeManager: LLM router reload error: %s", e)
