"""Trust Gate — blocks tool execution for user approval based on trust level.

Runs before every tool call. Checks the user's trust level against the
tool's risk classification. If approval is required, raises a
RepairableException that sends the approval prompt back to the agent,
which then presents it to the user.

At Observer level, this means every action gets explained first.
At Autonomous level, only critical actions (deploy, delete, payment) pause.
"""

from python.helpers.errors import RepairableException
from python.helpers.extension import Extension
from python.helpers.trust_system import (
    TrustLevel,
    get_approval_explanation,
    get_tool_risk,
    get_trust_level,
    requires_approval,
)


class TrustGate(Extension):
    async def execute(self, **kwargs):
        tool_name = kwargs.get("tool_name", "")
        tool_args = kwargs.get("tool_args", {})

        # Skip gate for essential tools (otherwise agent can't respond or receive input)
        if tool_name in ("response", "input", "wait", "unknown"):
            return

        trust_level = get_trust_level()

        if not requires_approval(tool_name, trust_level):
            return  # Auto-approved at this trust level

        # Build explanation
        explanation = get_approval_explanation(tool_name, tool_args)
        risk = get_tool_risk(tool_name)

        approval_msg = (
            f"[TRUST GATE — Approval Required]\n"
            f"{explanation}\n"
            f"Trust level: {TrustLevel(trust_level).name} | Risk: {risk.name}\n"
            f"This tool requires approval at your current trust level. "
            f"Please confirm you want to proceed by responding with your intent, "
            f"or use a different approach."
        )

        # Log the gate activation
        agent = kwargs.get("agent")
        if agent:
            agent.context.log.log(
                type="info",
                heading=f"Trust gate blocked: {tool_name}",
                content=f"Risk={risk.name}, trust={TrustLevel(trust_level).name}",
            )

        # Raise RepairableException — this sends the message back to the LLM
        # as an error it can "repair" by asking the user for confirmation
        raise RepairableException(approval_msg)
