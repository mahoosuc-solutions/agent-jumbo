"""Graceful Shutdown — handles SIGTERM/SIGINT for clean process termination."""

import asyncio
import logging
import signal
import threading

logger = logging.getLogger(__name__)

_shutting_down = False
_shutdown_event = threading.Event()


def is_shutting_down() -> bool:
    """Check whether the process is in graceful shutdown."""
    return _shutting_down


def register_shutdown_handlers():
    """Register signal handlers for graceful shutdown."""

    def _handle_signal(signum, frame):
        global _shutting_down
        sig_name = signal.Signals(signum).name
        logger.info("Received %s — initiating graceful shutdown", sig_name)
        _shutting_down = True
        _shutdown_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    logger.info("Graceful shutdown handlers registered")


async def shutdown_async(timeout: int = 30):
    """Async shutdown tasks — drain queues, disconnect services.

    Should be awaited after ``_shutdown_event`` is set.  The routine:

    1. Stops the AgentMesh bridge (if imported / running).
    2. Flushes any dead-letter entries still in memory.
    3. Waits a short grace period for in-flight tasks.
    4. Logs completion.
    """
    logger.info("Running async shutdown tasks (timeout=%ds)", timeout)
    try:
        # 1. Stop AgentMesh bridge if running
        try:
            from python.helpers.agentmesh_bridge import AgentMeshBridge

            bridge = AgentMeshBridge.instance() if hasattr(AgentMeshBridge, "instance") else None
            if bridge is not None:
                logger.info("Stopping AgentMesh bridge...")
                await bridge.stop()
                await bridge.disconnect()
                logger.info("AgentMesh bridge stopped")
        except ImportError:
            logger.debug("AgentMesh bridge not available — skipping")
        except Exception as exc:
            logger.warning("AgentMesh bridge shutdown error: %s", exc)

        # 2. Flush dead-letter queue
        try:
            from python.helpers.message_queue import MessageQueue

            mq = MessageQueue.instance() if hasattr(MessageQueue, "instance") else None
            if mq is not None and hasattr(mq, "flush_dead_letters"):
                logger.info("Flushing dead-letter queue...")
                mq.flush_dead_letters()
                logger.info("Dead-letter queue flushed")
        except ImportError:
            logger.debug("MessageQueue not available — skipping dead-letter flush")
        except Exception as exc:
            logger.warning("Dead-letter flush error: %s", exc)

        # 3. Wait for in-flight tasks
        logger.info("Waiting for in-flight tasks to complete...")
        await asyncio.sleep(min(timeout, 5))  # Brief grace period

        logger.info("Graceful shutdown complete")
    except Exception as e:
        logger.exception("Error during async shutdown: %s", e)


def wait_for_shutdown(timeout: float | None = None) -> bool:
    """Block the current thread until a shutdown signal is received.

    Returns ``True`` if the event was set (shutdown requested), ``False`` on
    timeout.  Useful for background threads that need to sleep but should wake
    promptly on shutdown.
    """
    return _shutdown_event.wait(timeout=timeout)
