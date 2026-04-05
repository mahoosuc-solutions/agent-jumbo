"""
_25_load_work_context — inject persistent work context into agent system prompt.

Runs at agent initialization. Reads agent_journal.db to:
1. Mark any interrupted sessions from previous runs
2. Build a startup context summary (recent work, goals, interrupted tasks)
3. Make it available as {work_context} in the system prompt
"""

from __future__ import annotations

from python.helpers.extension import Extension


class LoadWorkContext(Extension):
    async def execute(self, **kwargs):
        try:
            from python.helpers import agent_journal

            ctx_id = getattr(self.agent, "id", "") or ""
            project_name = getattr(getattr(self.agent, "active_project", None), "name", None)

            # Mark any sessions from a previous run of this context as interrupted
            if ctx_id:
                agent_journal.mark_interrupted_sessions(ctx_id)

            # Build context summary and inject as a prompt variable
            context_md = agent_journal.build_startup_context(project_name)
            if context_md.strip() and hasattr(self.agent, "data"):
                self.agent.data["work_context"] = context_md

        except Exception:
            # Never block agent startup
            pass
