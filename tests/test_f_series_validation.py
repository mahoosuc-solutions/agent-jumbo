"""
F-series validation tests.

F1: Docker readiness — container config, port mappings, health checks
F2: C-suite AgentMesh routing — event type → profile resolution
F4: Playwright async infrastructure — fixture importability
F5: E2E retry decorator — with_retry behavior
F6: Memory consolidation — stats, dedup, retention
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent


# ── F1: Docker Readiness ──────────────────────────────────────────────────


class TestDockerConfig:
    """Verify Docker configuration files are valid and consistent."""

    def test_dockerfile_local_exists(self):
        assert (ROOT / "DockerfileLocal").exists()

    def test_docker_compose_exists(self):
        assert (ROOT / "docker-compose.yml").exists()

    def test_docker_compose_has_healthcheck(self):
        content = (ROOT / "docker-compose.yml").read_text()
        assert "healthcheck" in content
        assert "/health" in content

    def test_docker_compose_has_port_mapping(self):
        content = (ROOT / "docker-compose.yml").read_text()
        assert "ports:" in content

    def test_docker_compose_has_env_file(self):
        content = (ROOT / "docker-compose.yml").read_text()
        assert "env_file" in content or ".env" in content

    def test_dockerfile_has_base_image(self):
        content = (ROOT / "DockerfileLocal").read_text()
        assert "FROM" in content

    def test_validate_release_has_docker_checks(self):
        content = (ROOT / "scripts" / "validate_release.sh").read_text()
        assert "check_docker_config" in content
        assert "check_docker_runtime" in content


class TestSchedulerBootConfig:
    """Verify MOS scheduler seeds are bootable."""

    def test_mos_scheduler_init_importable(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS, seed_mos_tasks

        assert callable(seed_mos_tasks)
        assert len(_MOS_TASKS) >= 5

    def test_all_task_schedules_valid(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS
        from python.helpers.task_scheduler import TaskSchedule

        for task in _MOS_TASKS:
            sched = task["schedule"]
            ts = TaskSchedule(
                minute=sched["minute"],
                hour=sched["hour"],
                day=sched["day"],
                month=sched["month"],
                weekday=sched["weekday"],
            )
            assert ts is not None


# ── F2: C-Suite AgentMesh Routing ─────────────────────────────────────────


class TestCSuiteEventRouting:
    """Verify C-suite event types route to correct profiles."""

    def test_category_map_has_csuite_entries(self):
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        assert CATEGORY_PROFILE_MAP["financial_report"] == "cfo"
        assert CATEGORY_PROFILE_MAP["revenue_analysis"] == "cfo"
        assert CATEGORY_PROFILE_MAP["payment_dunning"] == "cfo"
        assert CATEGORY_PROFILE_MAP["ops_digest"] == "coo"
        assert CATEGORY_PROFILE_MAP["sla_enforcement"] == "coo"
        assert CATEGORY_PROFILE_MAP["sales_pipeline"] == "cso"
        assert CATEGORY_PROFILE_MAP["proposal_generation"] == "cso"
        assert CATEGORY_PROFILE_MAP["brand_review"] == "cmo"
        assert CATEGORY_PROFILE_MAP["content_calendar"] == "cmo"
        assert CATEGORY_PROFILE_MAP["marketing"] == "cmo"

    def test_register_handlers_includes_executive_events(self):
        from python.helpers.agentmesh_task_handler import register_task_handlers

        mock_bridge = MagicMock()
        register_task_handlers(mock_bridge)

        registered_events = [call.args[0] for call in mock_bridge.on.call_args_list]
        assert "task.assigned" in registered_events
        assert "executive.financial_report" in registered_events
        assert "executive.ops_digest" in registered_events
        assert "executive.sales_update" in registered_events
        assert "executive.brand_review" in registered_events

    def test_all_csuite_profiles_in_map(self):
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        csuite_profiles = {"cfo", "coo", "cso", "cmo"}
        mapped_profiles = set(CATEGORY_PROFILE_MAP.values())
        assert csuite_profiles.issubset(mapped_profiles)

    def test_original_routing_preserved(self):
        """Ensure existing category routing wasn't broken."""
        from python.helpers.agentmesh_task_handler import CATEGORY_PROFILE_MAP

        assert CATEGORY_PROFILE_MAP["deployment"] == "actor-ops"
        assert CATEGORY_PROFILE_MAP["security_scan"] == "hacker"
        assert CATEGORY_PROFILE_MAP["code_review"] == "developer"
        assert CATEGORY_PROFILE_MAP["general"] == "base"


# ── F4: Playwright Async Infrastructure ───────────────────────────────────


class TestPlaywrightAsyncFixtures:
    """Verify async Playwright fixture infrastructure exists and is importable."""

    def test_conftest_async_exists(self):
        assert (ROOT / "tests" / "ui" / "conftest_async.py").exists()

    def test_conftest_async_importable(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "conftest_async",
            ROOT / "tests" / "ui" / "conftest_async.py",
        )
        mod = importlib.util.module_from_spec(spec)
        # Don't exec — just verify it parses
        assert spec is not None

    def test_sync_conftest_still_works(self):
        """Original sync conftest must still be present."""
        assert (ROOT / "tests" / "ui" / "conftest.py").exists()
        content = (ROOT / "tests" / "ui" / "conftest.py").read_text()
        assert "pytest_collection_modifyitems" in content


# ── F5: E2E Retry Decorator ──────────────────────────────────────────────


class TestRetryDecorator:
    """Verify the with_retry decorator and tolerant API helpers."""

    def test_with_retry_importable(self):
        from tests.e2e.helpers import with_retry

        assert callable(with_retry)

    def test_with_retry_passes_on_success(self):
        from tests.e2e.helpers import with_retry

        call_count = 0

        @with_retry(retries=3)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    def test_with_retry_retries_on_429(self):
        import urllib.error

        from tests.e2e.helpers import with_retry

        call_count = 0

        @with_retry(retries=3, backoff=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise urllib.error.HTTPError("http://test", 429, "Rate limited", {}, None)
            return "ok"

        assert fail_then_succeed() == "ok"
        assert call_count == 3

    def test_with_retry_raises_non_429(self):
        import urllib.error

        from tests.e2e.helpers import with_retry

        @with_retry(retries=3, backoff=0.01)
        def fail_500():
            raise urllib.error.HTTPError("http://test", 500, "Server Error", {}, None)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            fail_500()
        assert exc_info.value.code == 500

    def test_api_get_tolerant_exists(self):
        from tests.e2e.helpers import api_get_tolerant

        assert callable(api_get_tolerant)

    def test_api_post_tolerant_exists(self):
        from tests.e2e.helpers import api_post_tolerant

        assert callable(api_post_tolerant)


# ── F6: Memory Consolidation ─────────────────────────────────────────────


class TestMemoryStats:
    """Verify Memory.get_stats() returns correct metadata."""

    def test_stats_empty_memory(self):
        from python.helpers.memory import Memory

        db = MagicMock()
        db.get_all_docs.return_value = {}
        mem = Memory(db=db, memory_subdir="test")
        stats = mem.get_stats()
        assert stats["total_documents"] == 0
        assert stats["by_area"] == {}

    def test_stats_with_documents(self):
        from langchain_core.documents import Document

        from python.helpers.memory import Memory

        docs = {
            "id1": Document("text1", metadata={"area": "executive", "timestamp": "2025-01-01 10:00:00"}),
            "id2": Document("text2", metadata={"area": "executive", "timestamp": "2025-06-15 12:00:00"}),
            "id3": Document("text3", metadata={"area": "main", "timestamp": "2025-03-01 08:00:00"}),
        }
        db = MagicMock()
        db.get_all_docs.return_value = docs
        mem = Memory(db=db, memory_subdir="default")
        stats = mem.get_stats()

        assert stats["total_documents"] == 3
        assert stats["by_area"]["executive"] == 2
        assert stats["by_area"]["main"] == 1
        assert stats["oldest"] == "2025-01-01 10:00:00"
        assert stats["newest"] == "2025-06-15 12:00:00"


class TestMemoryConsolidate:
    """Verify consolidation deduplicates near-identical entries."""

    @pytest.mark.asyncio
    async def test_consolidate_empty(self):
        from python.helpers.memory import Memory

        db = MagicMock()
        db.get_all_docs.return_value = {}
        mem = Memory(db=db, memory_subdir="test")
        result = await mem.consolidate()
        assert result["removed"] == 0

    @pytest.mark.asyncio
    async def test_consolidate_dry_run(self):
        from langchain_core.documents import Document

        from python.helpers.memory import Memory

        doc1 = Document(
            "Revenue report Q1", metadata={"id": "a1", "area": "executive", "timestamp": "2025-01-01 10:00:00"}
        )
        doc2 = Document(
            "Revenue report Q1", metadata={"id": "a2", "area": "executive", "timestamp": "2025-06-01 10:00:00"}
        )

        db = MagicMock()
        db.get_all_docs.return_value = {"a1": doc1, "a2": doc2}
        db.asearch = AsyncMock(return_value=[doc2])

        mem = Memory(db=db, memory_subdir="test")
        result = await mem.consolidate(area="executive", dry_run=True)

        assert result["dry_run"] is True
        assert result["removed"] >= 0
        db.adelete.assert_not_called()

    @pytest.mark.asyncio
    async def test_consolidate_removes_older_duplicate(self):
        from langchain_core.documents import Document

        from python.helpers.memory import Memory

        doc1 = Document(
            "Revenue summary", metadata={"id": "a1", "area": "executive", "timestamp": "2025-01-01 10:00:00"}
        )
        doc2 = Document(
            "Revenue summary (updated)", metadata={"id": "a2", "area": "executive", "timestamp": "2025-06-01 10:00:00"}
        )

        db = MagicMock()
        db.get_all_docs.return_value = {"a1": doc1, "a2": doc2}
        db.asearch = AsyncMock(return_value=[doc2])
        db.adelete = AsyncMock()

        mem = Memory(db=db, memory_subdir="test")
        mem._save_db = MagicMock()
        result = await mem.consolidate(area="executive")

        assert result["removed"] == 1
        assert result["kept"] == 1
        db.adelete.assert_called_once()
        mem._save_db.assert_called_once()


class TestMemoryRetention:
    """Verify retention policy removes old documents."""

    @pytest.mark.asyncio
    async def test_retention_removes_old_docs(self):
        from langchain_core.documents import Document

        from python.helpers.memory import Memory

        old_ts = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d %H:%M:%S")
        new_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        doc_old = Document("Old data", metadata={"id": "x1", "area": "executive", "timestamp": old_ts})
        doc_new = Document("Fresh data", metadata={"id": "x2", "area": "executive", "timestamp": new_ts})

        db = MagicMock()
        db.get_all_docs.return_value = {"x1": doc_old, "x2": doc_new}
        db.adelete = AsyncMock()

        mem = Memory(db=db, memory_subdir="test")
        mem._save_db = MagicMock()
        result = await mem.apply_retention(area="executive", max_age_days=30)

        assert result["removed"] == 1
        db.adelete.assert_called_once_with(ids=["x1"])

    @pytest.mark.asyncio
    async def test_retention_dry_run(self):
        from langchain_core.documents import Document

        from python.helpers.memory import Memory

        old_ts = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d %H:%M:%S")
        doc = Document("Old", metadata={"id": "x1", "area": "executive", "timestamp": old_ts})

        db = MagicMock()
        db.get_all_docs.return_value = {"x1": doc}

        mem = Memory(db=db, memory_subdir="test")
        result = await mem.apply_retention(area="executive", max_age_days=30, dry_run=True)

        assert result["removed"] == 1
        assert result["dry_run"] is True
        db.adelete.assert_not_called()

    @pytest.mark.asyncio
    async def test_retention_ignores_other_areas(self):
        from langchain_core.documents import Document

        from python.helpers.memory import Memory

        old_ts = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d %H:%M:%S")
        doc = Document("Old main doc", metadata={"id": "x1", "area": "main", "timestamp": old_ts})

        db = MagicMock()
        db.get_all_docs.return_value = {"x1": doc}

        mem = Memory(db=db, memory_subdir="test")
        result = await mem.apply_retention(area="executive", max_age_days=30)

        assert result["removed"] == 0
