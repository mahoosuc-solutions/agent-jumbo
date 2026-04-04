"""Progressive Trust System — graduated autonomy for AI newcomers.

4 trust levels control how much the agent can do without asking:
  1. Observer   — explains everything, always asks
  2. Guided     — auto for low-risk, asks for medium+
  3. Collaborative — auto for most, asks for high-risk
  4. Autonomous — full autonomy (current default)
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import IntEnum
from typing import Any


class TrustLevel(IntEnum):
    OBSERVER = 1
    GUIDED = 2
    COLLABORATIVE = 3
    AUTONOMOUS = 4


class ToolRisk(IntEnum):
    LOW = 1  # read-only, no side effects
    MEDIUM = 2  # writes data, modifiable
    HIGH = 3  # sends external comms, executes code
    CRITICAL = 4  # deletes data, deploys, processes payments


# Tool risk classification — every tool gets a risk level
TOOL_RISK_REGISTRY: dict[str, ToolRisk] = {
    # LOW: read-only, information retrieval
    "response": ToolRisk.LOW,
    "input": ToolRisk.LOW,
    "memory_load": ToolRisk.LOW,
    "search_engine": ToolRisk.LOW,
    "document_query": ToolRisk.LOW,
    "vision_load": ToolRisk.LOW,
    "observability_usage_estimator": ToolRisk.LOW,
    "unknown": ToolRisk.LOW,
    "diagram_tool": ToolRisk.LOW,
    "diagram_architect": ToolRisk.LOW,
    # MEDIUM: writes/modifies data but no external effects
    "memory_save": ToolRisk.MEDIUM,
    "knowledge_ingest": ToolRisk.MEDIUM,
    "research_organize": ToolRisk.MEDIUM,
    "portfolio_manager": ToolRisk.MEDIUM,
    "portfolio_manager_tool": ToolRisk.MEDIUM,
    "project_lifecycle": ToolRisk.MEDIUM,
    "project_scaffold": ToolRisk.MEDIUM,
    "workflow_engine": ToolRisk.MEDIUM,
    "workflow_training": ToolRisk.MEDIUM,
    "linear_integration": ToolRisk.MEDIUM,
    "motion_integration": ToolRisk.MEDIUM,
    "notion_integration": ToolRisk.MEDIUM,
    "customer_lifecycle": ToolRisk.MEDIUM,
    "sales_generator": ToolRisk.MEDIUM,
    "brand_voice": ToolRisk.MEDIUM,
    "analytics_roi_calculator": ToolRisk.MEDIUM,
    "business_xray_tool": ToolRisk.MEDIUM,
    "property_manager_tool": ToolRisk.MEDIUM,
    "calendar_hub": ToolRisk.MEDIUM,
    "life_os": ToolRisk.MEDIUM,
    "skill_importer": ToolRisk.MEDIUM,
    "solution_catalog": ToolRisk.MEDIUM,
    "behaviour_adjustment": ToolRisk.MEDIUM,
    "wait": ToolRisk.MEDIUM,
    "scheduler": ToolRisk.MEDIUM,
    "coordinator": ToolRisk.MEDIUM,
    "digest_builder": ToolRisk.MEDIUM,
    "ralph_loop": ToolRisk.MEDIUM,
    "ai_migration": ToolRisk.MEDIUM,
    "demo_request_create": ToolRisk.MEDIUM,
    "demo_request_list": ToolRisk.MEDIUM,
    "auth_test": ToolRisk.MEDIUM,
    "api_design": ToolRisk.MEDIUM,
    "security_audit": ToolRisk.MEDIUM,
    # HIGH: external communication, code execution
    "email": ToolRisk.HIGH,
    "email_advanced": ToolRisk.HIGH,
    "telegram_send": ToolRisk.HIGH,
    "google_voice_sms": ToolRisk.HIGH,
    "twilio_voice_call": ToolRisk.HIGH,
    "notify_user": ToolRisk.HIGH,
    "a2a_chat": ToolRisk.HIGH,
    "code_execution_tool": ToolRisk.HIGH,
    "run_in_terminal": ToolRisk.HIGH,
    "cowork_approval": ToolRisk.HIGH,
    "browser_agent": ToolRisk.HIGH,
    "visual_validation": ToolRisk.HIGH,
    "call_subordinate": ToolRisk.HIGH,
    "virtual_team": ToolRisk.HIGH,
    "swarm_batch": ToolRisk.HIGH,
    "claude_sdk_bridge": ToolRisk.HIGH,
    "opencode_bridge": ToolRisk.HIGH,
    "pms_hub_tool": ToolRisk.HIGH,
    "finance_manager": ToolRisk.HIGH,
    "mahoosuc_finance_report": ToolRisk.HIGH,
    "code_review": ToolRisk.HIGH,
    # CRITICAL: deploys, deletes, processes payments
    "memory_delete": ToolRisk.CRITICAL,
    "memory_forget": ToolRisk.CRITICAL,
    "deployment_orchestrator": ToolRisk.CRITICAL,
    "deployment_execute": ToolRisk.CRITICAL,
    "deployment_config": ToolRisk.CRITICAL,
    "deployment_run_checks": ToolRisk.CRITICAL,
    "deployment_validate_env": ToolRisk.CRITICAL,
    "deployment_record_result": ToolRisk.CRITICAL,
    "devops_deploy": ToolRisk.CRITICAL,
    "devops_monitor": ToolRisk.CRITICAL,
    "stripe_payments": ToolRisk.CRITICAL,
    "plugin_marketplace": ToolRisk.CRITICAL,
}


def get_tool_risk(tool_name: str) -> ToolRisk:
    """Get risk level for a tool. Defaults to MEDIUM if not classified."""
    return TOOL_RISK_REGISTRY.get(tool_name, ToolRisk.MEDIUM)


def requires_approval(tool_name: str, trust_level: int) -> bool:
    """Check if a tool requires user approval at the given trust level."""
    level = TrustLevel(min(max(trust_level, 1), 4))
    risk = get_tool_risk(tool_name)

    if level == TrustLevel.OBSERVER:
        return True  # Everything requires approval
    if level == TrustLevel.GUIDED:
        return risk >= ToolRisk.MEDIUM  # Medium and above
    if level == TrustLevel.COLLABORATIVE:
        return risk >= ToolRisk.HIGH  # High and above
    if level == TrustLevel.AUTONOMOUS:
        return risk >= ToolRisk.CRITICAL  # Only critical (deploy, delete, payments)
    return False


def get_trust_level() -> int:
    """Get current trust level from settings."""
    try:
        from python.helpers import settings

        s = settings.get_settings()
        return int(s.get("trust_level", TrustLevel.COLLABORATIVE))
    except Exception:
        return TrustLevel.COLLABORATIVE


def get_approval_explanation(tool_name: str, tool_args: dict) -> str:
    """Generate a plain-English explanation of what the tool will do."""
    risk = get_tool_risk(tool_name)
    risk_labels = {
        ToolRisk.LOW: "Low risk (read-only)",
        ToolRisk.MEDIUM: "Medium risk (modifies data)",
        ToolRisk.HIGH: "High risk (external communication or code execution)",
        ToolRisk.CRITICAL: "Critical risk (deployment, deletion, or payment)",
    }

    action = tool_args.get("action", "execute")
    target = tool_args.get("name", tool_args.get("prompt", tool_args.get("email", "")))
    if isinstance(target, str) and len(target) > 100:
        target = target[:100] + "..."

    explanation = f"Tool: {tool_name}\n"
    explanation += f"Action: {action}\n"
    if target:
        explanation += f"Target: {target}\n"
    explanation += f"Risk: {risk_labels.get(risk, 'Unknown')}\n"

    return explanation


# Trust level descriptions for UI
TRUST_LEVEL_INFO = {
    TrustLevel.OBSERVER: {
        "name": "Observer",
        "icon": "eye",
        "description": "Maximum oversight. The agent explains every action and asks for your approval before doing anything. Best for learning how AI agents work.",
        "auto": "Nothing",
        "asks": "Everything",
    },
    TrustLevel.GUIDED: {
        "name": "Guided",
        "icon": "hand",
        "description": "The agent handles simple read-only tasks automatically, but asks before modifying data, sending messages, or executing code.",
        "auto": "Read-only tasks (search, view, query)",
        "asks": "Data modifications, external actions",
    },
    TrustLevel.COLLABORATIVE: {
        "name": "Collaborative",
        "icon": "handshake",
        "description": "The agent works independently on most tasks, only asking for approval on high-risk actions like sending emails, executing code, or making payments.",
        "auto": "Most tasks including data modifications",
        "asks": "Email, code execution, payments, deployments",
    },
    TrustLevel.AUTONOMOUS: {
        "name": "Autonomous",
        "icon": "rocket",
        "description": "Full autonomy. The agent handles everything including high-risk actions, only pausing for critical operations like deployments and payments.",
        "auto": "Everything except critical operations",
        "asks": "Deployments, deletions, payment processing",
    },
}


# ── Always-allow list ──────────────────────────────────────────────────────

TRUST_ALWAYS_ALLOW_KEY = "trust_always_allow"


def is_always_allowed(tool_name: str, settings: Mapping[str, Any]) -> bool:
    """Return True if the tool is in the user's permanent allow list."""
    allow_list = settings.get(TRUST_ALWAYS_ALLOW_KEY, [])
    return tool_name in allow_list


def get_approval_fingerprint(tool_name: str, tool_args: dict) -> str:
    """Return a stable fingerprint for an approval record.

    Format: "<tool_name>:<first_meaningful_arg_value>"
    Used by cowork.find_matching_approval() for deduplication.
    """
    # Pick the first string arg value as the identifier (to, email, name, prompt)
    first_val = ""
    for val in tool_args.values():
        if isinstance(val, str) and val:
            first_val = val
            break
    return f"{tool_name}:{first_val}"
