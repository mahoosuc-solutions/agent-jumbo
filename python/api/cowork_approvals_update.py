from agent import UserMessage
from python.helpers import cowork
from python.helpers.api import ApiHandler, Request, Response


class CoworkApprovalsUpdate(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        ctxid = input.get("context", "")
        action = (input.get("action") or "").lower().strip()
        approval_id = input.get("approval_id", "")
        inherit = bool(input.get("inherit", True))

        try:
            context = self.use_context(ctxid, create_if_not_exists=False)
        except Exception:
            return {"approvals": []}

        approvals = cowork.get_approvals(context)

        if action == "clear_resolved":
            remaining = [
                approval
                for approval in approvals
                if approval.get("status") == "pending" and not approval.get("consumed")
            ]
            context.data[cowork.APPROVALS_KEY] = remaining
            return {"approvals": remaining}

        if action == "clear" and approval_id:
            remaining = [approval for approval in approvals if approval.get("id") != approval_id]
            context.data[cowork.APPROVALS_KEY] = remaining
            return {"approvals": remaining}

        if action in ("approve", "approve_and_retry", "deny") and approval_id:
            status = "approved" if action in ("approve", "approve_and_retry") else "denied"
            updated = cowork.update_approval(context, approval_id, status, resolved_by="user")
            if updated:
                updated["inherit"] = inherit
                is_trust_gate = updated.get("source") == "trust_gate"

                if action == "approve_and_retry" or is_trust_gate:
                    tool_name = updated.get("tool_name", "tool")
                    if status == "approved":
                        message = f"Approval granted for {tool_name}. Please retry the action now."
                    else:
                        message = f"User denied approval for {tool_name}. Do not attempt this action again in this session."
                    context.communicate(UserMessage(message=message, attachments=[], system_message=[]))

                # Unblock the agent for trust gate records (always) and explicit approve_and_retry
                if is_trust_gate or action == "approve_and_retry":
                    context.paused = False
                    context.resume_queued()

            return {"approvals": cowork.get_approvals(context)}

        return {"approvals": approvals}
