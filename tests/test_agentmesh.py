"""Tests for AgentMesh components — risk classifier, bridge, task handler."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from python.helpers.agentmesh_bridge import AgentMeshBridge, AgentMeshConfig, AgentMeshEvent
from python.helpers.agentmesh_risk import classify_risk

# ── Risk Classifier ──────────────────────────────────────────────────────


class TestClassifyRisk:
    """Test the risk classification logic."""

    def test_explicit_risk_level_takes_precedence(self):
        assert classify_risk({"riskLevel": "CRITICAL"}) == "CRITICAL"
        assert classify_risk({"riskLevel": "LOW", "category": "deployment"}) == "LOW"

    def test_invalid_explicit_risk_ignored(self):
        result = classify_risk({"riskLevel": "BANANA", "category": "general"})
        assert result == "LOW"

    def test_low_risk_categories(self):
        for cat in ("research", "content", "general", "code_review"):
            assert classify_risk({"category": cat}) == "LOW", f"{cat} should be LOW"

    def test_medium_risk_categories(self):
        assert classify_risk({"category": "security_scan"}) == "MEDIUM"
        assert classify_risk({"category": "workflow"}) == "MEDIUM"

    def test_deployment_risk_depends_on_target(self):
        assert classify_risk({"category": "deployment", "context": {"target": "staging"}}) == "MEDIUM"
        assert classify_risk({"category": "deployment", "context": {"target": "production"}}) == "HIGH"
        assert classify_risk({"category": "deployment", "context": {"environment": "prod-us-east"}}) == "HIGH"

    def test_architecture_is_high(self):
        assert classify_risk({"category": "architecture"}) == "HIGH"

    def test_unknown_category_defaults_medium(self):
        assert classify_risk({"category": "alien_invasion"}) == "MEDIUM"

    def test_keyword_escalation(self):
        assert classify_risk({"category": "general", "description": "delete all logs"}) == "MEDIUM"
        assert classify_risk({"category": "research", "description": "rollback the deploy"}) == "MEDIUM"
        assert (
            classify_risk({"category": "deployment", "description": "purge cache", "context": {"target": "prod"}})
            == "CRITICAL"
        )

    def test_critical_priority_escalates(self):
        assert classify_risk({"category": "general", "priority": "critical"}) == "MEDIUM"
        assert (
            classify_risk({"category": "deployment", "priority": "critical", "context": {"target": "staging"}})
            == "HIGH"
        )

    def test_double_escalation(self):
        result = classify_risk(
            {
                "category": "deployment",
                "priority": "critical",
                "description": "destroy the old cluster",
                "context": {"target": "prod"},
            }
        )
        assert result == "CRITICAL"

    def test_missing_fields_dont_crash(self):
        assert classify_risk({}) == "LOW"  # defaults to "general" category
        assert classify_risk({"category": None}) == "MEDIUM"  # None not in known categories


# ── AgentMeshEvent Serialization ─────────────────────────────────────────


class TestAgentMeshEvent:
    """Test event serialization/deserialization."""

    def test_round_trip(self):
        event = AgentMeshEvent(
            id="evt-1",
            type="task.assigned",
            aggregate_id="task-1",
            aggregate_type="task",
            produced_by="mahoosuc-os",
            timestamp="2026-03-21T00:00:00Z",
            version=1,
            payload={"title": "Test task"},
            metadata={"correlationId": "corr-1"},
        )
        json_data = event.to_json()
        restored = AgentMeshEvent.from_json(json_data)
        assert restored.id == event.id
        assert restored.type == event.type
        assert restored.aggregate_id == event.aggregate_id
        assert restored.payload == event.payload

    def test_camel_case_keys(self):
        event = AgentMeshEvent(
            id="1",
            type="t",
            aggregate_id="a",
            aggregate_type="at",
            produced_by="p",
            timestamp="ts",
            version=1,
            payload={},
        )
        data = event.to_json()
        assert "aggregateId" in data
        assert "producedBy" in data
        assert "aggregate_id" not in data

    def test_from_json_missing_optional_fields(self):
        data = {
            "id": "1",
            "type": "t",
            "aggregateId": "a",
            "aggregateType": "at",
            "producedBy": "p",
            "timestamp": "ts",
            "version": 1,
        }
        event = AgentMeshEvent.from_json(data)
        assert event.payload == {}
        assert event.metadata == {}


# ── Bridge Config ────────────────────────────────────────────────────────


class TestAgentMeshBridge:
    """Test bridge configuration and health."""

    def test_default_config(self):
        config = AgentMeshConfig()
        assert config.name == "agent-mahoo"
        assert config.redis_url == "redis://localhost:6379"

    def test_health_initial(self):
        bridge = AgentMeshBridge(AgentMeshConfig())
        health = bridge.health()
        assert health["connected"] is False
        assert health["running"] is False
        assert health["events_processed"] == 0
        assert health["last_error"] is None

    def test_handler_registration(self):
        bridge = AgentMeshBridge(AgentMeshConfig())
        handler = AsyncMock()
        bridge.on("task.assigned", handler)
        assert "task.assigned" in bridge._handlers
        assert handler in bridge._handlers["task.assigned"]

    def test_emit_without_connect_raises(self):
        bridge = AgentMeshBridge(AgentMeshConfig())
        with pytest.raises(RuntimeError, match="not connected"):
            import asyncio

            asyncio.get_event_loop().run_until_complete(bridge.emit("test", "id", {}))

    def test_idempotency_tracking(self):
        bridge = AgentMeshBridge(AgentMeshConfig())
        assert len(bridge._processed_task_ids) == 0
        bridge._processed_task_ids["task.assigned:task-1"] = True
        assert "task.assigned:task-1" in bridge._processed_task_ids


# ── Task Handler ─────────────────────────────────────────────────────────


class TestTaskHandler:
    """Test task handler logic."""

    def test_category_profile_mapping(self):
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        assert CATEGORY_PROFILE_MAP["deployment"] == "actor-ops"
        assert CATEGORY_PROFILE_MAP["security_scan"] == "hacker"
        assert CATEGORY_PROFILE_MAP["code_review"] == "developer"
        assert CATEGORY_PROFILE_MAP["general"] == "base"

    def test_mesh_context_factory_creates_task_type(self):
        """Verify _get_or_create_mesh_context creates a TASK-type context."""
        from python.helpers.agentmesh_task_handler import _get_or_create_mesh_context

        ctx = _get_or_create_mesh_context()
        from agent import AgentContext, AgentContextType

        assert ctx is not None
        assert ctx.id == "agentmesh-worker"
        assert ctx.type == AgentContextType.TASK
        assert ctx.name == "AgentMesh Worker"

        # Second call returns same context
        ctx2 = _get_or_create_mesh_context()
        assert ctx2 is ctx

        # Cleanup
        AgentContext.remove("agentmesh-worker")
