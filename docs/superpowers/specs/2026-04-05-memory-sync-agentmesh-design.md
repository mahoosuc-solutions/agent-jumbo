# Memory Sync via AgentMesh Bridge — Design Spec

**Date:** 2026-04-05
**Status:** Approved
**Author:** Aaron + Claude Opus 4.6

## Problem

Agent Mahoo runs locally and connects to MOS on Hetzner via AgentMesh Bridge (Redis Streams). Memory is stored as local FAISS indexes — MOS has no visibility into what the local agent knows. This creates a blind spot: C-suite personas and scheduled tasks on MOS can't reference email digests, knowledge captures, or operator context that only exists locally.

## Decision

**Option A: Local → Cloud (one-way sync via event bus)**

Local Agent Mahoo is the source of truth. When EXECUTIVE memory is written locally, a `memory.updated` event is emitted through the existing AgentMesh Bridge. MOS consumes these events to build awareness. No FAISS duplication on the cloud side — MOS gets the text and metadata via events.

## What Gets Synced

Only the **EXECUTIVE** memory area. This contains:

- Email digests (from `mos-email-digest` scheduled task)
- Financial snapshots (from CFO persona)
- Operations summaries (from COO persona)
- Knowledge captures marked as executive-level

MAIN, FRAGMENTS, SOLUTIONS, and INSTRUMENTS areas remain local-only.

## Mechanism

The `Memory` class already has an `on_save(doc_id, text, metadata)` callback that fires after every `insert_text()` call. The sync module registers this callback during boot, filters for EXECUTIVE area writes, and schedules an async emit to the AgentMesh Bridge.

The bridge runs in a separate thread with its own event loop (standard pattern in `run_ui.py`), so the callback uses `loop.call_soon_threadsafe()` to bridge the sync→async gap.

## Event Schema

```json
{
  "type": "memory.updated",
  "aggregateId": "<doc_id>",
  "producedBy": "agent-mahoo",
  "payload": {
    "doc_id": "<doc_id>",
    "text": "<truncated to 4000 chars>",
    "metadata": { "area": "executive", "source": "<source>" },
    "memory_subdir": "default"
  }
}
```

## Failure Model

Fire-and-forget. If the bridge is down, local writes succeed normally. No retry, no queue. Events accumulate in the Redis Stream (capped at 10,000 by AgentMesh config) until MOS picks them up.

## Non-Goals

- Bidirectional sync (MOS → local)
- Syncing non-EXECUTIVE areas
- Replacing FAISS with a shared database
- Real-time consistency guarantees
