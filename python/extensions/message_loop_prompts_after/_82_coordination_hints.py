"""Coordination Hints — injects multi-LLM dispatch guidance into the agent context.

Runs after prompt enhancement (_80). Analyzes the user prompt for
multi-part structure and complexity signals. When detected, adds a
temporary hint instructing the agent to use the coordinator tool
for parallel multi-LLM execution.

This is a lightweight, loosely-coupled bridge between prompt processing
and the orchestration engine — the coordinator tool and task decomposer
do the heavy lifting.
"""

from __future__ import annotations

import re

from agent import LoopData
from python.helpers.extension import Extension

# Signals that a prompt would benefit from multi-LLM coordination
_COMPLEXITY_PATTERNS = [
    # Multi-part structure
    (r"(?:^|\n)\s*\d+[.)]\s*.+(?:\n\s*\d+[.)]\s*.+){1,}", "numbered_list"),
    (r"(?:^|\n)\s*[-*]\s*.+(?:\n\s*[-*]\s*.+){2,}", "bullet_list"),
    # Transition words joining distinct tasks
    (
        r"\b(?:then|also|additionally|next|after that|finally|meanwhile)\b.*\b(?:then|also|additionally|next|after that|finally|meanwhile)\b",
        "transitions",
    ),
    # Explicit multi-task language
    (r"\b(?:first|second|third)\b.*\b(?:second|third|fourth)\b", "ordinals"),
    # Research + action combinations
    (
        r"\b(?:research|find|look up|search)\b.*\b(?:write|create|build|implement|generate|draft)\b",
        "research_then_create",
    ),
    # Analysis + synthesis
    (r"\b(?:analyze|compare|evaluate)\b.*\b(?:summarize|recommend|suggest|propose)\b", "analyze_then_synthesize"),
]

# Minimum prompt length to consider for coordination (short prompts are never complex)
_MIN_PROMPT_LENGTH = 80


class CoordinationHints(Extension):
    """Injects coordination hints when multi-part tasks are detected."""

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs):
        # Only run on first iteration (don't re-hint on tool-call loops)
        if loop_data.iteration > 1:
            return

        if not loop_data.user_message:
            return

        user_text = loop_data.user_message.output_text()
        if not user_text or len(user_text) < _MIN_PROMPT_LENGTH:
            return

        # Already hinted this turn
        if loop_data.params_temporary.get("coordination_hinted"):
            return

        # Detect complexity
        signals = self._detect_complexity(user_text)
        if not signals:
            return

        # Build the hint
        signal_summary = ", ".join(signals)
        hint = (
            f"\n[Coordination hint: This request shows multi-part structure "
            f"({signal_summary}). Consider using the `coordinator` tool with "
            f"action `dispatch` to execute subtasks concurrently across "
            f"different LLM providers for faster, higher-quality results. "
            f"Use action `decompose` first to preview the task breakdown.]"
        )

        loop_data.extras_temporary["coordination_hint"] = hint
        loop_data.params_temporary["coordination_hinted"] = True

        self.agent.context.log.log(
            type="info",
            heading="Coordination hint injected",
            content=f"Detected complexity signals: {signal_summary}",
        )

    def _detect_complexity(self, text: str) -> list[str]:
        """Return list of complexity signal names detected in the prompt."""
        signals = []
        text_lower = text.lower()
        for pattern, name in _COMPLEXITY_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL):
                signals.append(name)
        return signals
