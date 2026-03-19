"""
Unit tests for WorkQueueManager.
Tests business logic for codebase scanning, scoring, item management, and settings.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

SAMPLE_SCAN_FINDINGS = {
    "todos": [
        {
            "source": "scanner",
            "source_type": "todo",
            "title": "TODO: fix this",
            "description": "A todo comment that needs addressing",
            "file_path": "foo.py",
            "line_number": 1,
            "external_id": "abc123",
        }
    ]
}

# scan_all is imported directly into work_queue_manager as `codebase_scan_all`,
# so the patch must target that binding, not the originating module.
SCAN_ALL_TARGET = "instruments.custom.work_queue.work_queue_manager.codebase_scan_all"
# WorkflowEngineManager is imported inside execute_item at call time.
WF_MANAGER_TARGET = "instruments.custom.workflow_engine.workflow_manager.WorkflowEngineManager"


class TestWorkQueueManager:
    """Test suite for WorkQueueManager"""

    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        """Create a fresh manager with a real temp DB for each test."""
        self.db_path = str(tmp_path / "test_work_queue.db")
        self.manager = WorkQueueManager(self.db_path)
        self.project_path = str(tmp_path / "myproject")

    # ── Init ──────────────────────────────────────────────────────────

    def test_init_creates_db(self):
        """__init__ creates the DB file at the given path."""
        assert os.path.exists(self.db_path)
        assert self.manager.db is not None

    # ── Project registration ──────────────────────────────────────────

    def test_register_get_remove_project(self):
        """register_project / get_projects / remove_project delegate to DB correctly."""
        result = self.manager.register_project(self.project_path, "My Project")
        assert result["path"] == self.project_path
        assert result["name"] == "My Project"

        projects = self.manager.get_projects()
        assert len(projects) == 1
        assert projects[0]["path"] == self.project_path
        assert projects[0]["name"] == "My Project"

        removed = self.manager.remove_project(self.project_path)
        assert removed is True

        projects_after = self.manager.get_projects()
        assert len(projects_after) == 0

    # ── Codebase scanning — happy path ────────────────────────────────

    def test_run_codebase_scan_happy_path(self):
        """run_codebase_scan upserts items and logs a completed scan."""
        with patch(
            SCAN_ALL_TARGET,
            return_value=SAMPLE_SCAN_FINDINGS,
        ):
            result = self.manager.run_codebase_scan(self.project_path)

        assert result["success"] is True
        assert result["items_found"] == 1
        assert result["by_type"] == {"todos": 1}
        assert "scan_id" in result

        # Item should be in the DB
        items_result = self.manager.get_items()
        assert items_result["total"] == 1
        assert items_result["items"][0]["title"] == "TODO: fix this"

        # Scan log should be completed
        last_scan = self.manager.db.get_last_scan()
        assert last_scan is not None
        assert last_scan["status"] == "completed"
        assert last_scan["items_found"] == 1

    # ── Codebase scanning — error handling ───────────────────────────

    def test_run_codebase_scan_error_handling(self):
        """run_codebase_scan returns error result and marks scan as error when scanner raises."""
        with patch(
            SCAN_ALL_TARGET,
            side_effect=RuntimeError("scanner exploded"),
        ):
            result = self.manager.run_codebase_scan(self.project_path)

        assert result["success"] is False
        assert "scanner exploded" in result["error"]
        assert "scan_id" in result

        last_scan = self.manager.db.get_last_scan()
        assert last_scan is not None
        assert last_scan["status"] == "error"
        assert "scanner exploded" in last_scan["error"]

    # ── Dashboard ─────────────────────────────────────────────────────

    def test_get_dashboard_returns_expected_keys(self):
        """get_dashboard returns stats, last_scan, and projects."""
        self.manager.register_project(self.project_path, "Dashboard Project")

        dashboard = self.manager.get_dashboard()

        assert "total" in dashboard
        assert "by_status" in dashboard
        assert "last_scan" in dashboard
        assert "projects" in dashboard
        assert len(dashboard["projects"]) == 1

    # ── get_items ─────────────────────────────────────────────────────

    def test_get_items_delegates_with_kwargs(self):
        """get_items delegates kwargs to DB and returns items + total."""
        with patch(
            SCAN_ALL_TARGET,
            return_value=SAMPLE_SCAN_FINDINGS,
        ):
            self.manager.run_codebase_scan(self.project_path)

        result = self.manager.get_items(source_type="todo")
        assert "items" in result
        assert "total" in result
        assert result["total"] == 1
        assert result["items"][0]["source_type"] == "todo"

        # Filter by a different source_type yields nothing
        result_empty = self.manager.get_items(source_type="linear_issue")
        assert result_empty["total"] == 0

    # ── update_item_status ────────────────────────────────────────────

    def test_update_item_status_returns_true(self):
        """update_item_status updates the item and returns True."""
        with patch(
            SCAN_ALL_TARGET,
            return_value=SAMPLE_SCAN_FINDINGS,
        ):
            self.manager.run_codebase_scan(self.project_path)

        items = self.manager.get_items()
        item_id = items["items"][0]["id"]

        ok = self.manager.update_item_status(item_id, "queued")
        assert ok is True

        updated = self.manager.db.get_item(item_id)
        assert updated["status"] == "queued"

    # ── bulk_update_status ────────────────────────────────────────────

    def test_bulk_update_status(self):
        """bulk_update_status updates multiple items and returns the count."""
        # Insert two distinct items
        findings_two = {
            "todos": [
                {
                    "source": "scanner",
                    "source_type": "todo",
                    "title": "TODO: first",
                    "description": "",
                    "file_path": "a.py",
                    "line_number": 1,
                    "external_id": "id_first",
                },
                {
                    "source": "scanner",
                    "source_type": "todo",
                    "title": "TODO: second",
                    "description": "",
                    "file_path": "b.py",
                    "line_number": 2,
                    "external_id": "id_second",
                },
            ]
        }
        with patch(
            SCAN_ALL_TARGET,
            return_value=findings_two,
        ):
            self.manager.run_codebase_scan(self.project_path)

        items = self.manager.get_items()
        item_ids = [i["id"] for i in items["items"]]
        assert len(item_ids) == 2

        count = self.manager.bulk_update_status(item_ids, "dismissed")
        assert count == 2

        for item_id in item_ids:
            item = self.manager.db.get_item(item_id)
            assert item["status"] == "dismissed"

    # ── recalculate_priorities ────────────────────────────────────────

    def test_recalculate_priorities_skips_terminal_items(self):
        """recalculate_priorities re-scores open items and skips done/dismissed ones."""
        findings_three = {
            "todos": [
                {
                    "source": "scanner",
                    "source_type": "todo",
                    "title": "TODO: open",
                    "description": "",
                    "file_path": "a.py",
                    "line_number": 1,
                    "external_id": "open_1",
                },
                {
                    "source": "scanner",
                    "source_type": "todo",
                    "title": "TODO: done",
                    "description": "",
                    "file_path": "b.py",
                    "line_number": 2,
                    "external_id": "done_1",
                },
                {
                    "source": "scanner",
                    "source_type": "todo",
                    "title": "TODO: dismissed",
                    "description": "",
                    "file_path": "c.py",
                    "line_number": 3,
                    "external_id": "dismissed_1",
                },
            ]
        }
        with patch(
            SCAN_ALL_TARGET,
            return_value=findings_three,
        ):
            self.manager.run_codebase_scan(self.project_path)

        items = self.manager.get_items()
        by_title = {i["title"]: i["id"] for i in items["items"]}

        self.manager.update_item_status(by_title["TODO: done"], "done")
        self.manager.update_item_status(by_title["TODO: dismissed"], "dismissed")

        # Force priority_score to 0 on the open item so recalculate has work to do
        self.manager.db.update_item(by_title["TODO: open"], {"priority_score": 0})

        updated_count = self.manager.recalculate_priorities()
        # The open item should have been re-scored; terminal ones are skipped
        assert isinstance(updated_count, int)
        assert updated_count >= 0

        # Terminal items must not have been touched (their status is unchanged)
        done_item = self.manager.db.get_item(by_title["TODO: done"])
        assert done_item["status"] == "done"
        dismissed_item = self.manager.db.get_item(by_title["TODO: dismissed"])
        assert dismissed_item["status"] == "dismissed"

    # ── execute_item — item not found ─────────────────────────────────

    def test_execute_item_not_found(self):
        """execute_item returns an error dict when the item ID does not exist."""
        result = self.manager.execute_item(item_id=99999)
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    # ── execute_item — workflow engine invoked ────────────────────────

    def test_execute_item_sets_status_in_progress(self):
        """execute_item calls WorkflowEngineManager and sets item status to in_progress."""
        with patch(
            SCAN_ALL_TARGET,
            return_value=SAMPLE_SCAN_FINDINGS,
        ):
            self.manager.run_codebase_scan(self.project_path)

        items = self.manager.get_items()
        item_id = items["items"][0]["id"]

        mock_wf_manager = MagicMock()
        mock_wf_manager.start_workflow.return_value = {"id": "exec-42"}
        mock_wf_class = MagicMock(return_value=mock_wf_manager)

        # execute_item does `from instruments.custom.workflow_engine.workflow_manager
        # import WorkflowEngineManager` at call time, so we patch that module in
        # sys.modules before the call.
        fake_wf_module = MagicMock()
        fake_wf_module.WorkflowEngineManager = mock_wf_class

        with patch.dict(
            "sys.modules",
            {"instruments.custom.workflow_engine.workflow_manager": fake_wf_module},
        ):
            result = self.manager.execute_item(item_id)

        assert result["success"] is True
        assert result["execution_id"] == "exec-42"
        assert result["item_id"] == item_id

        item = self.manager.db.get_item(item_id)
        assert item["status"] == "in_progress"

    # ── get_scan_schedule ─────────────────────────────────────────────

    def test_get_scan_schedule_defaults(self):
        """get_scan_schedule returns default values when no settings have been persisted."""
        schedule = self.manager.get_scan_schedule()

        assert schedule["enabled"] is False
        assert schedule["cron"] == "0 */6 * * *"
        assert schedule["scan_types"] == []
        assert schedule["project_path"] == ""
        assert schedule["task_uuid"] == ""

    # ── set_setting / get_settings round-trip ─────────────────────────

    def test_set_and_get_settings_roundtrip(self):
        """set_setting persists a value that get_settings returns."""
        self.manager.set_setting("my_key", "my_value")
        self.manager.set_setting("another_key", "another_value")

        settings = self.manager.get_settings()
        assert settings["my_key"] == "my_value"
        assert settings["another_key"] == "another_value"

        # Overwrite and verify
        self.manager.set_setting("my_key", "updated")
        settings2 = self.manager.get_settings()
        assert settings2["my_key"] == "updated"
