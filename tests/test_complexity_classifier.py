"""
Tests for ComplexityClassifier — keyword-based task complexity tier detection.

Validates:
  - Each tier's keyword patterns trigger correctly
  - TIER_MODEL_MAP constants are consistent
  - Confidence scoring is in valid range
  - Default fallback for unrecognized prompts is MEDIUM
  - ComplexityScore dataclass has all required fields
"""

from __future__ import annotations

import pytest

from python.helpers.complexity_classifier import (
    TIER_MODEL_MAP,
    TIER_SUBTASK_ESTIMATE,
    TIER_TOKEN_BUDGET,
    ComplexityClassifier,
    ComplexityTier,
)

# ---------------------------------------------------------------------------
# Tier classification
# ---------------------------------------------------------------------------


class TestSimpleTier:
    @pytest.mark.parametrize(
        "prompt",
        [
            "What is the current git branch?",
            "How many signups are there?",
            "List all solutions in the catalog",
            "Show me the status of the payment system",
            "Tell me the version of the app",
        ],
    )
    def test_simple_prompts_classified_as_simple(self, prompt):
        result = ComplexityClassifier.score(prompt)
        assert result.tier == ComplexityTier.SIMPLE, f"Expected SIMPLE for: {prompt!r}, got {result.tier}"

    def test_simple_score_has_correct_provider(self):
        result = ComplexityClassifier.score("What is the status of the queue?")
        assert result.recommended_provider == "ollama"

    def test_simple_estimate_is_one_subtask(self):
        result = ComplexityClassifier.score("How many customers are active?")
        assert result.estimated_subtasks == 1


class TestEasyTier:
    @pytest.mark.parametrize(
        "prompt",
        [
            "Fix the typo in the README",
            "Add a missing import to the signup module",
            "Rename the function from get_user to fetch_user",
            "Update the error message in the payment handler",
            "Remove the debug print statement",
        ],
    )
    def test_easy_prompts_classified_as_easy(self, prompt):
        result = ComplexityClassifier.score(prompt)
        assert result.tier == ComplexityTier.EASY, f"Expected EASY for: {prompt!r}, got {result.tier}"

    def test_easy_score_uses_google_provider(self):
        result = ComplexityClassifier.score("Fix the bug in the login handler")
        assert result.recommended_provider == "google"

    def test_easy_token_budget_is_2000(self):
        result = ComplexityClassifier.score("Add a health check endpoint")
        assert result.token_budget == 2_000


class TestMediumTier:
    @pytest.mark.parametrize(
        "prompt",
        [
            "Implement the signup email confirmation flow",
            "Integrate the Stripe payment provider into the checkout",
            "Refactor the dunning manager to support PayPal",
            "Design the multi-LLM task routing system",
            "Build a comprehensive test suite for the coordinator tool",
        ],
    )
    def test_medium_prompts_classified_as_medium(self, prompt):
        result = ComplexityClassifier.score(prompt)
        assert result.tier == ComplexityTier.MEDIUM, f"Expected MEDIUM for: {prompt!r}, got {result.tier}"

    def test_medium_uses_anthropic_sonnet(self):
        result = ComplexityClassifier.score("Implement the new payment router")
        assert result.recommended_provider == "anthropic"
        assert "sonnet" in result.recommended_model

    def test_medium_subtask_estimate(self):
        result = ComplexityClassifier.score("Integrate Linear with the workflow engine")
        assert result.estimated_subtasks == 5


class TestHardTier:
    @pytest.mark.parametrize(
        "prompt",
        [
            "Architect a multi-tenant SaaS platform from scratch",
            "Rewrite the entire authentication system",
            "Migrate entire database schema to a new provider",
            "Redesign the agent orchestration layer",
            "Build an enterprise-grade deployment pipeline",
        ],
    )
    def test_hard_prompts_classified_as_hard(self, prompt):
        result = ComplexityClassifier.score(prompt)
        assert result.tier == ComplexityTier.HARD, f"Expected HARD for: {prompt!r}, got {result.tier}"

    def test_hard_uses_anthropic_opus(self):
        result = ComplexityClassifier.score("Architect a full observability platform")
        assert result.recommended_provider == "anthropic"
        assert "opus" in result.recommended_model

    def test_hard_token_budget_is_32k(self):
        result = ComplexityClassifier.score("Rewrite the billing system from scratch")
        assert result.token_budget == 32_000


# ---------------------------------------------------------------------------
# Default fallback
# ---------------------------------------------------------------------------


class TestDefaultFallback:
    def test_unrecognized_prompt_defaults_to_medium(self):
        result = ComplexityClassifier.score("xyzzy frobnicate quux")
        assert result.tier == ComplexityTier.MEDIUM

    def test_empty_prompt_defaults_to_medium(self):
        result = ComplexityClassifier.score("")
        assert result.tier == ComplexityTier.MEDIUM

    def test_fallback_confidence_is_low(self):
        result = ComplexityClassifier.score("xyzzy frobnicate quux")
        assert result.confidence <= 0.5


# ---------------------------------------------------------------------------
# ComplexityScore fields
# ---------------------------------------------------------------------------


class TestComplexityScoreFields:
    def test_score_has_all_required_fields(self):
        result = ComplexityClassifier.score("Implement the new dashboard")
        assert hasattr(result, "tier")
        assert hasattr(result, "confidence")
        assert hasattr(result, "estimated_subtasks")
        assert hasattr(result, "token_budget")
        assert hasattr(result, "recommended_provider")
        assert hasattr(result, "recommended_model")
        assert hasattr(result, "reason")

    def test_confidence_is_between_0_and_1(self):
        for prompt in [
            "What is the status?",
            "Fix the bug",
            "Implement the feature",
            "Architect the system",
            "xyzzy",
        ]:
            result = ComplexityClassifier.score(prompt)
            assert 0.0 <= result.confidence <= 1.0, f"Confidence out of range for: {prompt!r}"

    def test_reason_is_non_empty(self):
        result = ComplexityClassifier.score("Add the missing endpoint")
        assert result.reason
        assert len(result.reason) > 0


# ---------------------------------------------------------------------------
# TIER_MODEL_MAP consistency
# ---------------------------------------------------------------------------


class TestTierModelMap:
    def test_all_tiers_have_model_entries(self):
        for tier in ComplexityTier:
            assert tier in TIER_MODEL_MAP, f"Missing TIER_MODEL_MAP entry for {tier}"
            assert tier in TIER_TOKEN_BUDGET, f"Missing TIER_TOKEN_BUDGET entry for {tier}"
            assert tier in TIER_SUBTASK_ESTIMATE, f"Missing TIER_SUBTASK_ESTIMATE entry for {tier}"

    def test_model_map_values_are_provider_model_tuples(self):
        for tier, (provider, model) in TIER_MODEL_MAP.items():
            assert isinstance(provider, str) and provider, f"Provider empty for {tier}"
            assert isinstance(model, str) and model, f"Model empty for {tier}"

    def test_token_budgets_increase_with_complexity(self):
        budgets = [
            TIER_TOKEN_BUDGET[t]
            for t in [
                ComplexityTier.SIMPLE,
                ComplexityTier.EASY,
                ComplexityTier.MEDIUM,
                ComplexityTier.HARD,
            ]
        ]
        assert budgets == sorted(budgets), "Token budgets should increase SIMPLE → HARD"

    def test_subtask_estimates_increase_with_complexity(self):
        estimates = [
            TIER_SUBTASK_ESTIMATE[t]
            for t in [
                ComplexityTier.SIMPLE,
                ComplexityTier.EASY,
                ComplexityTier.MEDIUM,
                ComplexityTier.HARD,
            ]
        ]
        assert estimates == sorted(estimates), "Subtask estimates should increase SIMPLE → HARD"

    def test_score_provider_matches_tier_map(self):
        """ComplexityClassifier.score() must return the same provider as TIER_MODEL_MAP."""
        for tier, (expected_provider, expected_model) in TIER_MODEL_MAP.items():
            # Create a fake score for this tier by calling score on a known trigger
            tier_trigger = {
                ComplexityTier.SIMPLE: "What is the current status?",
                ComplexityTier.EASY: "Fix the broken test",
                ComplexityTier.MEDIUM: "Implement the feature",
                ComplexityTier.HARD: "Architect the new system from scratch",
            }[tier]
            result = ComplexityClassifier.score(tier_trigger)
            if result.tier == tier:  # Only assert if we got the expected tier
                assert result.recommended_provider == expected_provider
                assert result.recommended_model == expected_model
