"""
Public demo chat endpoint — rate-limited, no auth required, max 5 turns per session.
"""

import os

from flask import session

import models
from python.helpers.api import ApiHandler
from python.helpers.settings import get_settings

_MAX_TURNS = 5
_SESSION_KEY = "demo_chat_turns"
_DEMO_SYSTEM = (
    "You are a helpful assistant demonstrating the Mahoosuc OS AI orchestration platform. "
    "Be concise, friendly, and showcase the platform's capabilities when relevant. "
    "If asked to do something complex, briefly explain what the full platform can do. "
    "Keep responses under 200 words."
)


class DemoChatEndpoint(ApiHandler):
    async def process(self, input: dict, files: list) -> dict:
        message = (input.get("message") or "").strip()
        history = input.get("history") or []

        if not message:
            return {"error": "message is required"}, 400  # type: ignore[return-value]

        turns_used = session.get(_SESSION_KEY, 0)
        if turns_used >= _MAX_TURNS:
            return {
                "error": "demo_limit_reached",
                "message": f"You've reached the {_MAX_TURNS}-message demo limit.",
                "cta": {"label": "Start Free — no credit card", "href": "/signup"},
            }, 429  # type: ignore[return-value]

        reply = await self._call_llm(message, history)
        session[_SESSION_KEY] = turns_used + 1
        session.modified = True

        return {
            "reply": reply,
            "turns_used": turns_used + 1,
            "turns_remaining": max(0, _MAX_TURNS - turns_used - 1),
        }

    async def _call_llm(self, message: str, history: list) -> str:
        try:
            s = get_settings()
            chat_model = models.get_chat_model(
                provider=os.environ.get("DEMO_MODEL_PROVIDER", s.get("chat_model_provider", "ollama")),
                name=os.environ.get("DEMO_MODEL_NAME", s.get("chat_model_name", "qwen2.5:3b")),
            )
            # Build langchain message list from history
            from langchain_core.messages import AIMessage, HumanMessage

            lc_messages = []
            for turn in history[-8:]:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role == "user" and content:
                    lc_messages.append(HumanMessage(content=content))
                elif role == "assistant" and content:
                    lc_messages.append(AIMessage(content=content))

            text, _ = await chat_model.unified_call(
                system_message=_DEMO_SYSTEM,
                user_message=message,
                messages=lc_messages,
                max_tokens=300,
            )
            return text
        except Exception as exc:
            return (
                "I'm the Mahoosuc OS demo assistant. "
                f"(LLM unavailable in this environment: {exc!s}.) "
                "In a live deployment this routes through 18 cloud providers and local Ollama models."
            )
