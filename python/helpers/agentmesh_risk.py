"""Risk classification for AgentMesh task payloads.

Returns a risk level that determines whether a task auto-executes
or requires human approval through the Mahoosuc OS approval workflow.
"""

from __future__ import annotations

from typing import Any

# Keywords that bump risk to HIGH regardless of category
HIGH_RISK_KEYWORDS = {"delete", "destroy", "rollback", "drop", "purge", "wipe"}

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def classify_risk(payload: dict[str, Any]) -> str:
    """Classify a task.assigned payload into a risk level.

    Returns one of: LOW, MEDIUM, HIGH, CRITICAL.
    """
    # Explicit risk level takes precedence
    explicit = payload.get("riskLevel")
    if explicit and explicit in RISK_LEVELS:
        return explicit

    category = payload.get("category", "general")
    priority = payload.get("priority", "medium")
    description = (payload.get("description") or "").lower()
    context = payload.get("context", {})
    target = (context.get("target") or context.get("environment") or "").lower()

    # Start with category-based default
    if category in ("research", "content", "general", "code_review"):
        risk = "LOW"
    elif category == "security_scan":
        risk = "MEDIUM"
    elif category == "deployment":
        risk = "HIGH" if "prod" in target else "MEDIUM"
    elif category == "architecture":
        risk = "HIGH"
    elif category == "workflow":
        risk = "MEDIUM"
    else:
        risk = "MEDIUM"

    # Keyword escalation
    if any(kw in description for kw in HIGH_RISK_KEYWORDS):
        risk = _escalate(risk)

    # Critical priority escalates one level
    if priority == "critical":
        risk = _escalate(risk)

    return risk


def _escalate(current: str) -> str:
    idx = RISK_LEVELS.index(current) if current in RISK_LEVELS else 1
    return RISK_LEVELS[min(idx + 1, len(RISK_LEVELS) - 1)]
