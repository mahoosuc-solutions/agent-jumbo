"""Task Decomposer — breaks complex prompts into provider-optimized subtasks."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class SubTaskType(Enum):
    RESEARCH = "research"  # Gather information — fast model
    ANALYZE = "analyze"  # Deep reasoning — strong model
    GENERATE = "generate"  # Produce content/code — specialized model
    VALIDATE = "validate"  # Check/test results — any model
    SYNTHESIZE = "synthesize"  # Combine results — strong model


@dataclass
class SubTask:
    id: str
    type: SubTaskType
    prompt: str
    recommended_provider: str  # google, anthropic, openai, ollama
    recommended_model: str | None = None
    priority: int = 1  # 1=highest
    dependencies: list[str] = field(default_factory=list)  # IDs of tasks this depends on
    result: str | None = None
    status: str = "pending"  # pending, running, completed, failed
    cost_cents: float = 0.0
    latency_ms: float = 0.0


class TaskClassifier:
    """Classifies prompts to determine optimal LLM provider."""

    # Keyword patterns mapped to (task_type, provider, reason)
    PATTERNS = {
        # Research patterns → fast model (Gemini Flash)
        r"\b(search|find|look up|list|enumerate|what is|who is|when did)\b": (
            SubTaskType.RESEARCH,
            "google",
            "Fast retrieval",
        ),
        # Analysis patterns → strong model (Claude)
        r"\b(analyze|evaluate|compare|assess|review|critique|reason|think through|explain why)\b": (
            SubTaskType.ANALYZE,
            "anthropic",
            "Deep reasoning",
        ),
        # Code generation → Claude/Codex
        r"\b(implement|code|program|write.*function|create.*class|build.*api|debug|fix.*bug|refactor)\b": (
            SubTaskType.GENERATE,
            "anthropic",
            "Code quality",
        ),
        # Creative writing → Claude
        r"\b(write|draft|compose|blog|article|story|email|proposal|documentation)\b": (
            SubTaskType.GENERATE,
            "anthropic",
            "Creative voice",
        ),
        # Data/extraction → Gemini (fast structured output)
        r"\b(extract|parse|classify|categorize|summarize|convert|transform|format)\b": (
            SubTaskType.RESEARCH,
            "google",
            "Fast extraction",
        ),
        # Validation → any fast model
        r"\b(verify|validate|check|test|confirm|audit)\b": (
            SubTaskType.VALIDATE,
            "google",
            "Fast validation",
        ),
        # Vision → Gemini
        r"\b(image|screenshot|photo|diagram|visual|look at|see)\b": (
            SubTaskType.ANALYZE,
            "google",
            "Vision capability",
        ),
        # Long context → Gemini 1.5 Pro
        r"\b(entire file|full document|whole codebase|all of|everything in)\b": (
            SubTaskType.ANALYZE,
            "google",
            "Long context window",
        ),
    }

    @classmethod
    def classify(cls, prompt: str) -> tuple[SubTaskType, str, str]:
        """Classify a prompt. Returns (task_type, recommended_provider, reason)."""
        prompt_lower = prompt.lower()
        for pattern, (task_type, provider, reason) in cls.PATTERNS.items():
            if re.search(pattern, prompt_lower):
                return task_type, provider, reason
        return SubTaskType.GENERATE, "anthropic", "Default (general task)"


class TaskDecomposer:
    """Decomposes complex tasks into parallelizable subtasks."""

    def decompose_simple(self, prompt: str) -> list[SubTask]:
        """Simple decomposition using keyword analysis.
        Returns a single subtask for simple prompts, multiple for complex ones."""
        task_type, provider, _reason = TaskClassifier.classify(prompt)

        # Check for multi-part indicators
        parts = self._detect_parts(prompt)

        if len(parts) <= 1:
            return [
                SubTask(
                    id="task_0",
                    type=task_type,
                    prompt=prompt,
                    recommended_provider=provider,
                    priority=1,
                )
            ]

        subtasks = []
        for i, part in enumerate(parts):
            part_type, part_provider, _ = TaskClassifier.classify(part)
            subtasks.append(
                SubTask(
                    id=f"task_{i}",
                    type=part_type,
                    prompt=part.strip(),
                    recommended_provider=part_provider,
                    priority=i + 1,
                )
            )

        # Add synthesis task that depends on all others
        subtasks.append(
            SubTask(
                id=f"task_{len(subtasks)}",
                type=SubTaskType.SYNTHESIZE,
                prompt=f"Synthesize the results of the previous {len(parts)} subtasks into a coherent response to: {prompt}",
                recommended_provider="anthropic",
                priority=len(subtasks) + 1,
                dependencies=[st.id for st in subtasks],
            )
        )

        return subtasks

    def _detect_parts(self, prompt: str) -> list[str]:
        """Detect multi-part structure in a prompt."""
        # Check for numbered lists
        numbered = re.findall(r"(?:^|\n)\s*\d+[.)]\s*(.+)", prompt)
        if len(numbered) >= 2:
            return numbered

        # Check for "and then", "also", "additionally" connectors
        connectors = re.split(
            r"\.\s*(?:Then|Also|Additionally|Next|After that|Finally)\s+",
            prompt,
            flags=re.IGNORECASE,
        )
        if len(connectors) >= 2:
            return connectors

        # Check for semicolons or " and " separating distinct tasks
        if "; " in prompt:
            parts = prompt.split("; ")
            if len(parts) >= 2:
                return parts

        return [prompt]
