"""Memory → AgentMesh sync — emits memory.updated events on EXECUTIVE writes.

When Agent Mahoo writes to EXECUTIVE memory locally, this module emits a
structured event via the AgentMesh Bridge so MOS on Hetzner receives the
knowledge without needing a separate FAISS index.

The sync is fire-and-forget: if the bridge is disconnected, local writes
still succeed. Only EXECUTIVE area writes are synced — MAIN, FRAGMENTS,
SOLUTIONS, and INSTRUMENTS stay local-only.

Usage:
    Called from run_ui.py after the AgentMesh bridge is connected:
        register_memory_sync(bridge, loop)

    Registered as Memory.on_save callback:
        memory_instance.on_save = on_memory_saved
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger("memory.mesh_sync")

_bridge: Any | None = None
_loop: asyncio.AbstractEventLoop | None = None

# Only sync these memory areas to the mesh
_SYNC_AREAS = {"executive"}


def register_memory_sync(bridge: Any, loop: asyncio.AbstractEventLoop) -> None:
    """Store bridge and event loop references for cross-thread emission."""
    global _bridge, _loop
    _bridge = bridge
    _loop = loop
    logger.info("Memory mesh sync registered")


def on_memory_saved(doc_id: str, text: str, metadata: dict[str, Any]) -> None:
    """Callback for Memory.on_save — emits memory.updated if EXECUTIVE area.

    This runs in the main Flask thread, so we schedule the async emit
    onto the AgentMesh event loop via call_soon_threadsafe.
    """
    if _bridge is None or _loop is None:
        return

    area = metadata.get("area", "main")
    if area not in _SYNC_AREAS:
        return

    payload = {
        "doc_id": doc_id,
        "text": text[:4000],  # cap payload size for Redis
        "metadata": {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))},
        "memory_subdir": metadata.get("memory_subdir", "default"),
    }

    def _schedule():
        asyncio.ensure_future(
            _bridge.emit(
                event_type="memory.updated",
                aggregate_id=doc_id,
                payload=payload,
            ),
            loop=_loop,
        )

    try:
        _loop.call_soon_threadsafe(_schedule)
        logger.debug("Scheduled memory.updated emission for doc %s", doc_id)
    except RuntimeError:
        # Loop is closed or not running — skip silently
        logger.debug("Event loop not running, skipping memory sync for doc %s", doc_id)


def attach_to_memory(memory_instance: Any) -> None:
    """Attach the mesh sync callback to a Memory instance.

    Called during Memory initialization when the bridge is active.
    Only attaches if register_memory_sync has been called.
    """
    if _bridge is not None:
        memory_instance.on_save = on_memory_saved
        logger.debug("Attached mesh sync to memory instance")
