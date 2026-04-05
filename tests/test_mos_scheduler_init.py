"""Tests for MOS cross-system scheduler initialization."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


class TestMosSchedulerInit:
    def test_registers_all_four_tasks(self):
        mock_scheduler = MagicMock()
        mock_scheduler.reload = AsyncMock()
        mock_scheduler.get_tasks.return_value = []
        mock_scheduler.add_task = AsyncMock()

        mock_task_schedule = MagicMock()

        patch_base = "python.helpers.task_scheduler"
        with (
            patch(f"{patch_base}.TaskScheduler") as mock_ts_cls,
            patch(f"{patch_base}.ScheduledTask") as mock_st_cls,
            patch(f"{patch_base}.TaskSchedule", mock_task_schedule),
        ):
            mock_ts_cls.get.return_value = mock_scheduler
            mock_st_cls.create = MagicMock(return_value=MagicMock())

            import importlib

            import python.helpers.mos_scheduler_init as mos_init

            importlib.reload(mos_init)
            result = asyncio.run(mos_init.seed_mos_tasks())

        assert result["status"] == "ok"
        assert result["total"] == 4
        assert len(result["registered"]) == 4
        assert result["skipped_existing"] == []
        assert mock_scheduler.add_task.call_count == 4

    def test_skips_existing_tasks(self):
        existing = MagicMock()
        existing.name = "mos-linear-to-motion"

        mock_scheduler = MagicMock()
        mock_scheduler.reload = AsyncMock()
        mock_scheduler.get_tasks.return_value = [existing]
        mock_scheduler.add_task = AsyncMock()

        patch_base = "python.helpers.task_scheduler"
        with (
            patch(f"{patch_base}.TaskScheduler") as mock_ts_cls,
            patch(f"{patch_base}.ScheduledTask") as mock_st_cls,
            patch(f"{patch_base}.TaskSchedule", MagicMock()),
        ):
            mock_ts_cls.get.return_value = mock_scheduler
            mock_st_cls.create = MagicMock(return_value=MagicMock())

            import importlib

            import python.helpers.mos_scheduler_init as mos_init

            importlib.reload(mos_init)
            result = asyncio.run(mos_init.seed_mos_tasks())

        assert result["status"] == "ok"
        assert "mos-linear-to-motion" in result["skipped_existing"]
        assert len(result["registered"]) == 3
        assert mock_scheduler.add_task.call_count == 3

    def test_idempotent_when_all_exist(self):
        existing_tasks = [
            MagicMock(name=n)
            for n in [
                "mos-linear-to-motion",
                "mos-linear-activity-digest",
                "mos-analytics-daily-digest",
                "mos-support-queue-check",
            ]
        ]
        # MagicMock name= sets the mock name, need to set .name attribute
        for task, name in zip(
            existing_tasks,
            [
                "mos-linear-to-motion",
                "mos-linear-activity-digest",
                "mos-analytics-daily-digest",
                "mos-support-queue-check",
            ],
        ):
            task.name = name

        mock_scheduler = MagicMock()
        mock_scheduler.reload = AsyncMock()
        mock_scheduler.get_tasks.return_value = existing_tasks
        mock_scheduler.add_task = AsyncMock()

        patch_base = "python.helpers.task_scheduler"
        with (
            patch(f"{patch_base}.TaskScheduler") as mock_ts_cls,
            patch(f"{patch_base}.ScheduledTask") as mock_st_cls,
            patch(f"{patch_base}.TaskSchedule", MagicMock()),
        ):
            mock_ts_cls.get.return_value = mock_scheduler
            mock_st_cls.create = MagicMock(return_value=MagicMock())

            import importlib

            import python.helpers.mos_scheduler_init as mos_init

            importlib.reload(mos_init)
            result = asyncio.run(mos_init.seed_mos_tasks())

        assert result["status"] == "ok"
        assert len(result["registered"]) == 0
        assert len(result["skipped_existing"]) == 4
        assert mock_scheduler.add_task.call_count == 0

    def test_task_names_are_unique(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        names = [t["name"] for t in _MOS_TASKS]
        assert len(names) == len(set(names)), "Duplicate MOS task names found"

    def test_all_tasks_have_required_fields(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        for task in _MOS_TASKS:
            assert "name" in task, "Task missing name"
            assert "prompt" in task, f"Task '{task.get('name')}' missing prompt"
            assert "schedule" in task, f"Task '{task.get('name')}' missing schedule"
            sched = task["schedule"]
            for field in ("minute", "hour", "day", "month", "weekday"):
                assert field in sched, f"Task '{task['name']}' missing schedule field: {field}"

    def test_linear_to_motion_runs_weekdays_only(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        task = next(t for t in _MOS_TASKS if t["name"] == "mos-linear-to-motion")
        assert task["schedule"]["weekday"] == "1-5"
        assert task["schedule"]["hour"] == "8,12,17"

    def test_support_queue_runs_hourly(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        task = next(t for t in _MOS_TASKS if t["name"] == "mos-support-queue-check")
        assert task["schedule"]["hour"] == "*"
        assert task["schedule"]["minute"] == "0"

    def test_analytics_digest_runs_daily_7am(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        task = next(t for t in _MOS_TASKS if t["name"] == "mos-analytics-daily-digest")
        assert task["schedule"]["hour"] == "7"
        assert task["schedule"]["minute"] == "0"

    def test_linear_activity_runs_daily_6am(self):
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        task = next(t for t in _MOS_TASKS if t["name"] == "mos-linear-activity-digest")
        assert task["schedule"]["hour"] == "6"
        assert task["schedule"]["minute"] == "0"

    def test_handles_scheduler_import_error(self):
        with patch.dict("sys.modules", {"python.helpers.task_scheduler": None}):
            import importlib

            import python.helpers.mos_scheduler_init as mos_init

            importlib.reload(mos_init)
            result = asyncio.run(mos_init.seed_mos_tasks())

        assert result["status"] == "skipped"
        assert "unavailable" in result["reason"].lower() or "none" in result["reason"].lower()
