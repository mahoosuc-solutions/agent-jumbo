"""Tests for memory_mesh_sync — AgentMesh event emission on memory writes."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


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

    mock_loop = MagicMock()
    mock_loop.call_soon_threadsafe = MagicMock()

    from python.helpers.memory_mesh_sync import on_memory_saved

    with patch("python.helpers.memory_mesh_sync._bridge", mock_bridge):
        with patch("python.helpers.memory_mesh_sync._loop", mock_loop):
            on_memory_saved("doc-abc", "Hello", {"area": "main"})

    # Bridge emit should NOT have been scheduled for non-executive areas
    assert not mock_loop.call_soon_threadsafe.called


def test_register_sets_bridge_and_loop():
    """register_memory_sync should store bridge and loop references."""
    mock_bridge = MagicMock()
    mock_loop = MagicMock()

    from python.helpers.memory_mesh_sync import register_memory_sync

    register_memory_sync(mock_bridge, mock_loop)

    from python.helpers import memory_mesh_sync

    assert memory_mesh_sync._bridge is mock_bridge
    assert memory_mesh_sync._loop is mock_loop
