"""Tests for WBM hospitality scheduler initialization."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestWbmSchedulerInit:
    def test_skips_without_wbm_tenant_id(self, monkeypatch):
        monkeypatch.delenv("WBM_TENANT_ID", raising=False)
        from python.helpers.wbm_scheduler_init import seed_wbm_tasks

        result = asyncio.run(seed_wbm_tasks())
        assert result["status"] == "skipped"
        assert "WBM_TENANT_ID" in result["reason"]

    def test_registers_all_nine_tasks(self, monkeypatch):
        monkeypatch.setenv("WBM_TENANT_ID", "test-tenant")

        mock_task = MagicMock()
        mock_task.name = "__new__"

        mock_scheduler = MagicMock()
        mock_scheduler.reload = AsyncMock()
        mock_scheduler.get_tasks.return_value = []
        mock_scheduler.add_task = AsyncMock()

        mock_scheduled_task = MagicMock(return_value=mock_task)
        mock_task_schedule = MagicMock()

        patch_base = "python.helpers.task_scheduler"
        with (
            patch(f"{patch_base}.TaskScheduler") as mock_ts_cls,
            patch(f"{patch_base}.ScheduledTask") as mock_st_cls,
            patch(f"{patch_base}.TaskSchedule", mock_task_schedule),
            patch(f"{patch_base}.TaskScheduler.get", return_value=mock_scheduler),
        ):
            mock_ts_cls.get.return_value = mock_scheduler
            mock_st_cls.create = mock_scheduled_task

            # Import inside the patch context so the lazy import sees our mocks
            import importlib

            import python.helpers.wbm_scheduler_init as wbm_init_mod

            importlib.reload(wbm_init_mod)
            result = asyncio.run(wbm_init_mod.seed_wbm_tasks())

        assert result["status"] == "ok"
        assert result["total"] == 9
        assert len(result["registered"]) == 9
        assert result["skipped_existing"] == []
        assert mock_scheduler.add_task.call_count == 9

    def test_skips_existing_tasks(self, monkeypatch):
        monkeypatch.setenv("WBM_TENANT_ID", "test-tenant")

        existing = MagicMock()
        existing.name = "wbm-daily-ops-brief"

        mock_scheduler = MagicMock()
        mock_scheduler.reload = AsyncMock()
        mock_scheduler.get_tasks.return_value = [existing]
        mock_scheduler.add_task = AsyncMock()

        mock_task_schedule = MagicMock()

        patch_base = "python.helpers.task_scheduler"
        with (
            patch(f"{patch_base}.TaskScheduler") as mock_ts_cls,
            patch(f"{patch_base}.ScheduledTask") as mock_st_cls,
            patch(f"{patch_base}.TaskSchedule", mock_task_schedule),
            patch(f"{patch_base}.TaskScheduler.get", return_value=mock_scheduler),
        ):
            mock_ts_cls.get.return_value = mock_scheduler
            mock_st_cls.create = MagicMock(return_value=MagicMock())

            import importlib

            import python.helpers.wbm_scheduler_init as wbm_init_mod

            importlib.reload(wbm_init_mod)
            result = asyncio.run(wbm_init_mod.seed_wbm_tasks())

        assert result["status"] == "ok"
        assert "wbm-daily-ops-brief" in result["skipped_existing"]
        assert len(result["registered"]) == 8
        assert mock_scheduler.add_task.call_count == 8

    def test_task_names_are_unique(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        names = [t["name"] for t in _WBM_TASKS]
        assert len(names) == len(set(names)), "Duplicate task names found"

    def test_all_tasks_have_required_fields(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        for task in _WBM_TASKS:
            assert "name" in task
            assert "prompt" in task
            assert "schedule" in task
            sched = task["schedule"]
            for field in ("minute", "hour", "day", "month", "weekday"):
                assert field in sched, f"Task '{task['name']}' missing schedule field: {field}"

    def test_seasonal_task_runs_quarterly(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        seasonal = next(t for t in _WBM_TASKS if t["name"] == "wbm-seasonal-rate-activation")
        assert seasonal["schedule"]["month"] == "3,6,9,12"
        assert seasonal["schedule"]["day"] == "1"

    def test_yearly_task_runs_january_first(self):
        from python.helpers.wbm_scheduler_init import _WBM_TASKS

        yearly = next(t for t in _WBM_TASKS if t["name"] == "wbm-yearly-platform-audit")
        assert yearly["schedule"]["month"] == "1"
        assert yearly["schedule"]["day"] == "1"
