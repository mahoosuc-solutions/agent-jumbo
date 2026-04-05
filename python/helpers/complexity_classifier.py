"""Complexity Classifier — maps task prompts to complexity tiers for model routing.

Mirrors the keyword heuristic pattern from task_decomposer.py:TaskClassifier
but on a different axis: how *hard* is the task, rather than what *type* it is.

Complexity tiers drive model selection in task_cycle.py:
    SIMPLE → lightweight local model (fast, cheap)
    EASY   → mid-tier cloud model (fast, capable)
    MEDIUM → strong model (slower, high quality)
    HARD   → flagship model (most capable, most expensive)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ComplexityTier(Enum):
    SIMPLE = "simple"  # Single lookup / read-only, no state change, ~1 subtask
    EASY = "easy"  # Single file change, clear spec, 1–3 subtasks
    MEDIUM = "medium"  # Multi-file, some ambiguity, 3–8 subtasks
    HARD = "hard"  # Architecture / cross-system / rewrite, 8+ subtasks


# ---------------------------------------------------------------------------
# Model routing table — single source of truth for tier → (provider, model)
# ---------------------------------------------------------------------------

TIER_MODEL_MAP: dict[ComplexityTier, tuple[str, str]] = {
    ComplexityTier.SIMPLE: ("ollama", "llama3.2"),
    ComplexityTier.EASY: ("google", "gemini-2.0-flash"),
    ComplexityTier.MEDIUM: ("anthropic", "claude-sonnet-4-6"),
    ComplexityTier.HARD: ("anthropic", "claude-opus-4-6"),
}

# Estimated token budget per tier (used to size context windows in task_cycle)
TIER_TOKEN_BUDGET: dict[ComplexityTier, int] = {
    ComplexityTier.SIMPLE: 500,
    ComplexityTier.EASY: 2_000,
    ComplexityTier.MEDIUM: 8_000,
    ComplexityTier.HARD: 32_000,
}

# Estimated subtask count range per tier
TIER_SUBTASK_ESTIMATE: dict[ComplexityTier, int] = {
    ComplexityTier.SIMPLE: 1,
    ComplexityTier.EASY: 2,
    ComplexityTier.MEDIUM: 5,
    ComplexityTier.HARD: 10,
}


@dataclass
class ComplexityScore:
    tier: ComplexityTier
    confidence: float  # 0.0–1.0 — how certain the classification is
    estimated_subtasks: int
    token_budget: int
    recommended_provider: str
    recommended_model: str
    reason: str  # human-readable explanation of why this tier was chosen


# ---------------------------------------------------------------------------
# Keyword pattern sets — ordered from most-specific (HARD) to least (SIMPLE)
# The first match wins, so specificity matters.
# ---------------------------------------------------------------------------

# HARD: architecture-level, cross-system, full rewrites
_HARD_PATTERNS = [
    r"\b(architect|rewrite|migrate entire|rebuild|overhaul|redesign|rearchitect)\b",
    r"\b(build from scratch|greenfield|full system|end.to.end|across (all|multiple) (services|systems|repos))\b",
    r"\b(large.scale|enterprise.grade|production.ready|high.availability)\b",
    r"\b(full.stack|platform.wide|cross.team)\b",
    r"\b(security (audit|review) of|threat model|penetration test)\b",
]

# MEDIUM: multi-file features, non-trivial integrations, refactors
_MEDIUM_PATTERNS = [
    r"\b(implement|integrate|refactor|design|develop|build|create|orchestrate)\b",
    r"\b(add (support for|integration with)|wire up|connect|link)\b",
    r"\b(multiple files|across (the|multiple) (codebase|modules)|end.to.end)\b",
    r"\b(workflow|pipeline|orchestrat|coordinat|multi.step)\b",
    r"\b(test suite|test coverage|comprehensive tests)\b",
]

# EASY: single-file changes, clear scope, targeted fixes
_EASY_PATTERNS = [
    r"\b(add|fix|update|change|rename|remove|delete|modify|adjust|tweak|patch)\b",
    r"\b(one (file|function|method|class|endpoint|route|test))\b",
    r"\b(small|simple|quick|minor|straightforward|one.liner)\b",
    r"\b(bug fix|typo|missing import|wrong (value|path|key))\b",
]

# SIMPLE: read-only, lookup, no code changes required
_SIMPLE_PATTERNS = [
    r"\b(what is|what are|how many|who is|when did|where is|which)\b",
    r"\b(list|show|display|print|tell me|explain|describe|summarize)\b",
    r"\b(read|look up|find|search|query|check|get|fetch)\b",
    r"\b(status|count|summary|overview|report)\b",
]

# Pattern group ordered from HARD → SIMPLE (first match wins)
_ORDERED_PATTERN_GROUPS: list[tuple[ComplexityTier, list[str]]] = [
    (ComplexityTier.HARD, _HARD_PATTERNS),
    (ComplexityTier.MEDIUM, _MEDIUM_PATTERNS),
    (ComplexityTier.EASY, _EASY_PATTERNS),
    (ComplexityTier.SIMPLE, _SIMPLE_PATTERNS),
]


class ComplexityClassifier:
    """Classifies task prompts into complexity tiers for model routing."""

    @classmethod
    def score(cls, prompt: str) -> ComplexityScore:
        """Score a prompt and return a ComplexityScore with routing metadata.

        Classification rules (first match wins, ordered HARD → SIMPLE):
        1. Count keyword matches across all tiers
        2. The tier with the *highest* match count wins (not just first match)
        3. Confidence = winning_matches / (winning_matches + runner_up_matches)
        4. Default to MEDIUM if no patterns match (safest non-destructive choice)
        """
        prompt_lower = prompt.lower()

        # Count matches per tier
        match_counts: dict[ComplexityTier, int] = {}
        matched_reasons: dict[ComplexityTier, str] = {}

        for tier, patterns in _ORDERED_PATTERN_GROUPS:
            count = 0
            first_match = None
            for pattern in patterns:
                m = re.search(pattern, prompt_lower)
                if m:
                    count += 1
                    if first_match is None:
                        first_match = m.group(0)
            match_counts[tier] = count
            if first_match:
                matched_reasons[tier] = f'matched "{first_match}"'

        # Pick winner by highest match count
        best_tier = max(match_counts, key=lambda t: match_counts[t])
        best_count = match_counts[best_tier]

        if best_count == 0:
            # No matches at all — default to MEDIUM (safest fallback)
            best_tier = ComplexityTier.MEDIUM
            confidence = 0.3
            reason = "No keyword matches; defaulting to MEDIUM"
        else:
            # Confidence = winner share of total matched signals
            total_matches = sum(match_counts.values())
            confidence = round(best_count / total_matches, 2) if total_matches > 0 else 0.5
            reason = matched_reasons.get(best_tier, f"{best_count} keyword matches")

        provider, model = TIER_MODEL_MAP[best_tier]

        return ComplexityScore(
            tier=best_tier,
            confidence=min(confidence, 1.0),
            estimated_subtasks=TIER_SUBTASK_ESTIMATE[best_tier],
            token_budget=TIER_TOKEN_BUDGET[best_tier],
            recommended_provider=provider,
            recommended_model=model,
            reason=reason,
        )
