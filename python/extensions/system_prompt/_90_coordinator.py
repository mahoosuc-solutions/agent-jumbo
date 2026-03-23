"""Inject multi-LLM coordinator awareness into the system prompt."""

from typing import Any

from agent import LoopData
from python.helpers.extension import Extension

COORDINATOR_CONTEXT = """
## Multi-LLM Coordination

You have access to a `coordinator` tool that can decompose complex tasks and dispatch them to multiple LLM providers concurrently.

Use the coordinator tool when:
- A task has multiple independent parts that could run in parallel
- Different parts of a task are better suited to different models
- You need to gather information from multiple sources simultaneously

Available actions:
- `decompose`: Preview how a task would be split into subtasks
- `dispatch`: Execute a task with multi-LLM coordination
- `classify`: Check which provider would be best for a specific prompt
- `provider_health`: Check which providers are available and healthy
- `cost_report`: View spending by provider

Provider strengths:
- **Anthropic (Claude)**: Complex reasoning, code generation, creative writing
- **Google (Gemini)**: Speed, vision, long context, data extraction
- **Ollama (local)**: Privacy, no cost, simple tasks
"""


class CoordinatorPrompt(Extension):
    async def execute(self, system_prompt: list[str] | None = None, loop_data: LoopData = LoopData(), **kwargs: Any):
        if system_prompt is None:
            return

        # Only inject when the agent has a valid context
        if not getattr(self.agent, "context", None):
            return

        system_prompt.append(COORDINATOR_CONTEXT)
