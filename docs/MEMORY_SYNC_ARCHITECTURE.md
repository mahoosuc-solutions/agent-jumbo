# Memory Sync Architecture — Local → Cloud via AgentMesh

## Overview

Agent Jumbo (local) is the source of truth for all memory. When EXECUTIVE memory is written locally (email digests, knowledge captures, interaction context), a `memory.updated` event is emitted through the AgentMesh Bridge (Redis Streams) so MOS on Hetzner receives the knowledge without duplicating FAISS storage.

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

## Security

The AgentMesh Bridge connects via Redis Streams. For production deployments:

- **TLS**: Set `AGENTMESH_REDIS_URL=rediss://...` (note the double `s`) to enable TLS encryption in transit
- **Authentication**: Redis AUTH is supported via the URL format `rediss://:<password>@host:port`
- **Network**: The Hetzner ↔ local connection should use a VPN or SSH tunnel if Redis is not TLS-enabled
- **Payload size**: Memory text is capped at 4,000 chars to prevent oversized events

## Configuration

No new environment variables. Sync activates automatically when `AGENTMESH_REDIS_URL` is set and the bridge connects successfully.

To enable TLS, change the Redis URL scheme from `redis://` to `rediss://`.

## Files

| File | Purpose |
|------|---------|
| `python/helpers/memory_mesh_sync.py` | Sync module — callback + emit logic |
| `python/helpers/memory.py` | `on_save` callback attachment in `get()` / `get_by_subdir()` |
| `python/helpers/agentmesh_task_handler.py` | `memory.updated` event handler registration |
| `run_ui.py` | `register_memory_sync()` called at boot |
