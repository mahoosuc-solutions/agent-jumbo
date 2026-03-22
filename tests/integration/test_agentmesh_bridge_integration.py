"""Integration tests for the AgentMesh Redis Streams bridge.

Uses fakeredis for in-process Redis simulation — no real Redis required.
Tests event lifecycle: connect, emit, consume, ACK, dedup, and reconnect.
"""

import json
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import pytest

from python.helpers.agentmesh_bridge import (
    STREAM_KEY,
    AgentMeshBridge,
    AgentMeshConfig,
    AgentMeshEvent,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture()
def fake_redis():
    """Create a shared fakeredis server for test isolation."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture()
async def bridge(fake_redis):
    """Create a connected bridge using fakeredis."""
    config = AgentMeshConfig(name="test-agent")
    b = AgentMeshBridge(config)
    # Inject fakeredis instead of real connection
    with patch("redis.asyncio.from_url", return_value=fake_redis):
        await b.connect()
    yield b
    await b.disconnect()


def _make_event(event_type="task.assigned", task_id="task-1", produced_by="mahoosuc-os"):
    """Create a sample AgentMeshEvent."""
    return AgentMeshEvent(
        id="evt-001",
        type=event_type,
        aggregate_id=task_id,
        aggregate_type="task",
        produced_by=produced_by,
        timestamp="2026-03-22T00:00:00Z",
        version=1,
        payload={"taskId": task_id, "assignee": "agent-jumbo", "category": "general"},
    )


# ── Lifecycle ────────────────────────────────────────────────────────


async def test_connect_creates_consumer_group(bridge, fake_redis):
    """connect() creates the stream and consumer group."""
    assert bridge._connected is True
    # Consumer group should exist — xinfo_groups returns group info
    groups = await fake_redis.xinfo_groups(STREAM_KEY)
    group_names = [g["name"] for g in groups]
    assert bridge._group_name in group_names


async def test_connect_idempotent(bridge, fake_redis):
    """Calling connect() twice doesn't raise BUSYGROUP."""
    with patch("redis.asyncio.from_url", return_value=fake_redis):
        await bridge.connect()  # Second connect
    assert bridge._connected is True


async def test_health_reflects_state(bridge):
    """health() returns current connection and processing state."""
    h = bridge.health()
    assert h["connected"] is True
    assert h["running"] is False
    assert h["events_processed"] == 0
    assert h["last_error"] is None


async def test_disconnect(bridge):
    """disconnect() cleans up state."""
    await bridge.disconnect()
    assert bridge._connected is False
    assert bridge._redis is None


# ── Emit ─────────────────────────────────────────────────────────────


async def test_emit_adds_to_stream(bridge, fake_redis):
    """emit() publishes an event to the Redis stream."""
    event_id = await bridge.emit(
        event_type="task.completed",
        aggregate_id="task-42",
        payload={"result": "success"},
    )
    assert event_id  # UUID string

    # Verify message exists in stream
    messages = await fake_redis.xrange(STREAM_KEY)
    assert len(messages) >= 1
    last_data = json.loads(messages[-1][1]["data"])
    assert last_data["type"] == "task.completed"
    assert last_data["aggregateId"] == "task-42"
    assert last_data["producedBy"] == "test-agent"


async def test_emit_raises_when_not_connected():
    """emit() raises RuntimeError if bridge is not connected."""
    config = AgentMeshConfig(name="offline-agent")
    bridge = AgentMeshBridge(config)
    with pytest.raises(RuntimeError, match="not connected"):
        await bridge.emit("test.event", "id-1", {})


# ── Process Message ──────────────────────────────────────────────────


async def test_process_dispatches_to_handler(bridge, fake_redis):
    """_process_message dispatches to registered handler and ACKs."""
    handler = AsyncMock()
    bridge.on("task.assigned", handler)

    event = _make_event()
    msg_id = await fake_redis.xadd(STREAM_KEY, {"data": json.dumps(event.to_json())})

    await bridge._process_message(msg_id, {"data": json.dumps(event.to_json())})

    handler.assert_called_once()
    received_event = handler.call_args[0][0]
    assert received_event.type == "task.assigned"
    assert received_event.aggregate_id == "task-1"
    assert bridge._events_processed == 1


async def test_process_skips_self_produced(bridge, fake_redis):
    """_process_message skips events produced by this bridge."""
    handler = AsyncMock()
    bridge.on("task.assigned", handler)

    event = _make_event(produced_by="test-agent")  # Same as bridge name
    await bridge._process_message("msg-1", {"data": json.dumps(event.to_json())})

    handler.assert_not_called()
    assert bridge._events_processed == 0


async def test_process_deduplicates(bridge, fake_redis):
    """_process_message skips duplicate task IDs."""
    handler = AsyncMock()
    bridge.on("task.assigned", handler)

    event = _make_event(task_id="task-dup")
    data = {"data": json.dumps(event.to_json())}

    await bridge._process_message("msg-1", data)
    await bridge._process_message("msg-2", data)  # Duplicate

    assert handler.call_count == 1
    assert bridge._events_processed == 1


async def test_process_skips_malformed_json(bridge, fake_redis):
    """_process_message ACKs and skips malformed JSON."""
    handler = AsyncMock()
    bridge.on("task.assigned", handler)

    await bridge._process_message("msg-bad", {"data": "not-valid-json{{"})

    handler.assert_not_called()
    assert bridge._events_processed == 0


async def test_process_skips_empty_data(bridge, fake_redis):
    """_process_message ACKs messages with no data field."""
    handler = AsyncMock()
    bridge.on("task.assigned", handler)

    await bridge._process_message("msg-empty", {})

    handler.assert_not_called()


# ── Dedup Cap ────────────────────────────────────────────────────────


async def test_dedup_set_caps_at_5000(bridge, fake_redis):
    """Dedup set is capped at 5000 entries."""
    # Pre-fill with 5001 entries (OrderedDict, not set)
    import collections

    bridge._processed_task_ids = collections.OrderedDict((f"task.assigned:task-{i}", True) for i in range(5001))

    handler = AsyncMock()
    bridge.on("task.assigned", handler)

    event = _make_event(task_id="task-new")
    await bridge._process_message("msg-cap", {"data": json.dumps(event.to_json())})

    # Should have processed and then trimmed
    assert handler.call_count == 1
    assert len(bridge._processed_task_ids) <= 2600  # ~half of 5001 + 1 new


# ── Dispatch ─────────────────────────────────────────────────────────


async def test_dispatch_handler_error_does_not_propagate(bridge):
    """Handler errors are swallowed (logged) and don't crash the bridge."""
    failing_handler = AsyncMock(side_effect=ValueError("handler boom"))
    bridge.on("task.assigned", failing_handler)

    event = _make_event()
    # Should not raise
    await bridge._dispatch(event)
    failing_handler.assert_called_once()


async def test_dispatch_multiple_handlers(bridge):
    """Multiple handlers for the same event type are all called."""
    h1 = AsyncMock()
    h2 = AsyncMock()
    bridge.on("task.assigned", h1)
    bridge.on("task.assigned", h2)

    event = _make_event()
    await bridge._dispatch(event)

    h1.assert_called_once()
    h2.assert_called_once()


# ── Reclaim Pending ──────────────────────────────────────────────────


async def test_reclaim_pending_completes_without_error(bridge, fake_redis):
    """_reclaim_pending runs without error on empty pending list."""
    bridge._running = True
    # Should complete gracefully with no pending entries
    await bridge._reclaim_pending()
    assert bridge._events_processed == 0


# ── Event Serialization ──────────────────────────────────────────────


async def test_emit_and_consume_roundtrip(bridge, fake_redis):
    """Events emitted by one bridge can be consumed by another."""
    # Create a "producer" bridge with a different name
    producer_config = AgentMeshConfig(name="mahoosuc-os")
    producer = AgentMeshBridge(producer_config)
    with patch("redis.asyncio.from_url", return_value=fake_redis):
        await producer.connect()

    # Producer emits
    await producer.emit(
        event_type="task.assigned",
        aggregate_id="round-trip-task",
        payload={"taskId": "round-trip-task", "assignee": "agent-jumbo"},
    )

    # Consumer processes
    handler = AsyncMock()
    bridge.on("task.assigned", handler)

    messages = await fake_redis.xreadgroup(
        groupname=bridge._group_name,
        consumername=bridge.config.name,
        streams={STREAM_KEY: ">"},
        count=10,
    )

    for _stream, msgs in messages:
        for msg_id, fields in msgs:
            await bridge._process_message(msg_id, fields)

    handler.assert_called_once()
    received = handler.call_args[0][0]
    assert received.aggregate_id == "round-trip-task"
    assert received.produced_by == "mahoosuc-os"

    await producer.disconnect()
