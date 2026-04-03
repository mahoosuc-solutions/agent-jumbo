# python/helpers/work_mode/drain.py
from __future__ import annotations

import logging
import threading
import time

log = logging.getLogger(__name__)

_POLL_INTERVAL = 0.1  # seconds between in-flight checks


class DrainCoordinator:
    """Waits for all in-flight AgentContext instances to complete.

    Uses AgentContext.all() to determine when the system is quiescent.
    New tasks should check is_draining() and defer or reject spawn during drain.
    """

    def __init__(self) -> None:
        self._draining = False
        self._lock = threading.Lock()

    def is_draining(self) -> bool:
        return self._draining

    def drain(self, timeout: float = 60.0) -> bool:
        """Block until all in-flight AgentContexts complete or timeout.

        Returns True if clean drain, False if timeout was hit.
        Logs a warning for each context that did not complete in time.
        """
        with self._lock:
            self._draining = True

        deadline = time.monotonic() + timeout
        try:
            while time.monotonic() < deadline:
                from agent import AgentContext

                active = AgentContext.all()
                if not active:
                    log.info("DrainCoordinator: clean drain complete")
                    return True
                time.sleep(_POLL_INTERVAL)

            # Timeout: log offenders
            from agent import AgentContext

            remaining = AgentContext.all()
            for ctx in remaining:
                ctx_id = getattr(ctx, "id", repr(ctx))
                log.warning(
                    "DrainCoordinator: task %s did not complete within drain window "
                    "(%.1fs). Consider adding DrainCoordinator support.",
                    ctx_id,
                    timeout,
                )
            return False
        finally:
            with self._lock:
                self._draining = False
