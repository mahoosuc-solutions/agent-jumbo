"""Unit tests for TaskScheduler.tick() — cron evaluation, due-task filtering, state machine."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from freezegun import freeze_time

from python.helpers.task_scheduler import (
    ScheduledTask,
    SchedulerTaskList,
    TaskSchedule,
    TaskState,
)


def _make_schedule(
    minute="*",
    hour="*",
    day="*",
    month="*",
    weekday="*",
    tz="UTC",
) -> TaskSchedule:
    return TaskSchedule(minute=minute, hour=hour, day=day, month=month, weekday=weekday, timezone=tz)


def _make_task(
    schedule_kwargs: dict,
    last_run: datetime | None = None,
    state: TaskState = TaskState.IDLE,
    name: str = "test-task",
) -> ScheduledTask:
    schedule = _make_schedule(**schedule_kwargs)
    task = ScheduledTask(
        name=name,
        system_prompt="test",
        prompt="test prompt",
        schedule=schedule,
    )
    if last_run is not None:
        task.last_run = last_run
    task.state = state
    return task


# ---------------------------------------------------------------------------
# TestCheckSchedule
# ---------------------------------------------------------------------------


class TestCheckSchedule:
    """Tests for ScheduledTask.check_schedule() cron evaluation."""

    @freeze_time("2025-06-15 10:00:30", tz_offset=0)  # Sunday
    def test_every_minute_is_due(self):
        """'* * * * *' should always be due."""
        task = _make_task({"minute": "*", "hour": "*"})
        assert task.check_schedule() is True

    @freeze_time("2025-06-16 10:15:30", tz_offset=0)  # Monday
    def test_task_not_due_when_cron_doesnt_match(self):
        """Task runs at minute=30, current time is :15 → not due."""
        task = _make_task({"minute": "30", "hour": "*"})
        assert task.check_schedule() is False

    @freeze_time("2025-06-16 10:30:30", tz_offset=0)  # Monday
    def test_task_due_when_minute_matches(self):
        """Task runs at minute=30, current time is 10:30 → due."""
        task = _make_task({"minute": "30", "hour": "*"})
        assert task.check_schedule() is True

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)
    def test_dedup_guard_same_minute(self):
        """Task with last_run in same cron minute returns False."""
        now = datetime(2025, 6, 16, 10, 0, 15, tzinfo=timezone.utc)
        task = _make_task({"minute": "*", "hour": "*"}, last_run=now)
        assert task.check_schedule() is False

    @freeze_time("2025-06-16 10:01:30", tz_offset=0)
    def test_dedup_allows_next_minute(self):
        """Task with last_run one minute earlier returns True."""
        last = datetime(2025, 6, 16, 10, 0, 15, tzinfo=timezone.utc)
        task = _make_task({"minute": "*", "hour": "*"}, last_run=last)
        assert task.check_schedule() is True

    @freeze_time("2025-06-14 10:00:30", tz_offset=0)  # Saturday
    def test_weekday_filter_saturday(self):
        """Weekday-only schedule (1-5) on Saturday returns False."""
        task = _make_task({"minute": "0", "hour": "10", "weekday": "1-5"})
        assert task.check_schedule() is False

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)  # Monday
    def test_weekday_filter_monday(self):
        """Weekday-only schedule (1-5) on Monday returns True."""
        task = _make_task({"minute": "0", "hour": "10", "weekday": "1-5"})
        assert task.check_schedule() is True

    @freeze_time("2025-06-16 12:00:30", tz_offset=0)
    def test_hourly_at_zero_true(self):
        """Hourly schedule at minute=0: True at :00."""
        task = _make_task({"minute": "0", "hour": "*"})
        assert task.check_schedule() is True

    @freeze_time("2025-06-16 12:30:30", tz_offset=0)
    def test_hourly_at_zero_false(self):
        """Hourly schedule at minute=0: False at :30."""
        task = _make_task({"minute": "0", "hour": "*"})
        assert task.check_schedule() is False

    @freeze_time("2025-06-16 08:00:30", tz_offset=0)
    def test_specific_hours_match(self):
        """Schedule at hour=8,12,17: True at 8:00."""
        task = _make_task({"minute": "0", "hour": "8,12,17"})
        assert task.check_schedule() is True

    @freeze_time("2025-06-16 09:00:30", tz_offset=0)
    def test_specific_hours_no_match(self):
        """Schedule at hour=8,12,17: False at 9:00."""
        task = _make_task({"minute": "0", "hour": "8,12,17"})
        assert task.check_schedule() is False

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)
    def test_dedup_guard_naive_last_run(self):
        """Dedup guard handles naive last_run (no tzinfo) by treating as UTC."""
        naive_now = datetime(2025, 6, 16, 10, 0, 15)  # no tzinfo
        task = _make_task({"minute": "*", "hour": "*"}, last_run=naive_now)
        assert task.check_schedule() is False

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)
    def test_no_last_run_is_due(self):
        """Task with no prior run should be due when cron matches."""
        task = _make_task({"minute": "0", "hour": "10"})
        assert task.check_schedule() is True

    def test_returns_false_when_crontab_unavailable(self):
        """check_schedule returns False when CronTab is None."""
        task = _make_task({"minute": "*", "hour": "*"})
        with patch("python.helpers.task_scheduler.CronTab", None):
            assert task.check_schedule() is False


# ---------------------------------------------------------------------------
# TestGetDueTasks
# ---------------------------------------------------------------------------


class TestGetDueTasks:
    """Tests for SchedulerTaskList.get_due_tasks() filtering."""

    @staticmethod
    def _make_task_list(tasks: list) -> SchedulerTaskList:
        tl = SchedulerTaskList(tasks=tasks)
        # SchedulerTaskList is a Pydantic model — use object.__setattr__ to bypass validation
        object.__setattr__(tl, "reload", AsyncMock(return_value=tl))
        object.__setattr__(tl, "save", AsyncMock(return_value=tl))
        return tl

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)  # Monday
    def test_returns_idle_matching_tasks(self):
        t = _make_task({"minute": "0", "hour": "10"}, state=TaskState.IDLE)
        tl = self._make_task_list([t])
        due = asyncio.get_event_loop().run_until_complete(tl.get_due_tasks())
        assert len(due) == 1
        assert due[0].name == "test-task"

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)
    def test_skips_running_tasks(self):
        t = _make_task({"minute": "0", "hour": "10"}, state=TaskState.RUNNING)
        tl = self._make_task_list([t])
        due = asyncio.get_event_loop().run_until_complete(tl.get_due_tasks())
        assert len(due) == 0

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)
    def test_skips_error_tasks(self):
        t = _make_task({"minute": "0", "hour": "10"}, state=TaskState.ERROR)
        tl = self._make_task_list([t])
        due = asyncio.get_event_loop().run_until_complete(tl.get_due_tasks())
        assert len(due) == 0

    def test_empty_list_returns_empty(self):
        tl = self._make_task_list([])
        due = asyncio.get_event_loop().run_until_complete(tl.get_due_tasks())
        assert due == []

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)
    def test_multiple_due_tasks(self):
        t1 = _make_task({"minute": "0", "hour": "10"}, name="task-a")
        t2 = _make_task({"minute": "0", "hour": "10"}, name="task-b")
        t3 = _make_task({"minute": "30", "hour": "10"}, name="task-c")  # not due
        tl = self._make_task_list([t1, t2, t3])
        due = asyncio.get_event_loop().run_until_complete(tl.get_due_tasks())
        names = {t.name for t in due}
        assert names == {"task-a", "task-b"}


# ---------------------------------------------------------------------------
# TestTaskStateMachine
# ---------------------------------------------------------------------------


class TestTaskStateMachine:
    """Tests for task state transitions via update()."""

    def test_idle_to_running(self):
        task = _make_task({"minute": "*"}, state=TaskState.IDLE)
        task.update(state=TaskState.RUNNING)
        assert task.state == TaskState.RUNNING

    def test_running_to_idle_on_success(self):
        task = _make_task({"minute": "*"}, state=TaskState.RUNNING)
        task.update(state=TaskState.IDLE)
        assert task.state == TaskState.IDLE

    def test_running_to_error(self):
        task = _make_task({"minute": "*"}, state=TaskState.RUNNING)
        task.update(state=TaskState.ERROR)
        assert task.state == TaskState.ERROR

    @freeze_time("2025-06-16 10:00:30", tz_offset=0)
    def test_running_task_not_due(self):
        """A RUNNING task matching the cron is NOT returned by get_due_tasks."""
        t = _make_task({"minute": "0", "hour": "10"}, state=TaskState.RUNNING)
        tl = SchedulerTaskList(tasks=[t])
        object.__setattr__(tl, "reload", AsyncMock(return_value=tl))
        due = asyncio.get_event_loop().run_until_complete(tl.get_due_tasks())
        assert len(due) == 0


# ---------------------------------------------------------------------------
# TestSeedAndTick
# ---------------------------------------------------------------------------


class TestSeedAndTick:
    """Integration: seeded MOS tasks + tick at specific times."""

    @staticmethod
    def _build_mos_tasks() -> list[ScheduledTask]:
        from python.helpers.mos_scheduler_init import _MOS_TASKS

        tasks = []
        for defn in _MOS_TASKS:
            sched = TaskSchedule(**defn["schedule"], timezone="UTC")
            task = ScheduledTask(
                name=defn["name"],
                system_prompt="mos",
                prompt=defn["prompt"],
                schedule=sched,
            )
            tasks.append(task)
        return tasks

    def test_all_seeded_tasks_start_idle(self):
        for t in self._build_mos_tasks():
            assert t.state == TaskState.IDLE

    @freeze_time("2025-06-16 08:00:30", tz_offset=0)  # Monday 08:00 UTC
    def test_linear_to_motion_due_weekday_8am(self):
        tasks = self._build_mos_tasks()
        lt = next(t for t in tasks if t.name == "mos-linear-to-motion")
        assert lt.check_schedule() is True

    @freeze_time("2025-06-14 08:00:30", tz_offset=0)  # Saturday 08:00 UTC
    def test_linear_to_motion_not_due_weekend(self):
        tasks = self._build_mos_tasks()
        lt = next(t for t in tasks if t.name == "mos-linear-to-motion")
        assert lt.check_schedule() is False

    @freeze_time("2025-06-16 06:00:30", tz_offset=0)  # Monday 06:00 UTC
    def test_linear_activity_digest_due_6am(self):
        tasks = self._build_mos_tasks()
        digest = next(t for t in tasks if t.name == "mos-linear-activity-digest")
        assert digest.check_schedule() is True

    @freeze_time("2025-06-16 07:00:30", tz_offset=0)
    def test_analytics_digest_due_7am(self):
        tasks = self._build_mos_tasks()
        ad = next(t for t in tasks if t.name == "mos-analytics-daily-digest")
        assert ad.check_schedule() is True

    @freeze_time("2025-06-16 11:00:30", tz_offset=0)
    def test_support_queue_due_hourly(self):
        tasks = self._build_mos_tasks()
        sq = next(t for t in tasks if t.name == "mos-support-queue-check")
        assert sq.check_schedule() is True
