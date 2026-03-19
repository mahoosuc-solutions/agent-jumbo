"""
Priority Scorer — assigns 0-100 priority scores to work items.

Pure functions, configurable via weight dicts.
"""

import json
from typing import Any

# ── Default weights (can be overridden via settings) ─────────────────

DEFAULT_SCANNER_WEIGHTS: dict[str, int] = {
    "fixme": 35,
    "todo": 15,
    "failing_test": 40,
    "skipped_test": 20,
    "stale_dep": 30,
    "coverage": 15,
}

DEFAULT_LINEAR_WEIGHTS: dict[str, int] = {
    # Linear priority field: 0=none, 1=urgent, 2=high, 3=medium, 4=low
    "priority_urgent": 40,
    "priority_high": 30,
    "priority_medium": 20,
    "priority_low": 10,
    "priority_none": 5,
}

# File importance: higher-traffic files get a bonus
IMPORTANT_FILE_PATTERNS = [
    ("test_", 5),
    ("__init__", 3),
    (".config", 5),
    ("route", 8),
    ("middleware", 8),
    ("auth", 10),
    ("security", 10),
    ("api/", 7),
    ("lib/", 5),
    ("core/", 7),
]


def score_scanner_item(
    item: dict[str, Any],
    weights: dict[str, int] | None = None,
) -> tuple[int, dict[str, Any]]:
    """
    Score a codebase-scanned item. Returns (score, breakdown).
    """
    w = weights or DEFAULT_SCANNER_WEIGHTS
    breakdown: dict[str, Any] = {}

    # Base score from source type
    base = w.get(item.get("source_type", ""), 15)
    breakdown["base_type"] = base

    # File importance bonus
    file_bonus = 0
    file_path = item.get("file_path", "").lower()
    for pattern, bonus in IMPORTANT_FILE_PATTERNS:
        if pattern in file_path:
            file_bonus = max(file_bonus, bonus)
    breakdown["file_importance"] = file_bonus

    # Security keyword bonus
    security_bonus = 0
    title = (item.get("title", "") + " " + item.get("description", "")).lower()
    security_keywords = ["security", "vulnerability", "injection", "xss", "csrf", "auth", "password", "secret", "token"]
    for kw in security_keywords:
        if kw in title:
            security_bonus = 15
            break
    breakdown["security"] = security_bonus

    raw = base + file_bonus + security_bonus
    score = min(100, max(0, raw))
    breakdown["total"] = score
    return score, breakdown


def score_linear_item(
    item: dict[str, Any],
    weights: dict[str, int] | None = None,
) -> tuple[int, dict[str, Any]]:
    """
    Score a Linear issue. Returns (score, breakdown).
    """
    w = weights or DEFAULT_LINEAR_WEIGHTS
    breakdown: dict[str, Any] = {}

    # Priority base
    priority = item.get("linear_priority", 0)
    priority_map = {
        1: "priority_urgent",
        2: "priority_high",
        3: "priority_medium",
        4: "priority_low",
        0: "priority_none",
    }
    priority_key = priority_map.get(priority, "priority_none")
    base = w.get(priority_key, 5)
    breakdown["priority_base"] = base

    # State bonus: in-progress states get a boost
    state_bonus = 0
    state = (item.get("linear_state") or "").lower()
    if "progress" in state or "started" in state:
        state_bonus = 10
    elif "review" in state:
        state_bonus = 15
    elif "blocked" in state:
        state_bonus = 5
    breakdown["state_bonus"] = state_bonus

    # Age factor: older issues get a small bump (up to 15 points for 30+ days)
    age_bonus = 0
    created = item.get("discovered_at") or item.get("created_at")
    if created:
        try:
            from datetime import datetime

            if isinstance(created, str):
                # Handle ISO format
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                age_days = (datetime.now(created_dt.tzinfo) - created_dt).days if created_dt.tzinfo else 0
            else:
                age_days = 0
            age_bonus = min(15, age_days // 2)
        except (ValueError, TypeError):
            age_bonus = 0
    breakdown["age_bonus"] = age_bonus

    # Label bonus
    label_bonus = 0
    labels_raw = item.get("linear_labels", "[]")
    try:
        labels = json.loads(labels_raw) if isinstance(labels_raw, str) else (labels_raw or [])
    except (json.JSONDecodeError, TypeError):
        labels = []
    priority_labels = {"bug", "critical", "urgent", "security", "p0", "p1"}
    for label in labels:
        if isinstance(label, str) and label.lower() in priority_labels:
            label_bonus = 10
            break
    breakdown["label_bonus"] = label_bonus

    raw = base + state_bonus + age_bonus + label_bonus
    score = min(100, max(0, raw))
    breakdown["total"] = score
    return score, breakdown


def score_item(item: dict[str, Any], weights: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    """Route to the appropriate scorer based on item source."""
    source = item.get("source", "scanner")
    if source == "linear":
        return score_linear_item(item, weights)
    return score_scanner_item(item, weights)
