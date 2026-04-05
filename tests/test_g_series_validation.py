"""
G-series validation tests.

G1: Docker smoke — container config, health endpoint, scheduler boot
G2: Playwright async migration — fixture infra + sync compatibility
G3: E2E retry wiring — tag API actions, tolerant helpers
G4: Memory consolidation scheduled task + stats API
G5: AgentMesh C-suite integration — event routing with fakeredis patterns
G6: Content calendar sidebar — nav button, store wiring
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ── G1: Docker Smoke Test ─────────────────────────────────────────────────


class TestDockerSmoke:
    """Structural verification of Docker + scheduler boot readiness."""

    def test_docker_compose_healthcheck_endpoint(self):
        content = (ROOT / "docker-compose.yml").read_text()
        assert "curl" in content and "/health" in content

    def test_docker_compose_start_period(self):
        content = (ROOT / "docker-compose.yml").read_text()
        assert "start_period" in content

    def test_run_ui_entrypoint_exists(self):
        assert (ROOT / "run_ui.py").exists()

    def test_scheduler_boot_registers_5_tasks(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        assert len(_MOS_TASKS) == 5
        names = [t["name"] for t in _MOS_TASKS]
        assert "mos-memory-consolidation" in names

    def test_memory_consolidation_is_weekly_sunday_3am(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        task = next(t for t in _MOS_TASKS if t["name"] == "mos-memory-consolidation")
        assert task["schedule"]["weekday"] == "0"  # Sunday
        assert task["schedule"]["hour"] == "3"
        assert task["schedule"]["minute"] == "0"

    def test_health_endpoint_exists(self):
        """health.py API handler must exist."""
        assert (ROOT / "python" / "api" / "health.py").exists() or (
            ROOT / "python" / "api" / "health_agentmesh.py"
        ).exists()

    def test_env_file_template_exists(self):
        """Either .env.example or .env should exist for Docker."""
        assert (ROOT / ".env").exists() or (ROOT / ".env.example").exists()


# ── G2: Playwright Async Migration ────────────────────────────────────────


class TestPlaywrightMigrationReadiness:
    """Verify async infra is ready and sync tests still work."""

    def test_async_conftest_has_fixtures(self):
        content = (ROOT / "tests" / "ui" / "conftest_async.py").read_text()
        assert "async_browser" in content
        assert "async_page" in content
        assert "async_playwright" in content

    def test_sync_conftest_unchanged(self):
        content = (ROOT / "tests" / "ui" / "conftest.py").read_text()
        assert "import sync_playwright" not in content  # conftest doesn't import sync_playwright
        assert "pytest_collection_modifyitems" in content

    def test_all_sync_test_files_exist(self):
        for name in ("test_observability_fixture.py", "test_observability_ui.py", "test_workflow_ui.py"):
            assert (ROOT / "tests" / "ui" / name).exists(), f"Missing {name}"

    def test_async_conftest_has_server_fixture(self):
        content = (ROOT / "tests" / "ui" / "conftest_async.py").read_text()
        assert "ui_server" in content


# ── G3: E2E Retry Wiring + Tag API ───────────────────────────────────────


class TestTagAPIActions:
    """Verify work_queue_item_update.py supports tag operations."""

    def test_add_tag_action_in_api(self):
        content = (ROOT / "python" / "api" / "work_queue_item_update.py").read_text()
        assert "add_tag" in content

    def test_set_tags_action_in_api(self):
        content = (ROOT / "python" / "api" / "work_queue_item_update.py").read_text()
        assert "set_tags" in content

    def test_by_tag_action_in_dashboard(self):
        content = (ROOT / "python" / "api" / "work_queue_dashboard.py").read_text()
        assert "by_tag" in content

    def test_update_action_accepts_tags(self):
        content = (ROOT / "python" / "api" / "work_queue_item_update.py").read_text()
        assert '"tags"' in content

    def test_with_retry_decorator_available(self):
        from tests.e2e.helpers import with_retry

        assert callable(with_retry)

    def test_api_get_tolerant_available(self):
        from tests.e2e.helpers import api_get_tolerant

        assert callable(api_get_tolerant)

    def test_api_post_tolerant_available(self):
        from tests.e2e.helpers import api_post_tolerant

        assert callable(api_post_tolerant)


# ── G4: Memory Consolidation Task + Stats API ────────────────────────────


class TestMemoryConsolidationTask:
    """Verify memory consolidation scheduled task and stats API."""

    def test_consolidation_task_in_mos_init(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        names = [t["name"] for t in _MOS_TASKS]
        assert "mos-memory-consolidation" in names

    def test_consolidation_prompt_mentions_executive(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        task = next(t for t in _MOS_TASKS if t["name"] == "mos-memory-consolidation")
        assert "executive" in task["prompt"].lower()
        assert "consolidation" in task["prompt"].lower()

    def test_memory_stats_api_exists(self):
        assert (ROOT / "python" / "api" / "memory_stats.py").exists()

    def test_memory_stats_api_importable(self):
        from python.api.memory_stats import MemoryStats

        assert hasattr(MemoryStats, "process")

    @pytest.mark.asyncio
    async def test_memory_stats_list_subdirs(self):
        from python.api.memory_stats import MemoryStats

        handler = MemoryStats.__new__(MemoryStats)
        with patch("python.helpers.memory.get_existing_memory_subdirs", return_value=["default", "projects/test"]):
            result = await handler.process({"action": "list_subdirs"}, request=None)
        assert result["success"] is True
        assert "default" in result["subdirs"]

    @pytest.mark.asyncio
    async def test_memory_stats_unloaded_subdir(self):
        from python.api.memory_stats import MemoryStats

        handler = MemoryStats.__new__(MemoryStats)
        with patch.dict("python.helpers.memory.Memory.index", {}, clear=True):
            result = await handler.process({"action": "stats", "memory_subdir": "default"}, request=None)
        assert result["success"] is True
        assert result["stats"]["loaded"] is False
        assert result["stats"]["total_documents"] == 0

    @pytest.mark.asyncio
    async def test_memory_stats_with_loaded_db(self):
        from langchain_core.documents import Document

        from python.api.memory_stats import MemoryStats

        mock_db = MagicMock()
        mock_db.get_all_docs.return_value = {
            "d1": Document("test", metadata={"area": "executive", "timestamp": "2025-06-01 10:00:00"}),
        }

        handler = MemoryStats.__new__(MemoryStats)
        with patch.dict("python.helpers.memory.Memory.index", {"default": mock_db}):
            result = await handler.process({"action": "stats", "memory_subdir": "default"}, request=None)
        assert result["success"] is True
        assert result["stats"]["total_documents"] == 1
        assert result["stats"]["loaded"] is True

    @pytest.mark.asyncio
    async def test_consolidate_dry_run_via_api(self):
        from python.api.memory_stats import MemoryStats

        mock_db = MagicMock()
        mock_db.get_all_docs.return_value = {}

        handler = MemoryStats.__new__(MemoryStats)
        with patch.dict("python.helpers.memory.Memory.index", {"default": mock_db}):
            result = await handler.process(
                {"action": "consolidate", "memory_subdir": "default", "dry_run": True},
                request=None,
            )
        assert result["success"] is True
        assert result["removed"] == 0


# ── G5: AgentMesh C-Suite Integration ─────────────────────────────────────


class TestAgentMeshCSuiteRouting:
    """Verify C-suite event routing end-to-end."""

    def test_category_map_routes_financial(self):
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        assert CATEGORY_PROFILE_MAP["financial_report"] == "cfo"
        assert CATEGORY_PROFILE_MAP["revenue_analysis"] == "cfo"

    def test_category_map_routes_ops(self):
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        assert CATEGORY_PROFILE_MAP["ops_digest"] == "coo"
        assert CATEGORY_PROFILE_MAP["sla_enforcement"] == "coo"
        assert CATEGORY_PROFILE_MAP["devops"] == "coo"

    def test_category_map_routes_sales(self):
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        assert CATEGORY_PROFILE_MAP["sales_pipeline"] == "cso"
        assert CATEGORY_PROFILE_MAP["proposal_generation"] == "cso"

    def test_category_map_routes_marketing(self):
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        assert CATEGORY_PROFILE_MAP["brand_review"] == "cmo"
        assert CATEGORY_PROFILE_MAP["content_calendar"] == "cmo"
        assert CATEGORY_PROFILE_MAP["marketing"] == "cmo"

    def test_executive_events_registered(self):
        from python.helpers.agentmesh_task_handler import register_task_handlers

        bridge = MagicMock()
        register_task_handlers(bridge)

        events = [call.args[0] for call in bridge.on.call_args_list]
        expected = [
            "task.assigned",
            "task.approval_resolved",
            "executive.financial_report",
            "executive.ops_digest",
            "executive.sales_update",
            "executive.brand_review",
        ]
        for ev in expected:
            assert ev in events, f"Missing handler for {ev}"

    @pytest.mark.asyncio
    async def test_task_assigned_ignores_non_agent_jumbo(self):
        """Events not assigned to agent-jumbo should be silently ignored."""
        from python.helpers.agentmesh_task_handler import _handle_task_assigned

        event = MagicMock()
        event.payload = {"taskId": "t1", "assignee": "other-agent", "category": "financial_report"}
        event.metadata = {}

        # Should not raise — just returns silently
        await _handle_task_assigned(event)

    @pytest.mark.asyncio
    async def test_high_risk_task_requires_approval(self):
        """HIGH risk tasks should emit approval_required, not execute."""
        from python.helpers.agentmesh_task_handler import _handle_task_assigned

        event = MagicMock()
        event.payload = {
            "taskId": "t1",
            "assignee": "agent-jumbo",
            "category": "financial_report",
        }
        event.aggregate_id = "t1"
        event.metadata = {"correlationId": "c1"}

        mock_bridge = AsyncMock()
        with (
            patch("python.helpers.agentmesh_task_handler.classify_risk", return_value="HIGH"),
            patch("python.helpers.agentmesh_task_handler._get_bridge", return_value=mock_bridge),
        ):
            await _handle_task_assigned(event)

        mock_bridge.emit.assert_called_once()
        call_kwargs = mock_bridge.emit.call_args
        assert (
            call_kwargs.kwargs.get("event_type") == "task.approval_required"
            or call_kwargs[1].get("event_type") == "task.approval_required"
        )


# ── G6: Content Calendar Sidebar ──────────────────────────────────────────


class TestContentCalendarUI:
    """Verify content calendar is wired into sidebar and UI."""

    def test_sidebar_has_calendar_button(self):
        content = (
            ROOT / "webui" / "components" / "sidebar" / "bottom" / "dashboard-nav" / "dashboard-nav.html"
        ).read_text()
        assert "contentCalendar" in content
        assert "Calendar" in content

    def test_content_calendar_store_exists(self):
        assert (ROOT / "webui" / "components" / "content-calendar" / "content-calendar-store.js").exists()

    def test_content_calendar_html_exists(self):
        assert (ROOT / "webui" / "components" / "content-calendar" / "content-calendar.html").exists()

    def test_store_registered_in_index(self):
        content = (ROOT / "webui" / "index.js").read_text()
        assert "content-calendar-store" in content

    def test_calendar_store_has_required_methods(self):
        content = (ROOT / "webui" / "components" / "content-calendar" / "content-calendar-store.js").read_text()
        assert "refresh" in content
        assert "setTag" in content
        assert "setStatusFilter" in content
        assert "by_tag" in content

    def test_calendar_html_has_tag_tabs(self):
        content = (ROOT / "webui" / "components" / "content-calendar" / "content-calendar.html").read_text()
        assert "marketing" in content
        assert "social" in content

    def test_calendar_html_has_status_pills(self):
        content = (ROOT / "webui" / "components" / "content-calendar" / "content-calendar.html").read_text()
        assert "queued" in content
        assert "in_progress" in content
        assert "done" in content

    def test_sidebar_nav_has_7_buttons(self):
        """Should have: Portfolio, Workflows, MOS, Tasks, Work Queue, Calendar, Trust."""
        content = (
            ROOT / "webui" / "components" / "sidebar" / "bottom" / "dashboard-nav" / "dashboard-nav.html"
        ).read_text()
        assert content.count("dashboard-nav-btn") >= 7  # class refs + :class refs
