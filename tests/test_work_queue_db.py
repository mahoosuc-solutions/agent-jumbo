"""Unit tests for WorkQueueDatabase."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWorkQueueDatabase:
    def setup_method(self):
        from instruments.custom.work_queue.work_queue_db import WorkQueueDatabase

        self.tmp = tempfile.mkdtemp()
        self.db = WorkQueueDatabase(os.path.join(self.tmp, "test_wq.db"))

    def _make_item(self, **overrides):
        base = {
            "external_id": "ext-1",
            "source": "github",
            "source_type": "pull_request",
            "title": "Fix login bug",
            "description": "Users cannot log in when 2FA is enabled",
            "file_path": "src/auth/login.py",
            "line_number": 42,
            "url": "https://github.com/org/repo/pull/1",
            "status": "discovered",
            "priority_score": 75,
            "priority_raw": {"urgency": 3, "impact": 4},
            "effort_estimate": "small",
            "effort_minutes": 30,
            "project_path": "/projects/myapp",
            "linear_priority": 2,
            "linear_state": "In Progress",
            "linear_assignee": "alice",
            "linear_labels": ["bug", "auth"],
        }
        base.update(overrides)
        return base

    # ── init_database ────────────────────────────────────────────────

    def test_init_database_creates_tables(self):
        conn = self.db.get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "projects" in tables
        assert "work_items" in tables
        assert "scan_log" in tables
        assert "settings" in tables

    def test_init_database_creates_indexes(self):
        conn = self.db.get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
        indexes = {row[0] for row in cursor.fetchall()}
        conn.close()
        assert "idx_work_items_dedup" in indexes
        assert "idx_work_items_status" in indexes
        assert "idx_work_items_project" in indexes
        assert "idx_work_items_priority" in indexes

    # ── register_project ─────────────────────────────────────────────

    def test_register_project_insert(self):
        result = self.db.register_project("/projects/alpha", "Alpha")
        assert result == {"path": "/projects/alpha", "name": "Alpha"}
        projects = self.db.get_projects()
        assert len(projects) == 1
        assert projects[0]["path"] == "/projects/alpha"
        assert projects[0]["name"] == "Alpha"

    def test_register_project_replace(self):
        self.db.register_project("/projects/alpha", "Alpha")
        self.db.register_project("/projects/alpha", "Alpha Renamed")
        projects = self.db.get_projects()
        assert len(projects) == 1
        assert projects[0]["name"] == "Alpha Renamed"

    # ── get_projects ─────────────────────────────────────────────────

    def test_get_projects_ordered_by_name(self):
        self.db.register_project("/projects/zebra", "Zebra")
        self.db.register_project("/projects/alpha", "Alpha")
        self.db.register_project("/projects/mango", "Mango")
        projects = self.db.get_projects()
        names = [p["name"] for p in projects]
        assert names == ["Alpha", "Mango", "Zebra"]

    # ── remove_project ───────────────────────────────────────────────

    def test_remove_project_returns_true_when_found(self):
        self.db.register_project("/projects/alpha", "Alpha")
        result = self.db.remove_project("/projects/alpha")
        assert result is True
        assert self.db.get_projects() == []

    def test_remove_project_returns_false_when_not_found(self):
        result = self.db.remove_project("/projects/nonexistent")
        assert result is False

    # ── upsert_item ──────────────────────────────────────────────────

    def test_upsert_item_insert_new(self):
        self.db.upsert_item(self._make_item())
        rows, total = self.db.get_items()
        assert total == 1
        assert rows[0]["title"] == "Fix login bug"
        assert rows[0]["source"] == "github"
        assert rows[0]["priority_score"] == 75

    def test_upsert_item_dedup_updates_title_and_score(self):
        self.db.upsert_item(self._make_item())
        self.db.upsert_item(self._make_item(title="Fix login bug UPDATED", priority_score=90))
        rows, total = self.db.get_items()
        assert total == 1
        assert rows[0]["title"] == "Fix login bug UPDATED"
        assert rows[0]["priority_score"] == 90

    def test_upsert_item_different_project_path_not_deduped(self):
        self.db.upsert_item(self._make_item(project_path="/projects/app1"))
        self.db.upsert_item(self._make_item(project_path="/projects/app2"))
        _, total = self.db.get_items()
        assert total == 2

    # ── get_item ─────────────────────────────────────────────────────

    def test_get_item_found(self):
        self.db.upsert_item(self._make_item())
        rows, _ = self.db.get_items()
        item_id = rows[0]["id"]
        item = self.db.get_item(item_id)
        assert item is not None
        assert item["title"] == "Fix login bug"
        assert item["id"] == item_id

    def test_get_item_not_found(self):
        result = self.db.get_item(999999)
        assert result is None

    # ── get_items pagination ─────────────────────────────────────────

    def test_get_items_pagination(self):
        for i in range(10):
            self.db.upsert_item(self._make_item(external_id=f"ext-{i}", title=f"Item {i}"))
        rows, total = self.db.get_items(page=1, page_size=4)
        assert total == 10
        assert len(rows) == 4

        rows2, _ = self.db.get_items(page=2, page_size=4)
        assert len(rows2) == 4

        rows3, _ = self.db.get_items(page=3, page_size=4)
        assert len(rows3) == 2

    # ── get_items filtering ──────────────────────────────────────────

    def test_get_items_filter_by_status(self):
        self.db.upsert_item(self._make_item(external_id="e1", status="discovered"))
        self.db.upsert_item(self._make_item(external_id="e2", status="queued"))
        self.db.upsert_item(self._make_item(external_id="e3", status="done"))
        rows, total = self.db.get_items(status="queued")
        assert total == 1
        assert rows[0]["status"] == "queued"

    def test_get_items_filter_by_source(self):
        self.db.upsert_item(self._make_item(external_id="e1", source="github"))
        self.db.upsert_item(self._make_item(external_id="e2", source="linear"))
        rows, total = self.db.get_items(source="linear")
        assert total == 1
        assert rows[0]["source"] == "linear"

    def test_get_items_filter_by_source_type(self):
        self.db.upsert_item(self._make_item(external_id="e1", source_type="pull_request"))
        self.db.upsert_item(self._make_item(external_id="e2", source_type="issue"))
        rows, total = self.db.get_items(source_type="issue")
        assert total == 1
        assert rows[0]["source_type"] == "issue"

    def test_get_items_filter_by_project_path(self):
        self.db.upsert_item(self._make_item(external_id="e1", project_path="/proj/a"))
        self.db.upsert_item(self._make_item(external_id="e2", project_path="/proj/b"))
        rows, total = self.db.get_items(project_path="/proj/a")
        assert total == 1
        assert rows[0]["project_path"] == "/proj/a"

    # ── get_items sort validation ─────────────────────────────────────

    def test_get_items_invalid_sort_column_falls_back_to_default(self):
        # Inject two items with different priority scores
        self.db.upsert_item(self._make_item(external_id="e1", priority_score=10, title="Low"))
        self.db.upsert_item(self._make_item(external_id="e2", priority_score=99, title="High"))
        # Invalid sort_by should fall back to priority_score DESC without raising
        rows, total = self.db.get_items(sort_by="INVALID_COLUMN", sort_dir="DESC")
        assert total == 2
        assert rows[0]["priority_score"] >= rows[1]["priority_score"]

    # ── search_items ─────────────────────────────────────────────────

    def test_search_items_matches_title(self):
        self.db.upsert_item(self._make_item(external_id="e1", title="Fix login crash"))
        self.db.upsert_item(
            self._make_item(
                external_id="e2",
                title="Update dashboard UI",
                description="Redesign the chart widgets",
                file_path="src/dashboard/charts.py",
            )
        )
        results = self.db.search_items("login")
        assert len(results) == 1
        assert "login" in results[0]["title"].lower()

    def test_search_items_matches_description(self):
        self.db.upsert_item(
            self._make_item(
                external_id="e1",
                title="Some task",
                description="Refactor the authentication module",
            )
        )
        self.db.upsert_item(
            self._make_item(
                external_id="e2",
                title="Other task",
                description="Update the billing service",
            )
        )
        results = self.db.search_items("authentication")
        assert len(results) == 1
        assert "authentication" in results[0]["description"].lower()

    def test_search_items_matches_file_path(self):
        self.db.upsert_item(self._make_item(external_id="e1", file_path="src/auth/tokens.py"))
        self.db.upsert_item(self._make_item(external_id="e2", file_path="src/billing/invoice.py"))
        results = self.db.search_items("tokens")
        assert len(results) == 1
        assert "tokens" in results[0]["file_path"]

    # ── update_item_status ───────────────────────────────────────────

    def test_update_item_status_queued_sets_queued_at(self):
        self.db.upsert_item(self._make_item())
        rows, _ = self.db.get_items()
        item_id = rows[0]["id"]
        self.db.update_item_status(item_id, "queued")
        item = self.db.get_item(item_id)
        assert item["status"] == "queued"
        assert item["queued_at"] is not None
        assert item["started_at"] is None
        assert item["completed_at"] is None

    def test_update_item_status_in_progress_sets_started_at(self):
        self.db.upsert_item(self._make_item())
        rows, _ = self.db.get_items()
        item_id = rows[0]["id"]
        self.db.update_item_status(item_id, "in_progress")
        item = self.db.get_item(item_id)
        assert item["status"] == "in_progress"
        assert item["started_at"] is not None
        assert item["completed_at"] is None

    def test_update_item_status_done_sets_completed_at(self):
        self.db.upsert_item(self._make_item())
        rows, _ = self.db.get_items()
        item_id = rows[0]["id"]
        self.db.update_item_status(item_id, "done")
        item = self.db.get_item(item_id)
        assert item["status"] == "done"
        assert item["completed_at"] is not None

    def test_update_item_status_arbitrary_sets_no_extra_timestamp(self):
        self.db.upsert_item(self._make_item())
        rows, _ = self.db.get_items()
        item_id = rows[0]["id"]
        self.db.update_item_status(item_id, "skipped")
        item = self.db.get_item(item_id)
        assert item["status"] == "skipped"
        assert item["queued_at"] is None
        assert item["started_at"] is None
        assert item["completed_at"] is None

    # ── update_item ──────────────────────────────────────────────────

    def test_update_item_allowed_fields(self):
        self.db.upsert_item(self._make_item())
        rows, _ = self.db.get_items()
        item_id = rows[0]["id"]
        result = self.db.update_item(
            item_id,
            {
                "priority_score": 55,
                "effort_estimate": "large",
                "effort_minutes": 120,
                "execution_id": 7,
                "execution_status": "running",
            },
        )
        assert result is True
        item = self.db.get_item(item_id)
        assert item["priority_score"] == 55
        assert item["effort_estimate"] == "large"
        assert item["effort_minutes"] == 120
        assert item["execution_id"] == 7
        assert item["execution_status"] == "running"

    def test_update_item_rejects_disallowed_fields(self):
        self.db.upsert_item(self._make_item())
        rows, _ = self.db.get_items()
        item_id = rows[0]["id"]
        result = self.db.update_item(item_id, {"title": "Hacked title", "source": "injected"})
        assert result is False
        item = self.db.get_item(item_id)
        assert item["title"] == "Fix login bug"
        assert item["source"] == "github"

    # ── bulk_update_status ───────────────────────────────────────────

    def test_bulk_update_status_updates_multiple(self):
        for i in range(3):
            self.db.upsert_item(self._make_item(external_id=f"ext-{i}"))
        rows, _ = self.db.get_items()
        ids = [r["id"] for r in rows]
        count = self.db.bulk_update_status(ids, "queued")
        assert count == 3
        updated, _ = self.db.get_items(status="queued")
        assert len(updated) == 3

    def test_bulk_update_status_empty_list_returns_zero(self):
        count = self.db.bulk_update_status([], "queued")
        assert count == 0

    # ── get_dashboard_data ────────────────────────────────────────────

    def test_get_dashboard_data_aggregation(self):
        self.db.upsert_item(
            self._make_item(external_id="e1", status="discovered", source="github", source_type="pull_request")
        )
        self.db.upsert_item(self._make_item(external_id="e2", status="queued", source="github", source_type="issue"))
        self.db.upsert_item(self._make_item(external_id="e3", status="done", source="linear", source_type="issue"))
        data = self.db.get_dashboard_data()
        assert data["total"] == 3
        assert data["by_status"]["discovered"] == 1
        assert data["by_status"]["queued"] == 1
        assert data["by_status"]["done"] == 1
        assert data["by_source"]["github"] == 2
        assert data["by_source"]["linear"] == 1
        assert data["by_type"]["pull_request"] == 1
        assert data["by_type"]["issue"] == 2
        assert "done_this_week" in data

    def test_get_dashboard_data_filtered_by_project(self):
        self.db.upsert_item(self._make_item(external_id="e1", project_path="/proj/a", source="github"))
        self.db.upsert_item(self._make_item(external_id="e2", project_path="/proj/b", source="linear"))
        data = self.db.get_dashboard_data(project_path="/proj/a")
        assert data["total"] == 1
        assert "github" in data["by_source"]
        assert "linear" not in data["by_source"]

    # ── start_scan / complete_scan / get_last_scan ────────────────────

    def test_start_and_complete_scan(self):
        scan_id = self.db.start_scan("full", "/projects/myapp")
        assert isinstance(scan_id, int)
        assert scan_id > 0
        self.db.complete_scan(scan_id, items_found=17)
        last = self.db.get_last_scan()
        assert last is not None
        assert last["status"] == "completed"
        assert last["items_found"] == 17
        assert last["completed_at"] is not None

    def test_complete_scan_with_error(self):
        scan_id = self.db.start_scan("partial", "/projects/myapp")
        self.db.complete_scan(scan_id, items_found=0, error="Timeout reached")
        last = self.db.get_last_scan()
        assert last["status"] == "error"
        assert last["error"] == "Timeout reached"

    def test_get_last_scan_filtered_by_type_and_path(self):
        sid1 = self.db.start_scan("full", "/proj/a")
        self.db.complete_scan(sid1, 5)
        sid2 = self.db.start_scan("partial", "/proj/b")
        self.db.complete_scan(sid2, 3)

        last_full = self.db.get_last_scan(scan_type="full")
        assert last_full["scan_type"] == "full"

        last_b = self.db.get_last_scan(project_path="/proj/b")
        assert last_b["project_path"] == "/proj/b"

    def test_get_last_scan_returns_none_when_empty(self):
        result = self.db.get_last_scan()
        assert result is None

    # ── settings ─────────────────────────────────────────────────────

    def test_set_and_get_setting(self):
        self.db.set_setting("scan_interval", "3600")
        value = self.db.get_setting("scan_interval")
        assert value == "3600"

    def test_get_setting_returns_default_when_missing(self):
        value = self.db.get_setting("nonexistent_key", default="fallback")
        assert value == "fallback"

    def test_get_setting_returns_empty_string_default(self):
        value = self.db.get_setting("nonexistent_key")
        assert value == ""

    def test_set_setting_replaces_existing(self):
        self.db.set_setting("mode", "auto")
        self.db.set_setting("mode", "manual")
        assert self.db.get_setting("mode") == "manual"

    def test_get_all_settings(self):
        self.db.set_setting("key_a", "val_a")
        self.db.set_setting("key_b", "val_b")
        all_settings = self.db.get_all_settings()
        assert all_settings == {"key_a": "val_a", "key_b": "val_b"}

    def test_get_all_settings_empty(self):
        result = self.db.get_all_settings()
        assert result == {}
