"""
Task Planner Tool — in-monologue task management for complex multi-step work.

Instead of delegating to subordinate agents, the agent decomposes a task
into numbered steps, executes them sequentially within its own monologue
loop, and tracks progress via extras_persistent (visible every iteration).
"""

from __future__ import annotations

import json

from python.helpers.tool import Response, Tool


class TaskPlanner(Tool):
    """Manage a step-by-step task plan within the current conversation."""

    async def execute(self, **kwargs):
        action = (self.args.get("action") or "").lower()
        actions = {
            "create_plan": self._create_plan,
            "update_step": self._update_step,
            "get_progress": self._get_progress,
            "add_step": self._add_step,
        }
        handler = actions.get(action)
        if handler:
            return await handler()
        return Response(message=self._format_help(), break_loop=False)

    async def _create_plan(self) -> Response:
        """Create a numbered plan from a list of step descriptions."""
        steps = self.args.get("steps", [])
        if isinstance(steps, str):
            # Handle comma-separated or newline-separated strings
            steps = [s.strip() for s in steps.replace("\n", ",").split(",") if s.strip()]

        if not steps:
            return Response(
                message="Please provide a list of steps. Example: steps=['Research X', 'Analyze Y', 'Write report']",
                break_loop=False,
            )

        plan = {
            "total": len(steps),
            "completed": 0,
            "failed": 0,
            "steps": [
                {"number": i + 1, "description": s, "status": "pending", "result": ""} for i, s in enumerate(steps)
            ],
        }

        # Store in agent data (survives across iterations)
        self.agent.data["_task_plan"] = plan

        # Store formatted plan in persistent extras (injected into prompt each iteration)
        if hasattr(self.agent, "loop_data") and self.agent.loop_data:
            self.agent.loop_data.extras_persistent["task_plan"] = self._format_plan(plan)

        return Response(message=self._format_plan(plan), break_loop=False)

    async def _update_step(self) -> Response:
        """Mark a step as done/failed/skipped with a result summary."""
        plan = self.agent.data.get("_task_plan")
        if not plan:
            return Response(message="No task plan exists. Use create_plan first.", break_loop=False)

        step_number = int(self.args.get("step_number", 0))
        status = self.args.get("status", "done").lower()
        result = self.args.get("result", "")

        if step_number < 1 or step_number > plan["total"]:
            return Response(
                message=f"Invalid step number {step_number}. Plan has {plan['total']} steps.",
                break_loop=False,
            )

        step = plan["steps"][step_number - 1]
        old_status = step["status"]
        step["status"] = status
        step["result"] = result[:500]  # Cap result length

        # Update counters
        if status == "done" and old_status != "done":
            plan["completed"] += 1
        elif status == "failed" and old_status != "failed":
            plan["failed"] += 1

        # Update stored plan
        self.agent.data["_task_plan"] = plan
        if hasattr(self.agent, "loop_data") and self.agent.loop_data:
            self.agent.loop_data.extras_persistent["task_plan"] = self._format_plan(plan)

        # Check if all steps are done
        all_done = all(s["status"] in ("done", "failed", "skipped") for s in plan["steps"])
        completion_msg = ""
        if all_done:
            completion_msg = (
                f"\n\nAll steps complete ({plan['completed']} done, {plan['failed']} failed). "
                f"Use the response tool to deliver the final result to the user."
            )

        return Response(
            message=self._format_plan(plan) + completion_msg,
            break_loop=False,
        )

    async def _add_step(self) -> Response:
        """Add a new step to an existing plan."""
        plan = self.agent.data.get("_task_plan")
        if not plan:
            return Response(message="No task plan exists. Use create_plan first.", break_loop=False)

        description = self.args.get("description", "")
        if not description:
            return Response(message="Please provide a step description.", break_loop=False)

        new_step = {
            "number": plan["total"] + 1,
            "description": description,
            "status": "pending",
            "result": "",
        }
        plan["steps"].append(new_step)
        plan["total"] += 1

        self.agent.data["_task_plan"] = plan
        if hasattr(self.agent, "loop_data") and self.agent.loop_data:
            self.agent.loop_data.extras_persistent["task_plan"] = self._format_plan(plan)

        return Response(message=self._format_plan(plan), break_loop=False)

    async def _get_progress(self) -> Response:
        """Show current plan status."""
        plan = self.agent.data.get("_task_plan")
        if not plan:
            return Response(message="No task plan exists.", break_loop=False)
        return Response(message=self._format_plan(plan), break_loop=False)

    @staticmethod
    def _format_plan(plan: dict) -> str:
        """Format the plan as a readable checklist."""
        icons = {"pending": "[ ]", "done": "[x]", "failed": "[!]", "skipped": "[-]"}
        lines = [
            f"Task Plan ({plan['completed']}/{plan['total']} complete"
            + (f", {plan['failed']} failed" if plan.get("failed") else "")
            + "):\n"
        ]
        for step in plan["steps"]:
            icon = icons.get(step["status"], "[ ]")
            lines.append(f"{icon} Step {step['number']}: {step['description']}")
            if step["result"]:
                # Indent result, truncate for readability
                result_preview = step["result"][:200]
                lines.append(f"     Result: {result_preview}")
        return "\n".join(lines)

    @staticmethod
    def _format_help() -> str:
        return json.dumps(
            {
                "tool": "task_planner",
                "description": "Manage a step-by-step plan for complex tasks",
                "actions": {
                    "create_plan": "Create a plan. Args: steps (list of step descriptions)",
                    "update_step": "Update a step. Args: step_number, status (done/failed/skipped), result",
                    "add_step": "Add a step. Args: description",
                    "get_progress": "Show current plan status",
                },
                "workflow": "create_plan → execute steps with other tools → update_step after each → response when done",
            },
            indent=2,
        )
