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

    # -- Lifecycle -----------------------------------------------------------

    async def connect(self) -> None:
        self._redis = aioredis.from_url(self.config.redis_url, decode_responses=True)
        # Create consumer group (idempotent)
        try:
            await self._redis.xgroup_create(STREAM_KEY, self._group_name, id="0", mkstream=True)
        except aioredis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise
        logger.info("AgentMesh bridge connected (group=%s)", self._group_name)

    async def disconnect(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()  # type: ignore[union-attr]
            self._redis = None

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
        assert self._redis, "Call connect() first"
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
        await self._redis.xadd(STREAM_KEY, {"data": json.dumps(event.to_json())})
        logger.debug("Emitted %s (id=%s)", event_type, event.id)
        return event.id

    # -- Poll loop -----------------------------------------------------------

    async def start(self) -> None:
        """Start consuming events.  Blocks until ``stop()`` is called."""
        assert self._redis, "Call connect() first"
        self._running = True
        logger.info("AgentMesh bridge listening for events")
        while self._running:
            try:
                results = await self._redis.xreadgroup(
                    groupname=self._group_name,
                    consumername=self.config.name,
                    streams={STREAM_KEY: ">"},
                    count=BATCH_SIZE,
                    block=BLOCK_TIMEOUT_MS,
                )
                if not results:
                    continue

                for _stream, messages in results:
                    for msg_id, fields in messages:
                        raw = fields.get("data")
                        if not raw:
                            await self._redis.xack(STREAM_KEY, self._group_name, msg_id)
                            continue

                        try:
                            data = json.loads(raw)
                            event = AgentMeshEvent.from_json(data)
                        except (json.JSONDecodeError, KeyError):
                            logger.warning("Malformed event, skipping %s", msg_id)
                            await self._redis.xack(STREAM_KEY, self._group_name, msg_id)
                            continue

                        # Skip self-produced events
                        if event.produced_by == self.config.name:
                            await self._redis.xack(STREAM_KEY, self._group_name, msg_id)
                            continue

                        await self._dispatch(event)
                        await self._redis.xack(STREAM_KEY, self._group_name, msg_id)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in AgentMesh poll loop")
                if self._running:
                    await asyncio.sleep(1)

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
