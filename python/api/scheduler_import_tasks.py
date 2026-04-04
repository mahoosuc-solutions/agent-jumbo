"""Bulk-import scheduler task definitions.

Accepts a list of task definition objects and creates any that don't already
exist (matched by name). Useful for seeding pre-built workflow bundles such as
the WBM recurring operations tasks from the onboarding guide.
"""

from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers.localization import Localization


class SchedulerImportTasks(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        try:
            from python.helpers.task_scheduler import (
                AdHocTask,
                PlannedTask,
                ScheduledTask,
                TaskSchedule,
                TaskScheduler,
                parse_task_plan,
                parse_task_schedule,
            )
        except ImportError as e:
            return {"ok": False, "error": f"Scheduler not available: {e}"}

        task_definitions = input.get("task_definitions", [])
        if not isinstance(task_definitions, list) or not task_definitions:
            return {"ok": False, "error": "task_definitions must be a non-empty array"}

        if timezone := input.get("timezone"):
            Localization.get().set_timezone(timezone)

        scheduler = TaskScheduler.get()
        await scheduler.reload()

        # Build name index of existing tasks for deduplication
        existing_names = {t.name for t in scheduler.get_tasks()}

        imported: list[str] = []
        skipped: list[str] = []
        failed: list[dict] = []

        for defn in task_definitions:
            name = defn.get("name", "").strip()
            if not name:
                failed.append({"name": "", "error": "missing name"})
                continue

            if name in existing_names:
                skipped.append(name)
                continue

            prompt = defn.get("prompt", "").strip()
            if not prompt:
                failed.append({"name": name, "error": "missing prompt"})
                continue

            system_prompt = defn.get("system_prompt", "")
            attachments = defn.get("attachments", [])
            project_name = defn.get("project_name") or None
            project_color = defn.get("project_color") or None
            tz = defn.get("timezone") or timezone or None

            try:
                schedule = defn.get("schedule")
                plan = defn.get("plan")

                if schedule:
                    task_schedule: TaskSchedule
                    if isinstance(schedule, str):
                        parts = schedule.split()
                        task_schedule = TaskSchedule(
                            minute=parts[0] if len(parts) > 0 else "*",
                            hour=parts[1] if len(parts) > 1 else "*",
                            day=parts[2] if len(parts) > 2 else "*",
                            month=parts[3] if len(parts) > 3 else "*",
                            weekday=parts[4] if len(parts) > 4 else "*",
                        )
                    else:
                        task_schedule = parse_task_schedule(schedule)

                    task = ScheduledTask.create(
                        name=name,
                        system_prompt=system_prompt,
                        prompt=prompt,
                        schedule=task_schedule,
                        attachments=attachments,
                        context_id=None,
                        timezone=tz,
                        project_name=project_name,
                        project_color=project_color,
                    )
                elif plan:
                    task_plan = parse_task_plan(plan)
                    task = PlannedTask.create(
                        name=name,
                        system_prompt=system_prompt,
                        prompt=prompt,
                        plan=task_plan,
                        attachments=attachments,
                        context_id=None,
                        project_name=project_name,
                        project_color=project_color,
                    )
                else:
                    import random

                    task = AdHocTask.create(
                        name=name,
                        system_prompt=system_prompt,
                        prompt=prompt,
                        token=str(random.randint(10**18, 10**19 - 1)),
                        attachments=attachments,
                        context_id=None,
                        project_name=project_name,
                        project_color=project_color,
                    )

                await scheduler.add_task(task)
                existing_names.add(name)
                imported.append(name)

            except Exception as exc:
                failed.append({"name": name, "error": str(exc)})

        return {
            "ok": True,
            "imported": len(imported),
            "skipped": len(skipped),
            "failed": len(failed),
            "imported_names": imported,
            "skipped_names": skipped,
            "failed_details": failed,
        }
