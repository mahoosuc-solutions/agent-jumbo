"""Trust Gate — pauses tool execution for user approval based on trust level.

Runs before every tool call. Checks the user's trust level against the
tool's risk classification. If approval is required, pauses execution
and prompts the user (via the agent's response) to approve or reject.

At Observer level, this means every action gets explained first.
At Autonomous level, only critical actions (deploy, delete, payment) pause.
"""

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

        # Skip gate for the response tool (otherwise agent can't respond)
        if tool_name in ("response", "input", "wait"):
            return

        trust_level = get_trust_level()

        if not requires_approval(tool_name, trust_level):
            return  # Auto-approved at this trust level

        # Build explanation
        explanation = get_approval_explanation(tool_name, tool_args)
        risk = get_tool_risk(tool_name)

        # Inject approval prompt into agent's context
        # The agent will see this as a system message and present it to the user
        approval_msg = (
            f"\n[TRUST GATE — Approval Required]\n"
            f"{explanation}\n"
            f"Your trust level is set to {TrustLevel(trust_level).name}. "
            f"This action requires your approval at this level.\n"
            f"To approve, respond with 'yes' or 'approve'. "
            f"To reject, respond with 'no' or 'reject'.\n"
            f"To change your trust level, use /trust in Telegram or Settings > Trust Level."
        )

        # Add to agent's loop data for display
        agent = kwargs.get("agent")
        if agent and hasattr(agent, "loop_data") and agent.loop_data:
            agent.loop_data.extras_temporary["trust_gate_pending"] = {
                "tool_name": tool_name,
                "tool_args": tool_args,
                "risk": risk.name,
                "explanation": explanation,
                "approval_message": approval_msg,
            }

        # Log the gate activation
        if agent:
            agent.context.log.log(
                type="info",
                heading=f"Trust gate: {tool_name}",
                content=f"Approval required (trust={TrustLevel(trust_level).name}, risk={risk.name})",
            )
