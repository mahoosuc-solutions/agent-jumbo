# Memory Sync via AgentMesh Bridge — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When Agent Jumbo (local) writes to EXECUTIVE memory, emit a `memory.updated` event through AgentMesh Bridge so MOS (Hetzner) receives the knowledge without duplicating FAISS storage. Local is the source of truth; cloud reads via event bus.

**Architecture:** Memory writes go through the existing `on_save` callback on the `Memory` class. A new module (`memory_mesh_sync.py`) registers this callback when the AgentMesh bridge is connected. On each memory write, it emits a `memory.updated` event containing the document text, metadata, and memory subdir. MOS consumes these events to build its own awareness. The sync is fire-and-forget: if the bridge is down, local writes still succeed.

**Tech Stack:** Python, AgentMesh Bridge (Redis Streams), FAISS (local only), existing `Memory.on_save` callback

---

### Task 1: Create memory_mesh_sync module

**Files:**

- Create: `python/helpers/memory_mesh_sync.py`
- Test: `tests/test_memory_mesh_sync.py`

- [ ] **Step 1: Write the failing test — emit on memory save**

```python
"""Tests for memory_mesh_sync — AgentMesh event emission on memory writes."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_on_memory_saved_emits_event():
    """When on_memory_saved fires, it should emit memory.updated via bridge."""
    mock_bridge = MagicMock()
    mock_bridge.emit = AsyncMock(return_value="evt-123")

    mock_loop = MagicMock()
    future = asyncio.Future()
    future.set_result("evt-123")
    mock_loop.call_soon_threadsafe = MagicMock()

    from python.helpers.memory_mesh_sync import on_memory_saved

    with patch("python.helpers.memory_mesh_sync._bridge", mock_bridge):
        with patch("python.helpers.memory_mesh_sync._loop", mock_loop):
            on_memory_saved("doc-abc", "Hello world", {"area": "executive", "source": "email_digest"})

    # Verify call_soon_threadsafe was called (bridges the sync→async gap)
    assert mock_loop.call_soon_threadsafe.called


def test_on_memory_saved_skips_when_no_bridge():
    """When bridge is None, on_memory_saved should silently no-op."""
    from python.helpers.memory_mesh_sync import on_memory_saved

    with patch("python.helpers.memory_mesh_sync._bridge", None):
        # Should not raise
        on_memory_saved("doc-abc", "Hello world", {"area": "executive"})


def test_on_memory_saved_skips_non_executive():
    """Only EXECUTIVE area writes should emit events."""
    mock_bridge = MagicMock()
    mock_bridge.emit = AsyncMock()

    from python.helpers.memory_mesh_sync import on_memory_saved

    with patch("python.helpers.memory_mesh_sync._bridge", mock_bridge):
        with patch("python.helpers.memory_mesh_sync._loop", MagicMock()):
            on_memory_saved("doc-abc", "Hello", {"area": "main"})

    # Bridge emit should NOT have been scheduled for non-executive areas
    # (call_soon_threadsafe not called)


def test_register_sets_bridge_and_loop():
    """register_memory_sync should store bridge and loop references."""
    mock_bridge = MagicMock()
    mock_loop = MagicMock()

    from python.helpers.memory_mesh_sync import register_memory_sync

    register_memory_sync(mock_bridge, mock_loop)

    from python.helpers import memory_mesh_sync

    assert memory_mesh_sync._bridge is mock_bridge
    assert memory_mesh_sync._loop is mock_loop
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memory_mesh_sync.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'python.helpers.memory_mesh_sync'`

- [ ] **Step 3: Write the implementation**

```python
"""Memory → AgentMesh sync — emits memory.updated events on EXECUTIVE writes.

When Agent Jumbo writes to EXECUTIVE memory locally, this module emits a
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_memory_mesh_sync.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add python/helpers/memory_mesh_sync.py tests/test_memory_mesh_sync.py
git commit -m "feat: memory_mesh_sync — emit memory.updated events for EXECUTIVE writes"
```

---

### Task 2: Wire sync into Memory initialization

**Files:**

- Modify: `python/helpers/memory.py` (lines 86-108, the `get()` and `get_by_subdir()` methods)
- Test: `tests/test_memory_mesh_sync.py` (add integration test)

- [ ] **Step 1: Write the failing test — Memory gets on_save callback**

Add to `tests/test_memory_mesh_sync.py`:

```python
def test_attach_to_memory_sets_on_save():
    """attach_to_memory should set the on_save callback on a Memory instance."""
    mock_memory = MagicMock()
    mock_memory.on_save = None

    from python.helpers.memory_mesh_sync import attach_to_memory, on_memory_saved

    attach_to_memory(mock_memory)
    assert mock_memory.on_save is on_memory_saved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memory_mesh_sync.py::test_attach_to_memory_sets_on_save -v`
Expected: FAIL with `ImportError: cannot import name 'attach_to_memory'`

- [ ] **Step 3: Add attach_to_memory function**

Add to `python/helpers/memory_mesh_sync.py`:

```python
def attach_to_memory(memory_instance: Any) -> None:
    """Attach the mesh sync callback to a Memory instance.

    Called during Memory initialization when the bridge is active.
    Only attaches if register_memory_sync has been called.
    """
    if _bridge is not None:
        memory_instance.on_save = on_memory_saved
        logger.debug("Attached mesh sync to memory instance")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_memory_mesh_sync.py -v`
Expected: 5 passed

- [ ] **Step 5: Wire into Memory.get() and Memory.get_by_subdir()**

In `python/helpers/memory.py`, after creating the `Memory` wrapper in the `get()` static method (around line 98), add:

```python
# After: wrap = Memory(db, memory_subdir=memory_subdir)
try:
    from python.helpers.memory_mesh_sync import attach_to_memory
    attach_to_memory(wrap)
except ImportError:
    pass
```

Add the same block in `get_by_subdir()` after line 128:

```python
# After: wrap = Memory(db, memory_subdir=memory_subdir)
try:
    from python.helpers.memory_mesh_sync import attach_to_memory
    attach_to_memory(wrap)
except ImportError:
    pass
```

- [ ] **Step 6: Commit**

```bash
git add python/helpers/memory_mesh_sync.py python/helpers/memory.py tests/test_memory_mesh_sync.py
git commit -m "feat: wire memory mesh sync into Memory initialization"
```

---

### Task 3: Wire sync into AgentMesh boot sequence

**Files:**

- Modify: `run_ui.py` (lines 481-486, inside `_run()`)

- [ ] **Step 1: Write the failing test — register called at boot**

Add to `tests/test_memory_mesh_sync.py`:

```python
def test_register_called_from_boot_sequence():
    """run_ui.py should call register_memory_sync after bridge.connect()."""
    content = open("run_ui.py").read()
    assert "register_memory_sync" in content, (
        "run_ui.py must call register_memory_sync after bridge connects"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memory_mesh_sync.py::test_register_called_from_boot_sequence -v`
Expected: FAIL

- [ ] **Step 3: Modify run_ui.py boot sequence**

In `run_ui.py`, modify the `_run()` function (around line 481):

```python
async def _run():
    bridge = AgentMeshBridge(AgentMeshConfig(redis_url=agentmesh_url))
    await bridge.connect()
    set_bridge(bridge)
    register_task_handlers(bridge)

    # Wire memory → AgentMesh sync for EXECUTIVE writes
    try:
        from python.helpers.memory_mesh_sync import register_memory_sync
        register_memory_sync(bridge, asyncio.get_event_loop())
    except Exception as e:
        PrintStyle(font_color="yellow").print(f"[!] Memory mesh sync failed: {e}")

    try:
        await bridge.start()
    finally:
        await bridge.disconnect()
```

Also update the import line (around 479):

```python
from python.helpers.agentmesh_task_handler import register_task_handlers, set_bridge
```

(No change needed — `register_memory_sync` is imported inside the try block.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_memory_mesh_sync.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add run_ui.py tests/test_memory_mesh_sync.py
git commit -m "feat: wire memory mesh sync into AgentMesh boot sequence"
```

---

### Task 4: Add memory.updated event to AgentMesh handler registration

**Files:**

- Modify: `python/helpers/agentmesh_task_handler.py` (line 48-56, `register_task_handlers`)
- Test: `tests/test_memory_mesh_sync.py`

- [ ] **Step 1: Write the failing test — handler registered**

Add to `tests/test_memory_mesh_sync.py`:

```python
def test_agentmesh_registers_memory_event_handler():
    """register_task_handlers must register a memory.updated handler."""
    content = open("python/helpers/agentmesh_task_handler.py").read()
    assert "memory.updated" in content, (
        "agentmesh_task_handler.py should register a memory.updated handler"
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memory_mesh_sync.py::test_agentmesh_registers_memory_event_handler -v`
Expected: FAIL

- [ ] **Step 3: Add memory.updated handler registration**

In `python/helpers/agentmesh_task_handler.py`, add to `register_task_handlers()`:

```python
def register_task_handlers(bridge: AgentMeshBridge) -> None:
    """Register all AgentMesh task event handlers on the bridge."""
    bridge.on("task.assigned", _handle_task_assigned)
    bridge.on("task.approval_resolved", _handle_approval_resolved)
    # C-suite executive event handlers
    bridge.on("executive.financial_report", _handle_task_assigned)
    bridge.on("executive.ops_digest", _handle_task_assigned)
    bridge.on("executive.sales_update", _handle_task_assigned)
    bridge.on("executive.brand_review", _handle_task_assigned)
    # Memory sync acknowledgment (consumed by MOS on Hetzner)
    bridge.on("memory.updated", _handle_memory_updated)
```

Add the handler function:

```python
async def _handle_memory_updated(event: AgentMeshEvent) -> None:
    """Log memory sync events received from other mesh nodes.

    On the local instance this is a no-op (we produced the event).
    On MOS/Hetzner this is where the remote node would ingest the knowledge.
    """
    payload = event.payload
    doc_id = payload.get("doc_id", "?")
    area = payload.get("metadata", {}).get("area", "?")
    source = payload.get("metadata", {}).get("source", "?")
    logger.info(
        "memory.updated received: doc=%s area=%s source=%s (produced_by=%s)",
        doc_id, area, source, event.produced_by,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_memory_mesh_sync.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add python/helpers/agentmesh_task_handler.py tests/test_memory_mesh_sync.py
git commit -m "feat: register memory.updated handler in AgentMesh task handler"
```

---

### Task 5: Update series validation tests

**Files:**

- Modify: `tests/test_j_series_validation.py`
- Modify: `tests/test_i_series_validation.py`

- [ ] **Step 1: Add memory sync validation to J-series**

Add to `tests/test_j_series_validation.py` in the `TestAgentMeshComprehensive` class:

```python
def test_agentmesh_has_memory_updated_handler(self):
    """AgentMesh must register a memory.updated event handler."""
    src = (ROOT / "python" / "helpers" / "agentmesh_task_handler.py").read_text()
    assert "memory.updated" in src, "Missing memory.updated handler registration"
```

Add a new test class:

```python
class TestMemoryMeshSync:
    """Validate memory → AgentMesh sync module."""

    def test_memory_mesh_sync_importable(self):
        import python.helpers.memory_mesh_sync as mod
        assert hasattr(mod, "register_memory_sync")
        assert hasattr(mod, "on_memory_saved")
        assert hasattr(mod, "attach_to_memory")

    def test_sync_only_executive_area(self):
        from python.helpers.memory_mesh_sync import _SYNC_AREAS
        assert "executive" in _SYNC_AREAS
        assert "main" not in _SYNC_AREAS

    def test_boot_sequence_wires_sync(self):
        content = (ROOT / "run_ui.py").read_text()
        assert "register_memory_sync" in content
```

- [ ] **Step 2: Run the full series regression**

Run: `python -m pytest tests/test_j_series_validation.py -v --tb=short`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add tests/test_j_series_validation.py
git commit -m "test: add memory mesh sync validation to J-series"
```

---

### Task 6: Documentation

**Files:**

- Create: `docs/MEMORY_SYNC_ARCHITECTURE.md`

- [ ] **Step 1: Write the architecture doc**

```markdown
# Memory Sync Architecture — Local → Cloud via AgentMesh

## Overview

Agent Jumbo (local) is the source of truth for all memory. When EXECUTIVE
memory is written locally (email digests, knowledge captures, interaction
context), a `memory.updated` event is emitted through the AgentMesh Bridge
(Redis Streams) so MOS on Hetzner receives the knowledge without
duplicating FAISS storage.

## Data Flow

```

Local (Agent Jumbo)                          Cloud (MOS / Hetzner)
┌────────────────────┐                      ┌──────────────────────┐
│ Memory.insert_text()│                      │                      │
│        ↓           │                      │                      │
│ FAISS write (local)│                      │                      │
│        ↓           │                      │                      │
│ on_save callback   │   Redis Streams      │ memory.updated       │
│        ↓           │──────────────────────│ event handler        │
│ memory_mesh_sync   │   memory.updated     │        ↓             │
│ emit to bridge     │   event              │ Log / ingest /       │
│                    │                      │ build awareness      │
└────────────────────┘                      └──────────────────────┘

```

## What Gets Synced

- **EXECUTIVE area only** — email digests, financial snapshots, ops summaries
- **Not synced:** MAIN, FRAGMENTS, SOLUTIONS, INSTRUMENTS (local-only)

## Event Schema

```json
{
  "type": "memory.updated",
  "aggregateId": "doc-abc-123",
  "producedBy": "agent-jumbo",
  "payload": {
    "doc_id": "doc-abc-123",
    "text": "## Email Digest — 2026-04-05T12:00...",
    "metadata": {
      "area": "executive",
      "source": "email_digest",
      "total_emails": 15,
      "total_unread": 3
    },
    "memory_subdir": "default"
  }
}
```

## Failure Modes

| Scenario | Behavior |
|----------|----------|
| AgentMesh bridge disconnected | Local write succeeds, sync skipped silently |
| Redis unreachable | Same — fire-and-forget, no retry |
| MOS not consuming | Events accumulate in Redis Stream (capped at 10,000) |
| Large document | Text capped at 4,000 chars in payload |

## Configuration

No new environment variables. Sync activates automatically when
`AGENTMESH_REDIS_URL` is set and the bridge connects successfully.

## Files

| File | Purpose |
|------|---------|
| `python/helpers/memory_mesh_sync.py` | Sync module — callback + emit logic |
| `python/helpers/memory.py` | `on_save` callback attachment in `get()` / `get_by_subdir()` |
| `python/helpers/agentmesh_task_handler.py` | `memory.updated` event handler registration |
| `run_ui.py` | `register_memory_sync()` called at boot |

```

- [ ] **Step 2: Commit**

```bash
git add docs/MEMORY_SYNC_ARCHITECTURE.md
git commit -m "docs: memory sync architecture — local→cloud via AgentMesh"
```

---

### Task 7: Final integration test and push

- [ ] **Step 1: Run full regression**

```bash
python -m pytest tests/test_e_series_validation.py tests/test_f_series_validation.py \
  tests/test_g_series_validation.py tests/test_h_series_validation.py \
  tests/test_i_series_validation.py tests/test_j_series_validation.py \
  tests/test_k_series_validation.py tests/test_memory_mesh_sync.py \
  --tb=short -q
```

Expected: All pass (Docker tests may skip if daemon is down)

- [ ] **Step 2: Push**

```bash
git push origin main
```
