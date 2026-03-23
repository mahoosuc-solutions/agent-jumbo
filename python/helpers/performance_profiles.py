"""Performance Profiles — trust-level-aware agent configuration.

Each trust level maps to a performance profile that controls agent speed,
thoroughness, and resource usage. When trust level changes, the matching
profile is applied to settings automatically.

Profiles:
  Careful (Observer)       — slow, maximum explanations, quality-first routing
  Balanced (Guided)        — moderate speed, good explanations, balanced routing
  Efficient (Collaborative) — fast, concise, speed-first routing
  Turbo (Autonomous)       — maximum throughput, minimal overhead, cost routing
"""

from __future__ import annotations

PROFILES: dict[str, dict] = {
    "careful": {
        "trust_level": 1,
        "temperature": 0.1,
        "max_monologue_iterations": 15,
        "max_monologue_seconds": 600,
        "prompt_enhance_enabled": True,
        "prompt_enhance_timeout_seconds": 12,
        "prompt_enhance_max_chars": 6000,
        "chat_model_ctx_history": 0.55,
        "response_style": "verbose",
        "validation_level": "full",
        "explanation_depth": "full",
        "llm_routing_priority": "quality",
        "chat_model_rl_requests": 30,
        "chat_model_rl_input": 500000,
        "chat_model_rl_output": 100000,
    },
    "balanced": {
        "trust_level": 2,
        "temperature": 0.2,
        "max_monologue_iterations": 20,
        "max_monologue_seconds": 900,
        "prompt_enhance_enabled": True,
        "prompt_enhance_timeout_seconds": 8,
        "prompt_enhance_max_chars": 4000,
        "chat_model_ctx_history": 0.60,
        "response_style": "balanced",
        "validation_level": "standard",
        "explanation_depth": "summary",
        "llm_routing_priority": "balanced",
        "chat_model_rl_requests": 60,
        "chat_model_rl_input": 1000000,
        "chat_model_rl_output": 200000,
    },
    "efficient": {
        "trust_level": 3,
        "temperature": 0.3,
        "max_monologue_iterations": 25,
        "max_monologue_seconds": 1200,
        "prompt_enhance_enabled": False,
        "prompt_enhance_timeout_seconds": 6,
        "prompt_enhance_max_chars": 3000,
        "chat_model_ctx_history": 0.70,
        "response_style": "concise",
        "validation_level": "minimal",
        "explanation_depth": "none",
        "llm_routing_priority": "speed",
        "chat_model_rl_requests": 120,
        "chat_model_rl_input": 2000000,
        "chat_model_rl_output": 500000,
    },
    "turbo": {
        "trust_level": 4,
        "temperature": 0.5,
        "max_monologue_iterations": 40,
        "max_monologue_seconds": 1800,
        "prompt_enhance_enabled": False,
        "prompt_enhance_timeout_seconds": 4,
        "prompt_enhance_max_chars": 2000,
        "chat_model_ctx_history": 0.75,
        "response_style": "minimal",
        "validation_level": "none",
        "explanation_depth": "none",
        "llm_routing_priority": "cost",
        "chat_model_rl_requests": 0,
        "chat_model_rl_input": 0,
        "chat_model_rl_output": 0,
    },
}

# Map trust levels to profile names
TRUST_LEVEL_TO_PROFILE = {
    1: "careful",
    2: "balanced",
    3: "efficient",
    4: "turbo",
}


def resolve_profile(trust_level: int) -> dict:
    """Get the performance profile for a trust level."""
    profile_name = TRUST_LEVEL_TO_PROFILE.get(trust_level, "efficient")
    return PROFILES.get(profile_name, PROFILES["efficient"]).copy()


def get_profile_name(trust_level: int) -> str:
    """Get the profile name for a trust level."""
    return TRUST_LEVEL_TO_PROFILE.get(trust_level, "efficient")


def apply_profile_to_settings(settings: dict, trust_level: int) -> dict:
    """Apply a performance profile to settings based on trust level.

    Uses soft merge: profile values are applied as defaults, but
    settings explicitly changed by the user are preserved.

    The 'user_overrides' key in settings tracks which settings were
    manually changed. If not present, all profile values are applied.
    """
    profile = resolve_profile(trust_level)
    user_overrides = set(settings.get("user_overrides", []))

    # Settings that the profile controls
    PROFILE_MANAGED_KEYS = {
        "prompt_enhance_enabled",
        "prompt_enhance_timeout_seconds",
        "prompt_enhance_max_chars",
        "chat_model_ctx_history",
        "chat_model_rl_requests",
        "chat_model_rl_input",
        "chat_model_rl_output",
        "response_style",
        "validation_level",
        "explanation_depth",
        "llm_routing_priority",
        "max_monologue_iterations",
        "max_monologue_seconds",
    }

    for key in PROFILE_MANAGED_KEYS:
        if key in profile and key not in user_overrides:
            settings[key] = profile[key]

    # Temperature is nested in chat_model_kwargs
    if "temperature" not in user_overrides:
        kwargs = settings.get("chat_model_kwargs", {})
        if isinstance(kwargs, dict):
            kwargs["temperature"] = str(profile.get("temperature", 0.3))
            settings["chat_model_kwargs"] = kwargs

    # Always update trust_level and profile name
    settings["trust_level"] = trust_level
    settings["performance_profile"] = get_profile_name(trust_level)

    return settings


def get_profile_summary(trust_level: int) -> dict:
    """Get a human-readable summary of a profile for display."""
    profile = resolve_profile(trust_level)
    name = get_profile_name(trust_level)

    return {
        "name": name,
        "trust_level": trust_level,
        "speed": {
            "careful": "Slow — maximum safety",
            "balanced": "Moderate — good balance",
            "efficient": "Fast — experienced users",
            "turbo": "Maximum — power users",
        }.get(name, "Unknown"),
        "temperature": profile.get("temperature"),
        "max_iterations": profile.get("max_monologue_iterations"),
        "max_seconds": profile.get("max_monologue_seconds"),
        "prompt_enhance": profile.get("prompt_enhance_enabled"),
        "ctx_history_ratio": profile.get("chat_model_ctx_history"),
        "response_style": profile.get("response_style"),
        "routing_priority": profile.get("llm_routing_priority"),
    }
