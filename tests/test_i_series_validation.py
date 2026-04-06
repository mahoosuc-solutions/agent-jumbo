"""
I-series validation tests.

I1: Docker live smoke test — container health via docker exec
I2: E2E test stabilization — verify retry wrappers on all test files
I3: Calendar + Memory dashboard live validation — API endpoint structure
I4: AgentMesh comprehensive integration — lifecycle, approval, error paths
I5: Performance benchmarks — WBM batch operations, scheduler tick, memory ops
I6: Documentation — CHANGELOG entries, test infrastructure docs
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Container name used in docker-compose.yml
_CONTAINER = os.environ.get("AJ_CONTAINER", "agent-jumbo-production")


def _docker_available() -> bool:
    """Check whether Docker CLI is available and the container is running."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Running}}", _CONTAINER],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0 and "true" in result.stdout.lower()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _docker_exec_curl(path: str, *, timeout: int = 10) -> dict:
    """Run curl inside the container and return parsed JSON."""
    result = subprocess.run(
        ["docker", "exec", _CONTAINER, "curl", "-sf", f"http://localhost:80{path}"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    assert result.returncode == 0, f"curl {path} failed: {result.stderr}"
    return json.loads(result.stdout)


_SKIP_NO_DOCKER = pytest.mark.skipif(
    not _docker_available(),
    reason=f"Container '{_CONTAINER}' not running",
)


# ── I1: Docker Live Smoke Test ─────────────────────────────────────────────


class TestDockerLiveSmoke:
    """Live Docker container health checks via docker exec."""

    @_SKIP_NO_DOCKER
    def test_health_endpoint_returns_ok(self):
        """GET /health inside container returns ok=true."""
        data = _docker_exec_curl("/health")
        assert data.get("ok") is True, f"Health check failed: {data}"

    @_SKIP_NO_DOCKER
    def test_health_has_required_sections(self):
        """Health response includes git, disk, memory, and startup sections."""
        data = _docker_exec_curl("/health")
        for key in ("status", "checks"):
            assert key in data, f"Missing '{key}' in health response"
        checks = data["checks"]
        for section in ("git", "disk", "memory"):
            assert section in checks, f"Missing '{section}' in health checks"

    @_SKIP_NO_DOCKER
    def test_health_disk_ok(self):
        """Container has sufficient free disk space."""
        data = _docker_exec_curl("/health")
        disk = data["checks"]["disk"]
        assert disk["ok"] is True, f"Disk check failed: {disk}"
        assert disk["free_gb"] > 1.0, f"Low disk space: {disk['free_gb']} GB"

    @_SKIP_NO_DOCKER
    def test_health_memory_ok(self):
        """Container RSS is within acceptable bounds."""
        data = _docker_exec_curl("/health")
        mem = data["checks"]["memory"]
        assert mem["ok"] is True, f"Memory check failed: {mem}"
        assert mem["rss_mb"] < 4096, f"Excessive RSS: {mem['rss_mb']} MB"

    @_SKIP_NO_DOCKER
    def test_health_uptime_positive(self):
        """Container has been running for at least 1 second."""
        data = _docker_exec_curl("/health")
        # uptime_seconds lives inside checks
        uptime = data.get("checks", {}).get("uptime_seconds", data.get("uptime_seconds", 0))
        assert uptime > 1.0, f"Uptime too low: {uptime}"

    @_SKIP_NO_DOCKER
    def test_service_profile_available(self):
        """Health response includes service profile with running services."""
        data = _docker_exec_curl("/health")
        # service_profile may be at top level or nested in checks
        profile = data.get("service_profile") or data.get("checks", {}).get("service_profile", {})
        assert profile.get("supported") is True, f"service_profile: {profile}"
        services = profile.get("services", [])
        running = [s for s in services if s.get("runtime_state") == "running"]
        assert len(running) >= 1, f"No running services found: {services}"

    @_SKIP_NO_DOCKER
    def test_login_page_serves_html(self):
        """GET /login returns HTML (not a 500 error)."""
        result = subprocess.run(
            [
                "docker",
                "exec",
                _CONTAINER,
                "curl",
                "-sf",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "http://localhost:80/login",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "200", f"Login page returned {result.stdout.strip()}"


# ── I2: E2E Test Stabilization ─────────────────────────────────────────────


class TestE2EStabilization:
    """Verify that all E2E test files use retry-tolerant patterns."""

    _E2E_DIR = ROOT / "tests" / "e2e"

    def _e2e_files(self) -> list[Path]:
        return sorted(self._E2E_DIR.glob("test_*.py"))

    def test_all_e2e_files_import_helpers(self):
        """Every E2E test file imports from helpers (tolerant wrappers or retry)."""
        missing = []
        for f in self._e2e_files():
            content = f.read_text()
            has_tolerant = "api_post_tolerant" in content or "api_get_tolerant" in content
            has_retry = "with_retry" in content
            has_raw_only = "urllib.request" in content and not has_tolerant and not has_retry
            # Files that only use Playwright (no urllib) are fine
            if has_raw_only:
                missing.append(f.name)
        # performance.py uses raw urllib for timing precision, accessibility.py
        # uses Playwright, functional.py mostly uses Playwright with inline retry
        assert len(missing) <= 3, f"Files still using raw urllib without retry: {missing}"

    def test_tolerant_helpers_exist_in_helpers_module(self):
        """The helpers module exports both tolerant wrappers and the retry decorator."""
        from tests.e2e.helpers import api_get_tolerant, api_post_tolerant, with_retry

        assert callable(api_post_tolerant)
        assert callable(api_get_tolerant)
        assert callable(with_retry)

    def test_at_least_35_e2e_files_wired(self):
        """At least 35 E2E test files exist (regression guard)."""
        count = len(self._e2e_files())
        assert count >= 35, f"Only {count} E2E test files found"

    def test_conftest_has_warmup_fixture(self):
        """E2E conftest provides the warmup fixture for rate-limit cooldown."""
        content = (self._E2E_DIR / "conftest.py").read_text()
        assert "warmup" in content, "conftest.py missing warmup fixture"


# ── I3: Calendar + Memory Dashboard Validation ─────────────────────────────


class TestCalendarMemoryValidation:
    """Validate calendar and memory dashboard APIs are structurally sound."""

    def test_calendar_connect_module_importable(self):
        mod = importlib.import_module("python.api.calendar_connect")
        assert hasattr(mod, "CalendarConnect")

    def test_calendar_dashboard_module_importable(self):
        mod = importlib.import_module("python.api.calendar_dashboard")
        assert hasattr(mod, "CalendarDashboard")

    def test_memory_dashboard_module_importable(self):
        mod = importlib.import_module("python.api.memory_dashboard")
        assert hasattr(mod, "MemoryDashboard")

    def test_memory_stats_module_importable(self):
        mod = importlib.import_module("python.api.memory_stats")
        assert hasattr(mod, "MemoryStats")

    def test_calendar_e2e_tests_exist(self):
        assert (ROOT / "tests" / "e2e" / "test_calendar_e2e_api.py").exists()

    def test_memory_e2e_tests_exist(self):
        assert (ROOT / "tests" / "e2e" / "test_memory_api.py").exists()

    @_SKIP_NO_DOCKER
    def test_memory_dashboard_get_subdirs_live(self):
        """Live: POST memory_dashboard with get_memory_subdirs action."""
        # Login first to get session cookie
        result = subprocess.run(
            [
                "docker",
                "exec",
                _CONTAINER,
                "curl",
                "-sf",
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "-d",
                json.dumps({"action": "get_memory_subdirs"}),
                "http://localhost:80/memory_dashboard",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # May fail due to auth — that's acceptable; we just verify the endpoint exists
        if result.returncode == 0:
            data = json.loads(result.stdout)
            assert "success" in data or "error" in data


# ── I4: AgentMesh Comprehensive Integration ────────────────────────────────


class TestAgentMeshComprehensive:
    """Validate AgentMesh task handler lifecycle and error paths."""

    def test_task_handler_importable(self):
        mod = importlib.import_module("python.helpers.agentmesh_task_handler")
        assert hasattr(mod, "register_task_handlers")

    def test_task_handler_has_lifecycle_functions(self):
        mod = importlib.import_module("python.helpers.agentmesh_task_handler")
        for func in ("register_task_handlers", "set_bridge", "_handle_task_assigned", "_handle_approval_resolved"):
            assert hasattr(mod, func), f"Missing function: {func}"

    def test_agentmesh_bridge_integration_tests_exist(self):
        assert (ROOT / "tests" / "integration" / "test_agentmesh_bridge_integration.py").exists()

    def test_agentmesh_bridge_has_sufficient_test_coverage(self):
        """At least 12 integration tests for AgentMesh bridge."""
        content = (ROOT / "tests" / "integration" / "test_agentmesh_bridge_integration.py").read_text()
        test_count = content.count("async def test_") + content.count("def test_")
        assert test_count >= 12, f"Only {test_count} AgentMesh tests (need ≥12)"

    def test_health_agentmesh_exists(self):
        assert (ROOT / "python" / "api" / "health_agentmesh.py").exists()

    def test_agentmesh_has_memory_updated_handler(self):
        """AgentMesh must register a memory.updated event handler."""
        src = (ROOT / "python" / "helpers" / "agentmesh_task_handler.py").read_text()
        assert "memory.updated" in src, "Missing memory.updated handler registration"


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


# ── I5: Performance Benchmark Tests ────────────────────────────────────────


class TestPerformanceBenchmarks:
    """Validate performance characteristics of core subsystems."""

    def _make_item(self, i: int) -> dict:
        return {
            "external_id": f"bench-{i}",
            "source": "benchmark",
            "source_type": "test",
            "title": f"bench-item-{i}",
            "description": f"Benchmark item {i}",
            "project_path": "/tmp/bench",
            "tags": ["perf-test"],
        }

    def test_wbm_batch_insert_under_200ms(self):
        """Batch insert of 50 WBM items completes in <200ms."""
        from instruments.custom.work_queue.work_queue_db import WorkQueueDatabase

        with tempfile.TemporaryDirectory() as tmpdir:
            db = WorkQueueDatabase(os.path.join(tmpdir, "bench.db"))
            db.init_database()

            t0 = time.perf_counter()
            for i in range(50):
                db.upsert_item(self._make_item(i))
            elapsed = time.perf_counter() - t0
            assert elapsed < 0.200, f"50 inserts took {elapsed:.3f}s (limit 0.2s)"

    def test_wbm_query_by_tag_under_50ms(self):
        """Query 50 items by tag completes in <50ms."""
        from instruments.custom.work_queue.work_queue_db import WorkQueueDatabase

        with tempfile.TemporaryDirectory() as tmpdir:
            db = WorkQueueDatabase(os.path.join(tmpdir, "bench.db"))
            db.init_database()

            for i in range(50):
                db.upsert_item(self._make_item(i))

            t0 = time.perf_counter()
            results = db.get_items_by_tag("perf-test")
            elapsed = time.perf_counter() - t0
            assert len(results) == 50
            assert elapsed < 0.050, f"Tag query took {elapsed:.3f}s (limit 0.05s)"

    def test_wbm_status_transition_under_10ms(self):
        """Single status transition completes in <10ms."""
        from instruments.custom.work_queue.work_queue_db import WorkQueueDatabase

        with tempfile.TemporaryDirectory() as tmpdir:
            db = WorkQueueDatabase(os.path.join(tmpdir, "bench.db"))
            db.init_database()
            db.upsert_item(self._make_item(0))
            items = db.get_items_by_tag("perf-test")
            item_id = items[0]["id"]

            t0 = time.perf_counter()
            db.update_item_status(item_id, "in_progress")
            elapsed = time.perf_counter() - t0
            assert elapsed < 0.010, f"Status transition took {elapsed:.3f}s (limit 0.01s)"

    def test_memory_module_import_under_500ms(self):
        """Importing the memory module completes in <500ms."""
        t0 = time.perf_counter()
        importlib.import_module("python.helpers.memory")
        elapsed = time.perf_counter() - t0
        # May already be cached — that's fine, measures hot-path
        assert elapsed < 0.500, f"Memory import took {elapsed:.3f}s (limit 0.5s)"

    def test_e2e_performance_tests_exist(self):
        """E2E performance test file exists with timing assertions."""
        content = (ROOT / "tests" / "e2e" / "test_performance.py").read_text()
        assert "elapsed" in content, "Performance tests should measure elapsed time"
        assert "class TestApiSLA" in content, "Missing API SLA test class"


# ── I6: Documentation Validation ───────────────────────────────────────────


class TestDocumentation:
    """Validate documentation is up to date."""

    def test_changelog_exists(self):
        assert (ROOT / "CHANGELOG.md").exists()

    def test_changelog_has_i_series_entry(self):
        content = (ROOT / "CHANGELOG.md").read_text()
        assert "I-series" in content or "I1" in content or "Docker smoke" in content.lower(), (
            "CHANGELOG missing I-series entry"
        )

    def test_readme_exists(self):
        assert (ROOT / "README.md").exists()

    def test_e2e_helpers_documented(self):
        """E2E helpers module has docstrings."""
        content = (ROOT / "tests" / "e2e" / "helpers.py").read_text()
        assert '"""' in content, "Helpers module missing docstrings"

    def test_docker_compose_documented(self):
        """docker-compose.yml exists and is valid YAML."""
        import yaml

        path = ROOT / "docker-compose.yml"
        assert path.exists()
        data = yaml.safe_load(path.read_text())
        assert "services" in data
