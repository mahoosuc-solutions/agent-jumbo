"""AgentMesh Redis Streams bridge for Agent Jumbo.

Connects Agent Jumbo to the AgentMesh event bus via a single Redis Stream
(``agentmesh:events``).  Each consumer uses a consumer group so that events
are delivered exactly once per system.

Usage::

    bridge = AgentMeshBridge(AgentMeshConfig(redis_url="redis://localhost:6379"))
    await bridge.connect()
    bridge.on("task.assigned", handle_task)
    await bridge.start()          # blocks until stop()
    await bridge.disconnect()
"""

from __future__ import annotations

import asyncio
import collections
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

STREAM_KEY = "agentmesh:events"
CONSUMER_GROUP_PREFIX = "agentmesh:cg"
BLOCK_TIMEOUT_MS = 5000
BATCH_SIZE = 10
STREAM_MAXLEN = 10000
MAX_BACKOFF_SECONDS = 60


@dataclass
class AgentMeshEvent:
    """Mirror of the TypeScript AgentMeshEvent interface."""

    id: str
    type: str
    aggregate_id: str
    aggregate_type: str
    produced_by: str
    timestamp: str
    version: int
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        """Serialize to the camelCase JSON shape expected by AgentMesh."""
        return {
            "id": self.id,
            "type": self.type,
            "aggregateId": self.aggregate_id,
            "aggregateType": self.aggregate_type,
            "producedBy": self.produced_by,
            "timestamp": self.timestamp,
            "version": self.version,
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> AgentMeshEvent:
        return cls(
            id=data["id"],
            type=data["type"],
            aggregate_id=data["aggregateId"],
            aggregate_type=data["aggregateType"],
            produced_by=data["producedBy"],
            timestamp=data["timestamp"],
            version=data["version"],
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentMeshConfig:
    name: str = "agent-jumbo"
    redis_url: str = "redis://localhost:6379"


EventHandlerFn = Callable[[AgentMeshEvent], Awaitable[None]]


class AgentMeshBridge:
    """Bridge between Agent Jumbo and AgentMesh via Redis Streams."""

    def __init__(self, config: AgentMeshConfig) -> None:
        self.config = config
        self._redis: aioredis.Redis | None = None
        self._handlers: dict[str, list[EventHandlerFn]] = {}
        self._running = False
        self._group_name = f"{CONSUMER_GROUP_PREFIX}:{config.name}"
        self._events_processed = 0
        self._last_error: str | None = None
        self._connected = False
        self._processed_task_ids: collections.OrderedDict[str, bool] = collections.OrderedDict()

    # -- Lifecycle -----------------------------------------------------------

    async def connect(self) -> None:
        self._redis = aioredis.from_url(self.config.redis_url, decode_responses=True)
        # Create consumer group (idempotent)
        try:
            await self._redis.xgroup_create(STREAM_KEY, self._group_name, id="0", mkstream=True)
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        self._connected = True
        self._last_error = None
        logger.info("AgentMesh bridge connected (group=%s)", self._group_name)

    async def _reconnect(self) -> None:
        """Close broken connection and re-establish."""
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass
            self._redis = None
        self._connected = False
        await self.connect()

    async def disconnect(self) -> None:
        self._running = False
        self._connected = False
        if self._redis:
            await self._redis.aclose()  # type: ignore[union-attr]
            self._redis = None

    # -- Health --------------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """Return health status for monitoring."""
        return {
            "connected": self._connected,
            "running": self._running,
            "events_processed": self._events_processed,
            "last_error": self._last_error,
        }

    # -- Subscribe -----------------------------------------------------------

    def on(self, event_type: str, handler: EventHandlerFn) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    # -- Emit ----------------------------------------------------------------

    async def emit(
        self,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> str:
        if not self._redis:
            raise RuntimeError("AgentMesh bridge not connected — call connect() first")
        event = AgentMeshEvent(
            id=str(uuid4()),
            type=event_type,
            aggregate_id=aggregate_id,
            aggregate_type=event_type.split(".")[0] if "." in event_type else event_type,
            produced_by=self.config.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            version=1,
            payload=payload,
            metadata={"correlationId": correlation_id or str(uuid4())},
        )
        await self._redis.xadd(
            STREAM_KEY,
            {"data": json.dumps(event.to_json())},
            maxlen=STREAM_MAXLEN,
            approximate=True,
        )
        logger.debug("Emitted %s (id=%s)", event_type, event.id)
        return event.id

    # -- Poll loop -----------------------------------------------------------

    async def _process_message(self, msg_id: str, fields: dict[str, Any]) -> None:
        """Parse, filter, dispatch, and ACK a single stream message."""
        if not self._redis:
            return

        raw = fields.get("data")
        if not raw:
            await self._redis.xack(STREAM_KEY, self._group_name, msg_id)
            return

        try:
            data = json.loads(raw)
            event = AgentMeshEvent.from_json(data)
        except (json.JSONDecodeError, KeyError):
            logger.warning("Malformed event, skipping %s", msg_id)
            await self._redis.xack(STREAM_KEY, self._group_name, msg_id)
            return

        # Skip self-produced events
        if event.produced_by == self.config.name:
            await self._redis.xack(STREAM_KEY, self._group_name, msg_id)
            return

        # Idempotency: skip already-processed task IDs
        task_id = event.payload.get("taskId", event.aggregate_id)
        dedup_key = f"{event.type}:{task_id}"
        if dedup_key in self._processed_task_ids:
            logger.info("Skipping duplicate event %s", dedup_key)
            await self._redis.xack(STREAM_KEY, self._group_name, msg_id)
            return

        await self._dispatch(event)
        self._processed_task_ids[dedup_key] = True
        self._events_processed += 1
        await self._redis.xack(STREAM_KEY, self._group_name, msg_id)

        # Cap dedup set size — FIFO eviction of oldest half
        if len(self._processed_task_ids) > 5000:
            to_remove = len(self._processed_task_ids) // 2
            for _ in range(to_remove):
                self._processed_task_ids.popitem(last=False)

    async def _reclaim_pending(self) -> None:
        """Drain pending entries (claimed but not ACK'd) from a previous crash."""
        if not self._redis:
            return
        last_id = "0"
        while self._running:
            results = await self._redis.xreadgroup(
                groupname=self._group_name,
                consumername=self.config.name,
                streams={STREAM_KEY: last_id},
                count=BATCH_SIZE,
            )
            if not results:
                break
            _stream, messages = results[0]
            if not messages:
                break
            for msg_id, fields in messages:
                last_id = msg_id
                await self._process_message(msg_id, fields)
        logger.info("Pending reclaim complete")

    async def start(self) -> None:
        """Start consuming events.  Blocks until ``stop()`` is called."""
        if not self._redis:
            raise RuntimeError("AgentMesh bridge not connected — call connect() first")
        self._running = True
        consecutive_errors = 0
        logger.info("AgentMesh bridge listening for events")

        await self._reclaim_pending()

        while self._running:
            try:
                results = await self._redis.xreadgroup(
                    groupname=self._group_name,
                    consumername=self.config.name,
                    streams={STREAM_KEY: ">"},
                    count=BATCH_SIZE,
                    block=BLOCK_TIMEOUT_MS,
                )
                consecutive_errors = 0  # Reset on successful poll

                if not results:
                    continue

                for _stream, messages in results:
                    for msg_id, fields in messages:
                        await self._process_message(msg_id, fields)

            except asyncio.CancelledError:
                break
            except (ConnectionError, OSError, aioredis.ConnectionError) as exc:
                consecutive_errors += 1
                self._connected = False
                self._last_error = str(exc)
                backoff = min(2**consecutive_errors, MAX_BACKOFF_SECONDS)
                logger.warning(
                    "AgentMesh Redis connection lost (attempt %d), reconnecting in %ds: %s",
                    consecutive_errors,
                    backoff,
                    exc,
                )
                if self._running:
                    await asyncio.sleep(backoff)
                    try:
                        await self._reconnect()
                    except Exception as reconn_exc:
                        self._last_error = f"Reconnect failed: {reconn_exc}"
                        logger.error("AgentMesh reconnect failed: %s", reconn_exc)
            except Exception:
                consecutive_errors += 1
                self._last_error = "Unexpected error in poll loop"
                backoff = min(2**consecutive_errors, MAX_BACKOFF_SECONDS)
                logger.exception("Error in AgentMesh poll loop (backoff %ds)", backoff)
                if self._running:
                    await asyncio.sleep(backoff)

    def stop(self) -> None:
        self._running = False

    # -- Internal ------------------------------------------------------------

    async def _dispatch(self, event: AgentMeshEvent) -> None:
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception("Handler error for %s (id=%s)", event.type, event.id)
