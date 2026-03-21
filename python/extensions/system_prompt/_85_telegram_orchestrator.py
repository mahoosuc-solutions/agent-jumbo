"""Inject Telegram orchestrator system prompt for Telegram-originated conversations."""

import os
from typing import Any

from agent import LoopData
from python.helpers.extension import Extension


class TelegramOrchestratorPrompt(Extension):
    async def execute(self, system_prompt: list[str] | None = None, loop_data: LoopData = LoopData(), **kwargs: Any):
        if system_prompt is None:
            return

        context = self.agent.context
        if not context:
            return

        # Check if this is a Telegram context
        ctx_id = context.id or ""
        is_telegram = ctx_id.startswith("telegram-")

        # Also check shared context mode
        if not is_telegram:
            shared = os.getenv("TELEGRAM_AGENT_CONTEXT", "")
            if shared and ctx_id == shared:
                is_telegram = True

        if not is_telegram:
            return

        # Inject the orchestrator prompt
        try:
            prompt_content = self.agent.read_prompt("agent.system.telegram_orchestrator.md")
            if prompt_content:
                system_prompt.append(prompt_content)
        except Exception:
            pass
