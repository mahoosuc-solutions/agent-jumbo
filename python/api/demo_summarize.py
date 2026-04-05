"""
Public demo document summarizer — no auth, rate-limited to 3 summaries per session.
"""

import os

from flask import session

import models
from python.helpers.api import ApiHandler
from python.helpers.settings import get_settings

_MAX_USES = 3
_SESSION_KEY = "demo_summarize_uses"
_MAX_INPUT_CHARS = 8000
_SYSTEM = (
    "You are a document analysis assistant. "
    "Given a document or text excerpt, produce a structured summary with: "
    "1) a one-sentence TL;DR, "
    "2) 3-5 key points as bullet items, "
    "3) any action items or decisions if present. "
    "Be concise. Plain text output only, no markdown headers."
)


class DemoSummarizeEndpoint(ApiHandler):
    async def process(self, input: dict, files: list) -> dict:
        text = (input.get("text") or "").strip()

        if not text:
            return {"error": "text is required"}, 400  # type: ignore[return-value]

        uses = session.get(_SESSION_KEY, 0)
        if uses >= _MAX_USES:
            return {
                "error": "demo_limit_reached",
                "message": f"You've reached the {_MAX_USES}-summary demo limit.",
                "cta": {"label": "Start Free — no credit card", "href": "/signup"},
            }, 429  # type: ignore[return-value]

        # Truncate oversized input
        if len(text) > _MAX_INPUT_CHARS:
            text = text[:_MAX_INPUT_CHARS] + "\n\n[...truncated for demo — full platform processes unlimited length]"

        summary = await self._summarize(text)
        session[_SESSION_KEY] = uses + 1
        session.modified = True

        return {
            "summary": summary,
            "uses_remaining": max(0, _MAX_USES - uses - 1),
            "char_count": len(text),
        }

    async def _summarize(self, text: str) -> str:
        try:
            s = get_settings()
            chat_model = models.get_chat_model(
                provider=os.environ.get("DEMO_MODEL_PROVIDER", s.get("chat_model_provider", "ollama")),
                name=os.environ.get("DEMO_MODEL_NAME", s.get("chat_model_name", "qwen2.5:3b")),
            )
            result, _ = await chat_model.unified_call(
                system_message=_SYSTEM,
                user_message=f"Please summarize the following:\n\n{text}",
                max_tokens=400,
            )
            return result
        except Exception as exc:
            return (
                f"Summary unavailable (LLM offline: {exc!s}). "
                "In a live deployment the AI Document Processing instrument "
                "handles full pipelines: extract → classify → summarize → route."
            )
