"""Trust Gate — blocks tool execution for user approval based on trust level.

Runs before every tool call. Checks:
  1. Is the tool in the user's permanent allow list? → skip
  2. Does the current trust level require approval for this risk level? → block

When blocking, stores a structured approval record via cowork.add_approval()
and sets context.paused = True so the agent spin-waits at handle_intervention()
until the user approves or denies in the cowork sidebar panel.

On approval: cowork_approvals_update.py injects a retry message and sets
context.paused = False, resuming the agent.
"""

import uuid

from python.helpers import cowork, settings
from python.helpers.errors import RepairableException
from python.helpers.extension import Extension
from python.helpers.trust_system import (
    TRUST_ALWAYS_ALLOW_KEY,
    TrustLevel,
    get_approval_explanation,
    get_approval_fingerprint,
    get_tool_risk,
    get_trust_level,
    is_always_allowed,
    requires_approval,
)

# Tools that bypass the gate entirely — agent cannot function without these
_GATE_BYPASS = {"response", "input", "wait", "unknown"}

# Risk level labels for the approval record
_RISK_LABELS = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}


class TrustGate(Extension):
    async def execute(self, **kwargs):
        tool_name = kwargs.get("tool_name", "")
        tool_args = kwargs.get("tool_args", {}) or {}

        if tool_name in _GATE_BYPASS:
            return

        trust_level = get_trust_level()

        # Check permanent allow list first
        s = settings.get_settings()
        if is_always_allowed(tool_name, s):
            return

        if not requires_approval(tool_name, trust_level):
            return  # Auto-approved at this trust level

        agent = kwargs.get("agent")
        if agent is None:
            # No agent context — fall back to text warning (shouldn't happen in prod)
            raise RepairableException(
                f"[TRUST GATE] {tool_name} requires approval but no agent context available."
            )

        # Build and store the approval record
        risk = get_tool_risk(tool_name)
        approval = cowork.add_approval(
            agent.context,
            {
                "id": f"trust-{uuid.uuid4().hex[:12]}",
                "source": "trust_gate",
                "tool_name": tool_name,
                "tool_args": tool_args,
                "risk": _RISK_LABELS.get(int(risk), "MEDIUM"),
                "risk_label": get_approval_explanation(tool_name, tool_args),
                "trust_level_name": TrustLevel(trust_level).name.capitalize(),
                "status": "pending",
                "fingerprint": get_approval_fingerprint(tool_name, tool_args),
                "agent_number": getattr(agent, "agent_number", 0),
            },
        )

        # Pause the agent — handle_intervention() spin-waits while context.paused is True
        agent.context.paused = True

        agent.context.log.log(
            type="info",
            heading=f"Trust gate blocked: {tool_name}",
            content=f"Risk={_RISK_LABELS.get(int(risk))} trust={TrustLevel(trust_level).name} approval_id={approval['id']}",
        )

        raise RepairableException(
            f"[TRUST GATE] {tool_name} requires approval. "
            f"Check the Approvals panel to approve or deny this action."
        )
