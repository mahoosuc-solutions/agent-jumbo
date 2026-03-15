"""
Ralph Loop Manager

Business logic for Ralph Loop autonomous iteration management.
Integrates with workflow engine for task-based loops.
"""

import re

from .ralph_db import RalphLoopDatabase


class RalphLoopManager:
    """Manager for Ralph Loop operations."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            from python.helpers import files

            db_path = files.get_abs_path("./instruments/custom/ralph_loop/data/ralph_loop.db")
        self.db = RalphLoopDatabase(db_path)

    # ==================== LOOP LIFECYCLE ====================

    def start_loop(
        self,
        prompt: str,
        name: str | None = None,
        completion_promise: str | None = None,
        max_iterations: int = 50,
        agent_id: str | None = None,
        workflow_execution_id: int | None = None,
        task_id: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """
        Start a new Ralph loop.

        Returns dict with loop_id and initial status.
        """
        # Check for existing active loop for this agent
        if agent_id:
            existing = self.db.get_active_loop(agent_id)
            if existing:
                return {
                    "error": f"Agent already has an active loop (ID: {existing['loop_id']}). "
                    "Cancel it first with cancel_loop action.",
                    "existing_loop_id": existing["loop_id"],
                }

        loop_id = self.db.create_loop(
            prompt=prompt,
            name=name,
            completion_promise=completion_promise,
            max_iterations=max_iterations,
            agent_id=agent_id,
            workflow_execution_id=workflow_execution_id,
            task_id=task_id,
            context=context,
        )

        # Create first iteration record
        self.db.create_iteration(loop_id=loop_id, iteration_number=1)

        return {
            "loop_id": loop_id,
            "name": name or "Ralph Loop",
            "status": "active",
            "current_iteration": 1,
            "max_iterations": max_iterations,
            "completion_promise": completion_promise,
        }

    def get_status(self, loop_id: int) -> dict:
        """Get current status of a loop."""
        loop = self.db.get_loop(loop_id)
        if not loop:
            return {"error": f"Loop {loop_id} not found"}

        iterations = self.db.get_iterations(loop_id)

        return {
            "loop_id": loop["loop_id"],
            "name": loop["name"],
            "status": loop["status"],
            "current_iteration": loop["current_iteration"],
            "max_iterations": loop["max_iterations"],
            "completion_promise": loop["completion_promise"],
            "started_at": loop["started_at"],
            "completed_at": loop["completed_at"],
            "iteration_count": len(iterations),
            "workflow_execution_id": loop.get("workflow_execution_id"),
            "task_id": loop.get("task_id"),
        }

    def get_active_loop(self, agent_id: str) -> dict | None:
        """Get the active loop for an agent."""
        return self.db.get_active_loop(agent_id)

    def cancel_loop(self, loop_id: int, reason: str | None = None) -> dict:
        """Cancel an active loop."""
        loop = self.db.get_loop(loop_id)
        if not loop:
            return {"error": f"Loop {loop_id} not found"}

        if loop["status"] != "active":
            return {"error": f"Loop {loop_id} is not active (status: {loop['status']})"}

        self.db.complete_loop(loop_id, status="cancelled")

        return {
            "loop_id": loop_id,
            "status": "cancelled",
            "iterations_completed": loop["current_iteration"],
            "reason": reason or "Manual cancellation",
        }

    def list_loops(self, status: str | None = None, agent_id: str | None = None, limit: int = 50) -> list:
        """List loops with optional filtering."""
        return self.db.list_loops(status=status, agent_id=agent_id, limit=limit)

    # ==================== ITERATION MANAGEMENT ====================

    def check_completion(self, loop_id: int, last_output: str) -> tuple[bool, str]:
        """
        Check if the loop should complete based on output.

        Returns (is_complete, reason) tuple.
        """
        loop = self.db.get_loop(loop_id)
        if not loop:
            return (True, "Loop not found")

        if loop["status"] != "active":
            return (True, f"Loop already {loop['status']}")

        # Check for completion promise in output
        if loop["completion_promise"]:
            promise_pattern = f"<promise>{re.escape(loop['completion_promise'])}</promise>"
            if re.search(promise_pattern, last_output, re.IGNORECASE):
                self.db.complete_loop(loop_id, status="completed")
                return (True, f"Completion promise detected: {loop['completion_promise']}")

        # Check max iterations
        if loop["max_iterations"] > 0:
            if loop["current_iteration"] >= loop["max_iterations"]:
                self.db.complete_loop(loop_id, status="max_iterations")
                return (True, f"Max iterations ({loop['max_iterations']}) reached")

        return (False, "Continue")

    def advance_iteration(
        self,
        loop_id: int,
        output_summary: str | None = None,
        files_modified: list | None = None,
        git_commit: str | None = None,
    ) -> dict:
        """
        Advance to the next iteration.

        Returns the new iteration info or completion status.
        """
        loop = self.db.get_loop(loop_id)
        if not loop:
            return {"error": f"Loop {loop_id} not found"}

        if loop["status"] != "active":
            return {"error": f"Loop is not active (status: {loop['status']})"}

        # Complete current iteration
        latest = self.db.get_latest_iteration(loop_id)
        if latest:
            self.db.complete_iteration(
                iteration_id=latest["iteration_id"],
                output_summary=output_summary,
                files_modified=files_modified,
                git_commit=git_commit,
                success=True,
            )

        # Increment counter
        new_iteration = self.db.increment_iteration(loop_id)

        # Create new iteration record
        self.db.create_iteration(loop_id=loop_id, iteration_number=new_iteration)

        # Update last output
        if output_summary:
            self.db.update_loop(loop_id, last_output=output_summary)

        return {
            "loop_id": loop_id,
            "iteration": new_iteration,
            "max_iterations": loop["max_iterations"],
            "prompt": loop["prompt"],
            "completion_promise": loop["completion_promise"],
        }

    def get_iteration_history(self, loop_id: int) -> list:
        """Get full iteration history for a loop."""
        return self.db.get_iterations(loop_id)

    # ==================== WORKFLOW INTEGRATION ====================

    def start_task_loop(
        self,
        workflow_execution_id: int,
        task_id: str,
        prompt: str,
        name: str | None = None,
        completion_promise: str | None = None,
        max_iterations: int = 30,
        agent_id: str | None = None,
    ) -> dict:
        """Start a Ralph loop for a workflow task."""
        return self.start_loop(
            prompt=prompt,
            name=name or f"Task: {task_id}",
            completion_promise=completion_promise,
            max_iterations=max_iterations,
            agent_id=agent_id,
            workflow_execution_id=workflow_execution_id,
            task_id=task_id,
            context={"source": "workflow", "task_id": task_id},
        )

    def link_to_workflow(self, loop_id: int, workflow_execution_id: int, task_id: str | None = None) -> dict:
        """Link an existing loop to a workflow execution."""
        loop = self.db.get_loop(loop_id)
        if not loop:
            return {"error": f"Loop {loop_id} not found"}

        context = loop.get("context", {})
        context["workflow_execution_id"] = workflow_execution_id
        if task_id:
            context["task_id"] = task_id

        self.db.update_loop(loop_id, context=context)

        return {"loop_id": loop_id, "workflow_execution_id": workflow_execution_id, "task_id": task_id, "linked": True}

    # ==================== CONFIGURATION ====================

    def update_completion_promise(self, loop_id: int, completion_promise: str) -> dict:
        """Update the completion promise for a loop."""
        loop = self.db.get_loop(loop_id)
        if not loop:
            return {"error": f"Loop {loop_id} not found"}

        # Use raw SQL update for this specific field
        import sqlite3

        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute(
                "UPDATE ralph_loops SET completion_promise = ? WHERE loop_id = ?", (completion_promise, loop_id)
            )

        return {"loop_id": loop_id, "completion_promise": completion_promise, "updated": True}

    def update_max_iterations(self, loop_id: int, max_iterations: int) -> dict:
        """Update the max iterations for a loop."""
        loop = self.db.get_loop(loop_id)
        if not loop:
            return {"error": f"Loop {loop_id} not found"}

        import sqlite3

        with sqlite3.connect(self.db.db_path) as conn:
            conn.execute("UPDATE ralph_loops SET max_iterations = ? WHERE loop_id = ?", (max_iterations, loop_id))

        return {"loop_id": loop_id, "max_iterations": max_iterations, "updated": True}

    def pause_loop(self, loop_id: int) -> dict:
        """Pause a loop (can resume later)."""
        loop = self.db.get_loop(loop_id)
        if not loop:
            return {"error": f"Loop {loop_id} not found"}

        if loop["status"] != "active":
            return {"error": f"Can only pause active loops (current: {loop['status']})"}

        self.db.update_loop(loop_id, status="paused")

        return {"loop_id": loop_id, "status": "paused", "current_iteration": loop["current_iteration"]}

    def resume_loop(self, loop_id: int) -> dict:
        """Resume a paused loop."""
        loop = self.db.get_loop(loop_id)
        if not loop:
            return {"error": f"Loop {loop_id} not found"}

        if loop["status"] != "paused":
            return {"error": f"Can only resume paused loops (current: {loop['status']})"}

        self.db.update_loop(loop_id, status="active")

        return {
            "loop_id": loop_id,
            "status": "active",
            "current_iteration": loop["current_iteration"],
            "prompt": loop["prompt"],
            "completion_promise": loop["completion_promise"],
        }

    # ==================== STATISTICS ====================

    def get_stats(self, agent_id: str | None = None) -> dict:
        """Get Ralph loop statistics."""
        return self.db.get_stats(agent_id)

    # ==================== PROMPT GENERATION ====================

    def generate_iteration_prompt(self, loop_id: int) -> str | None:
        """
        Generate the prompt for the next iteration.

        This is used by the extension hook to inject the prompt.
        """
        loop = self.db.get_loop(loop_id)
        if not loop or loop["status"] != "active":
            return None

        prompt_parts = [
            f"🔄 **Ralph Loop - Iteration {loop['current_iteration']}**",
            "",
            f"**Task:** {loop['name']}",
            "",
            "**Instructions:**",
            loop["prompt"],
            "",
        ]

        if loop["completion_promise"]:
            prompt_parts.extend(
                [
                    "**To complete this task:**",
                    f"Output `<promise>{loop['completion_promise']}</promise>` when the task is done.",
                    "",
                    "⚠️ **Important:** Only output the completion promise when the task is "
                    "genuinely complete. Do not lie to exit the loop.",
                    "",
                ]
            )

        prompt_parts.extend(
            [
                "Your previous work is visible in files. Continue iterating until done.",
                f"Iteration {loop['current_iteration']}/{loop['max_iterations'] or '∞'}",
            ]
        )

        return "\n".join(prompt_parts)
