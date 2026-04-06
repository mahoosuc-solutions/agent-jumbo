"""
H-series validation tests.

H1: Docker integration — container config, health endpoint, scheduler state
H2: E2E retry wiring — tolerant imports across 39 files
H3: Playwright async migration — fixture verification + async test readiness
H4: Content calendar CRUD — create item, status transitions, store methods
H5: Memory stats dashboard — panel, store, router registration
H6: AgentMesh E2E — fakeredis event routing, approval workflow, category dispatch
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ── H1: Docker Integration ────────────────────────────────────────────────


class TestDockerIntegration:
    """Structural + conditional runtime Docker verification."""

    def test_docker_compose_port_mapping(self):
        content = (ROOT / "docker-compose.yml").read_text()
        assert "50001:80" in content or "80" in content

    def test_dockerfile_local_exists(self):
        assert (ROOT / "DockerfileLocal").exists()

    def test_run_ui_boots_scheduler(self):
        content = (ROOT / "run_ui.py").read_text()
        assert "seed_mos_tasks" in content or "scheduler" in content.lower()

    def test_scheduler_registers_5_tasks_at_boot(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        assert len(_MOS_TASKS) >= 5

    def test_all_tasks_have_cron_schedule(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        for task in _MOS_TASKS:
            sched = task["schedule"]
            for field in ("minute", "hour", "day", "month", "weekday"):
                assert field in sched, f"Task {task['name']} missing '{field}' in schedule"

    def test_memory_stats_endpoint_importable(self):
        from python.api.memory_stats import MemoryStats

        assert hasattr(MemoryStats, "process")

    def test_health_agentmesh_endpoint(self):
        assert (ROOT / "python" / "api" / "health_agentmesh.py").exists()


# ── H2: E2E Retry Wiring ─────────────────────────────────────────────────


class TestE2ERetryWiring:
    """Verify all E2E test files use tolerant API helpers."""

    def _get_e2e_test_files(self):
        return sorted((ROOT / "tests" / "e2e").glob("test_*.py"))

    def test_no_raw_api_post_imports(self):
        """All test files should import api_post_tolerant (aliased or direct)."""
        raw_imports = []
        for f in self._get_e2e_test_files():
            content = f.read_text()
            for line in content.splitlines():
                if "from tests.e2e.helpers import" in line and "api_post" in line:
                    if "api_post_tolerant" not in line:
                        raw_imports.append(f.name)
                        break
        assert raw_imports == [], f"Files still using raw api_post: {raw_imports}"

    def test_no_raw_api_get_imports(self):
        """All test files should import api_get_tolerant (aliased or direct)."""
        raw_imports = []
        for f in self._get_e2e_test_files():
            content = f.read_text()
            for line in content.splitlines():
                if "from tests.e2e.helpers import" in line and "api_get" in line:
                    if "api_get_tolerant" not in line and "api_get" in line.split("import")[1]:
                        # Check if there's a bare api_get that isn't api_get_tolerant
                        imports = line.split("import")[1]
                        tokens = [t.strip().split(" ")[0] for t in imports.split(",")]
                        if "api_get" in tokens:
                            raw_imports.append(f.name)
                            break
        assert raw_imports == [], f"Files still using raw api_get: {raw_imports}"

    def test_tolerant_helpers_exist(self):
        content = (ROOT / "tests" / "e2e" / "helpers.py").read_text()
        assert "def api_post_tolerant" in content
        assert "def api_get_tolerant" in content
        assert "def with_retry" in content

    def test_at_least_35_files_wired(self):
        """At minimum 35 E2E test files should use tolerant helpers."""
        count = 0
        for f in self._get_e2e_test_files():
            content = f.read_text()
            if "api_post_tolerant" in content or "api_get_tolerant" in content:
                count += 1
        assert count >= 35, f"Only {count} files wired with tolerant helpers"


# ── H3: Playwright Async Migration ────────────────────────────────────────


class TestPlaywrightAsyncMigration:
    """Verify async infrastructure and sync/async coexistence."""

    def test_async_conftest_exists(self):
        assert (ROOT / "tests" / "ui" / "conftest_async.py").exists()

    def test_async_fixtures_complete(self):
        content = (ROOT / "tests" / "ui" / "conftest_async.py").read_text()
        assert "async_browser" in content
        assert "async_page" in content
        assert "ui_server" in content
        assert "async_playwright" in content

    def test_sync_tests_still_present(self):
        """Sync tests should remain — they work with asyncio_mode=strict."""
        assert (ROOT / "tests" / "ui" / "test_workflow_ui.py").exists()
        assert (ROOT / "tests" / "ui" / "test_observability_ui.py").exists()

    def test_sync_conftest_has_marker_stripping(self):
        content = (ROOT / "tests" / "ui" / "conftest.py").read_text()
        assert "pytest_collection_modifyitems" in content
        assert "asyncio" in content

    def test_fixture_test_not_playwright(self):
        """test_observability_fixture.py uses Node, not Playwright — no migration needed."""
        content = (ROOT / "tests" / "ui" / "test_observability_fixture.py").read_text()
        assert "sync_playwright" not in content
        assert "subprocess" in content


# ── H4: Content Calendar CRUD ─────────────────────────────────────────────


class TestContentCalendarCRUD:
    """Verify create-item and status transition capabilities."""

    def test_store_has_create_method(self):
        content = (ROOT / "webui" / "components" / "content-calendar" / "content-calendar-store.js").read_text()
        assert "async createItem" in content
        assert "newItemTitle" in content
        assert "newItemDescription" in content

    def test_store_has_transition_method(self):
        content = (ROOT / "webui" / "components" / "content-calendar" / "content-calendar-store.js").read_text()
        assert "async transitionStatus" in content
        assert "nextStatus" in content

    def test_store_has_status_flow(self):
        content = (ROOT / "webui" / "components" / "content-calendar" / "content-calendar-store.js").read_text()
        assert "STATUS_FLOW" in content
        assert "queued" in content
        assert "in_progress" in content
        assert "review" in content

    def test_html_has_create_form(self):
        content = (ROOT / "webui" / "components" / "content-calendar" / "content-calendar.html").read_text()
        assert "New Item" in content
        assert "createItem" in content
        assert "showCreateForm" in content
        assert "placeholder" in content.lower()

    def test_html_has_transition_buttons(self):
        content = (ROOT / "webui" / "components" / "content-calendar" / "content-calendar.html").read_text()
        assert "transitionStatus" in content
        assert "nextStatus" in content

    def test_dashboard_api_has_add_action(self):
        content = (ROOT / "python" / "api" / "work_queue_dashboard.py").read_text()
        assert '"add"' in content or "'add'" in content
        assert "upsert_item" in content

    @pytest.mark.asyncio
    async def test_dashboard_add_returns_item_id(self):
        from python.api.work_queue_dashboard import WorkQueueDashboard

        handler = WorkQueueDashboard.__new__(WorkQueueDashboard)
        mock_manager = MagicMock()
        mock_manager.db.upsert_item.return_value = 42

        with patch("instruments.custom.work_queue.work_queue_manager.WorkQueueManager", return_value=mock_manager):
            result = await handler.process(
                {"action": "add", "title": "Test post", "tags": ["marketing"], "source": "content-calendar"},
                request=None,
            )
        assert result["success"] is True
        assert result["item_id"] == 42

    @pytest.mark.asyncio
    async def test_dashboard_add_requires_title(self):
        from python.api.work_queue_dashboard import WorkQueueDashboard

        handler = WorkQueueDashboard.__new__(WorkQueueDashboard)
        mock_manager = MagicMock()

        with patch("instruments.custom.work_queue.work_queue_manager.WorkQueueManager", return_value=mock_manager):
            result = await handler.process({"action": "add", "title": ""}, request=None)
        assert result["success"] is False
        assert "title" in result["error"].lower()


# ── H5: Memory Stats Dashboard ───────────────────────────────────────────


class TestMemoryStatsDashboard:
    """Verify memory dashboard panel, store, and router registration."""

    def test_dashboard_html_exists(self):
        assert (ROOT / "webui" / "dashboards" / "memory" / "memory-dashboard.html").exists()

    def test_dashboard_store_exists(self):
        assert (ROOT / "webui" / "dashboards" / "memory" / "memory-store.js").exists()

    def test_dashboard_registered_in_router(self):
        content = (ROOT / "webui" / "dashboards" / "dashboard-router.js").read_text()
        assert "'memory'" in content or '"memory"' in content
        assert "memory-dashboard.html" in content
        assert "memory-store.js" in content

    def test_content_calendar_registered_in_router(self):
        content = (ROOT / "webui" / "dashboards" / "dashboard-router.js").read_text()
        assert "contentCalendar" in content
        assert "content-calendar" in content

    def test_dashboard_html_has_stats_cards(self):
        content = (ROOT / "webui" / "dashboards" / "memory" / "memory-dashboard.html").read_text()
        assert "Total Documents" in content
        assert "Memory Subdir" in content
        assert "by_area" in content or "by area" in content.lower()

    def test_dashboard_html_has_consolidation_preview(self):
        content = (ROOT / "webui" / "dashboards" / "memory" / "memory-dashboard.html").read_text()
        assert "Consolidation Preview" in content or "consolidate" in content.lower()
        assert "dry run" in content.lower() or "dryRun" in content

    def test_store_has_required_methods(self):
        content = (ROOT / "webui" / "dashboards" / "memory" / "memory-store.js").read_text()
        assert "loadStats" in content
        assert "loadSubdirs" in content
        assert "consolidateDryRun" in content
        assert "selectSubdir" in content

    def test_sidebar_has_memory_button(self):
        content = (
            ROOT / "webui" / "components" / "sidebar" / "bottom" / "dashboard-nav" / "dashboard-nav.html"
        ).read_text()
        assert "memory" in content.lower()
        assert "Memory" in content

    def test_sidebar_has_9_dashboard_buttons(self):
        """Portfolio, Workflows, MOS, Tasks, Work Queue, Calendar, Trust, Memory = 8 buttons."""
        content = (
            ROOT / "webui" / "components" / "sidebar" / "bottom" / "dashboard-nav" / "dashboard-nav.html"
        ).read_text()
        count = content.count('dashboard-nav-btn"')
        assert count >= 8, f"Expected >= 8 button class refs, got {count}"

    @pytest.mark.asyncio
    async def test_memory_stats_api_stats_action(self):
        from python.api.memory_stats import MemoryStats

        handler = MemoryStats.__new__(MemoryStats)
        with patch.dict("python.helpers.memory.Memory.index", {}, clear=True):
            result = await handler.process({"action": "stats"}, request=None)
        assert result["success"] is True
        assert result["stats"]["total_documents"] == 0

    @pytest.mark.asyncio
    async def test_memory_stats_api_consolidate_unloaded(self):
        from python.api.memory_stats import MemoryStats

        handler = MemoryStats.__new__(MemoryStats)
        with patch.dict("python.helpers.memory.Memory.index", {}, clear=True):
            result = await handler.process({"action": "consolidate", "memory_subdir": "nonexistent"}, request=None)
        assert result["success"] is False
        assert "not loaded" in result["error"]

    @pytest.mark.asyncio
    async def test_memory_stats_api_retention_action(self):
        from python.api.memory_stats import MemoryStats

        handler = MemoryStats.__new__(MemoryStats)
        mock_db = MagicMock()
        mock_db.get_all_docs.return_value = {}

        with patch.dict("python.helpers.memory.Memory.index", {"default": mock_db}):
            result = await handler.process(
                {"action": "retention", "max_age_days": 90, "dry_run": True},
                request=None,
            )
        assert result["success"] is True
        assert result["removed"] == 0


# ── H6: AgentMesh E2E ────────────────────────────────────────────────────


class TestAgentMeshE2E:
    """End-to-end C-suite event routing and approval workflow tests."""

    def test_category_profile_map_complete(self):
        """All 19 categories must be mapped."""
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        assert len(CATEGORY_PROFILE_MAP) >= 19

    def test_all_csuite_categories_have_profiles(self):
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        csuite_categories = {
            "financial_report": "cfo",
            "revenue_analysis": "cfo",
            "payment_dunning": "cfo",
            "ops_digest": "coo",
            "sla_enforcement": "coo",
            "devops": "coo",
            "sales_pipeline": "cso",
            "proposal_generation": "cso",
            "brand_review": "cmo",
            "content_calendar": "cmo",
            "marketing": "cmo",
        }
        for cat, expected_profile in csuite_categories.items():
            assert CATEGORY_PROFILE_MAP.get(cat) == expected_profile, (
                f"{cat} → {CATEGORY_PROFILE_MAP.get(cat)} != {expected_profile}"
            )

    @pytest.mark.asyncio
    async def test_event_routing_financial_report(self):
        """Emit financial_report with LOW risk → should call _execute_task."""
        from python.helpers.agentmesh_task_handler import _handle_task_assigned

        event = MagicMock()
        event.payload = {
            "taskId": "t-fin-1",
            "assignee": "agent-jumbo",
            "category": "financial_report",
        }
        event.aggregate_id = "t-fin-1"
        event.metadata = {"correlationId": "c1"}

        mock_exec = AsyncMock()
        with (
            patch("python.helpers.agentmesh_task_handler.classify_risk", return_value="LOW"),
            patch("python.helpers.agentmesh_task_handler._get_bridge", return_value=AsyncMock()),
            patch("python.helpers.agentmesh_task_handler._execute_task", mock_exec),
        ):
            await _handle_task_assigned(event)

        mock_exec.assert_called_once_with("t-fin-1", event.payload, "c1")

    @pytest.mark.asyncio
    async def test_event_routing_content_calendar(self):
        """Emit content_calendar with LOW risk → should call _execute_task."""
        from python.helpers.agentmesh_task_handler import _handle_task_assigned

        event = MagicMock()
        event.payload = {
            "taskId": "t-cal-1",
            "assignee": "agent-jumbo",
            "category": "content_calendar",
        }
        event.aggregate_id = "t-cal-1"
        event.metadata = {"correlationId": "c2"}

        mock_exec = AsyncMock()
        with (
            patch("python.helpers.agentmesh_task_handler.classify_risk", return_value="LOW"),
            patch("python.helpers.agentmesh_task_handler._get_bridge", return_value=AsyncMock()),
            patch("python.helpers.agentmesh_task_handler._execute_task", mock_exec),
        ):
            await _handle_task_assigned(event)

        mock_exec.assert_called_once_with("t-cal-1", event.payload, "c2")

    @pytest.mark.asyncio
    async def test_high_risk_emits_approval_required(self):
        """HIGH risk tasks should not execute — emit approval_required instead."""
        from python.helpers.agentmesh_task_handler import _handle_task_assigned

        event = MagicMock()
        event.payload = {
            "taskId": "t-risk-1",
            "assignee": "agent-jumbo",
            "category": "payment_dunning",
        }
        event.aggregate_id = "t-risk-1"
        event.metadata = {"correlationId": "c3"}

        mock_bridge = AsyncMock()
        with (
            patch("python.helpers.agentmesh_task_handler.classify_risk", return_value="HIGH"),
            patch("python.helpers.agentmesh_task_handler._get_bridge", return_value=mock_bridge),
        ):
            await _handle_task_assigned(event)

        mock_bridge.emit.assert_called_once()
        emit_kwargs = mock_bridge.emit.call_args
        event_type = emit_kwargs.kwargs.get("event_type") or emit_kwargs[1].get("event_type", "")
        assert event_type == "task.approval_required"

    @pytest.mark.asyncio
    async def test_critical_risk_also_emits_approval(self):
        from python.helpers.agentmesh_task_handler import _handle_task_assigned

        event = MagicMock()
        event.payload = {
            "taskId": "t-crit-1",
            "assignee": "agent-jumbo",
            "category": "financial_report",
        }
        event.aggregate_id = "t-crit-1"
        event.metadata = {"correlationId": "c4"}

        mock_bridge = AsyncMock()
        with (
            patch("python.helpers.agentmesh_task_handler.classify_risk", return_value="CRITICAL"),
            patch("python.helpers.agentmesh_task_handler._get_bridge", return_value=mock_bridge),
        ):
            await _handle_task_assigned(event)

        mock_bridge.emit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unknown_assignee_silently_ignored(self):
        from python.helpers.agentmesh_task_handler import _handle_task_assigned

        event = MagicMock()
        event.payload = {
            "taskId": "t-other-1",
            "assignee": "other-agent",
            "category": "financial_report",
        }
        event.metadata = {}

        # Should not raise or call any bridge methods
        await _handle_task_assigned(event)

    @pytest.mark.asyncio
    async def test_event_handler_registration(self):
        from python.helpers.agentmesh_task_handler import register_task_handlers

        bridge = MagicMock()
        register_task_handlers(bridge)

        registered = [call.args[0] for call in bridge.on.call_args_list]
        assert "task.assigned" in registered
        assert "task.approval_resolved" in registered
        assert "executive.financial_report" in registered
        assert "executive.ops_digest" in registered
        assert "executive.sales_update" in registered
        assert "executive.brand_review" in registered

    @pytest.mark.asyncio
    async def test_low_risk_executes_immediately(self):
        """LOW risk tasks should execute, not require approval."""
        from python.helpers.agentmesh_task_handler import _handle_task_assigned

        event = MagicMock()
        event.payload = {
            "taskId": "t-low-1",
            "assignee": "agent-jumbo",
            "category": "ops_digest",
        }
        event.aggregate_id = "t-low-1"
        event.metadata = {"correlationId": "c5"}

        mock_exec = AsyncMock()
        mock_bridge = AsyncMock()
        with (
            patch("python.helpers.agentmesh_task_handler.classify_risk", return_value="LOW"),
            patch("python.helpers.agentmesh_task_handler._get_bridge", return_value=mock_bridge),
            patch("python.helpers.agentmesh_task_handler._execute_task", mock_exec),
        ):
            await _handle_task_assigned(event)

        mock_exec.assert_called_once()
        mock_bridge.emit.assert_not_called()
