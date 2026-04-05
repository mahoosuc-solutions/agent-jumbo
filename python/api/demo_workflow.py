"""
Public demo workflow visualizer — given a goal, return an AI-generated workflow plan.
No auth, limited to 3 plans per session.
"""

import os

from flask import session

import models
from python.helpers.api import ApiHandler
from python.helpers.settings import get_settings

_MAX_USES = 3
_SESSION_KEY = "demo_workflow_uses"
_SYSTEM = """You are a workflow planning assistant for the Mahoosuc OS AI orchestration platform.
Given a business goal, produce a clear multi-step agent workflow plan in JSON format.

Respond with valid JSON only — no prose, no markdown fences.

Schema:
{
  "goal": "<restated goal>",
  "steps": [
    {
      "id": 1,
      "title": "<step title>",
      "agent_role": "<what the agent does>",
      "instrument": "<instrument name e.g. customer_lifecycle, stripe_payments, email>",
      "inputs": ["<input 1>"],
      "outputs": ["<output 1>"],
      "human_review": false
    }
  ],
  "estimated_runtime": "<e.g. 2-5 minutes>",
  "requires_human_review": false
}

Use 4-8 steps. Reference real Mahoosuc OS instruments where relevant:
customer_lifecycle, stripe_payments, knowledge_base, scheduler, email,
google_voice, telegram, linear_tasks, document_processor, web_browser."""


class DemoWorkflowEndpoint(ApiHandler):
    async def process(self, input: dict, files: list) -> dict:
        goal = (input.get("goal") or "").strip()

        if not goal:
            return {"error": "goal is required"}, 400  # type: ignore[return-value]

        if len(goal) > 500:
            goal = goal[:500]

        uses = session.get(_SESSION_KEY, 0)
        if uses >= _MAX_USES:
            return {
                "error": "demo_limit_reached",
                "message": f"You've reached the {_MAX_USES}-workflow demo limit.",
                "cta": {"label": "Start Free — no credit card", "href": "/signup"},
            }, 429  # type: ignore[return-value]

        plan = await self._plan(goal)
        session[_SESSION_KEY] = uses + 1
        session.modified = True

        return {
            "plan": plan,
            "uses_remaining": max(0, _MAX_USES - uses - 1),
        }

    async def _plan(self, goal: str) -> dict:
        import json

        try:
            s = get_settings()
            chat_model = models.get_chat_model(
                provider=os.environ.get("DEMO_MODEL_PROVIDER", s.get("chat_model_provider", "ollama")),
                name=os.environ.get("DEMO_MODEL_NAME", s.get("chat_model_name", "qwen2.5:3b")),
            )
            raw, _ = await chat_model.unified_call(
                system_message=_SYSTEM,
                user_message=f"Goal: {goal}",
                max_tokens=800,
            )
            # Strip any accidental markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception as exc:
            # Return a canned fallback plan so the UI always renders something
            return {
                "goal": goal,
                "steps": [
                    {
                        "id": 1,
                        "title": "Ingest goal context",
                        "agent_role": "Extract structured requirements from the goal",
                        "instrument": "knowledge_base",
                        "inputs": ["raw goal text"],
                        "outputs": ["structured requirements"],
                        "human_review": False,
                    },
                    {
                        "id": 2,
                        "title": "Route to appropriate instrument",
                        "agent_role": "Select the best instrument chain for the task",
                        "instrument": "scheduler",
                        "inputs": ["structured requirements"],
                        "outputs": ["instrument execution plan"],
                        "human_review": False,
                    },
                    {
                        "id": 3,
                        "title": "Execute and report",
                        "agent_role": "Run the plan and return results",
                        "instrument": "customer_lifecycle",
                        "inputs": ["execution plan"],
                        "outputs": ["completion report"],
                        "human_review": True,
                    },
                ],
                "estimated_runtime": "2-5 minutes",
                "requires_human_review": True,
                "_note": f"Live LLM offline ({exc!s}); showing example plan.",
            }
