"""Task handler for AgentMesh events in Agent Jumbo.

Routes ``task.assigned`` events to the appropriate Agent Jumbo profile
and reports lifecycle events (accepted, status_update, completed, failed,
escalated) back through the AgentMesh bridge.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

from python.helpers.agentmesh_risk import classify_risk

if TYPE_CHECKING:
    from python.helpers.agentmesh_bridge import AgentMeshBridge, AgentMeshEvent

logger = logging.getLogger(__name__)

# Map task categories to Agent Jumbo profile names.
# The profile name is used as a hint in the system prompt —
# it does not require a full runtime reconfiguration.
CATEGORY_PROFILE_MAP: dict[str, str] = {
    "deployment": "actor-ops",
    "security_scan": "hacker",
    "code_review": "developer",
    "research": "researcher",
    "content": "ghost-writer",
    "architecture": "developer",
    "workflow": "actor-ops",
    "general": "base",
    # C-suite executive routing
    "financial_report": "cfo",
    "revenue_analysis": "cfo",
    "payment_dunning": "cfo",
    "ops_digest": "coo",
    "sla_enforcement": "coo",
    "devops": "coo",
    "sales_pipeline": "cso",
    "proposal_generation": "cso",
    "brand_review": "cmo",
    "content_calendar": "cmo",
    "marketing": "cmo",
}


def register_task_handlers(bridge: AgentMeshBridge) -> None:
    """Register all AgentMesh task event handlers on the bridge."""
    bridge.on("task.assigned", _handle_task_assigned)
    bridge.on("task.approval_resolved", _handle_approval_resolved)
    # C-suite executive event handlers
    bridge.on("executive.financial_report", _handle_task_assigned)
    bridge.on("executive.ops_digest", _handle_task_assigned)
    bridge.on("executive.sales_update", _handle_task_assigned)
    bridge.on("executive.brand_review", _handle_task_assigned)


async def _handle_task_assigned(event: AgentMeshEvent) -> None:
    """Handle an incoming task assignment from Mahoosuc OS."""
    payload = event.payload
    task_id = payload.get("taskId", event.aggregate_id)
    assignee = payload.get("assignee", "")

    if assignee != "agent-jumbo":
        return  # Not for us

    category = payload.get("category", "general")
    risk_level = classify_risk(payload)
    correlation_id = event.metadata.get("correlationId")

    logger.info(
        "Received task.assigned: %s (category=%s, risk=%s)",
        task_id,
        category,
        risk_level,
    )

    # If high risk, wait for approval instead of executing
    if risk_level in ("HIGH", "CRITICAL"):
        logger.info("Task %s requires approval (risk=%s)", task_id, risk_level)
        bridge = _get_bridge()
        if bridge:
            await bridge.emit(
                event_type="task.approval_required",
                aggregate_id=task_id,
                payload={
                    "taskId": task_id,
                    "riskLevel": risk_level,
                    "originalPayload": payload,
                },
                correlation_id=correlation_id,
            )
        return

    await _execute_task(task_id, payload, correlation_id)


async def _handle_approval_resolved(event: AgentMeshEvent) -> None:
    """Handle approval resolution — execute if approved."""
    payload = event.payload
    task_id = payload.get("taskId", event.aggregate_id)
    status = payload.get("status", "")
    correlation_id = event.metadata.get("correlationId")

    if status == "approved":
        original_payload = payload.get("originalPayload", {})
        await _execute_task(task_id, original_payload, correlation_id)
    elif status == "rejected":
        bridge = _get_bridge()
        if bridge:
            await bridge.emit(
                event_type="task.failed",
                aggregate_id=task_id,
                payload={
                    "taskId": task_id,
                    "error": "Task rejected by approval workflow",
                    "executedBy": "agent-jumbo",
                    "executionTimeMs": 0,
                },
                correlation_id=correlation_id,
            )


def _get_or_create_mesh_context():
    """Get or create a dedicated AgentContext for mesh task execution.

    Uses AgentContextType.TASK with a fixed ID so mesh tasks never
    interfere with user chat sessions.
    """
    from agent import AgentContext, AgentContextType

    mesh_ctx_id = "agentmesh-worker"
    ctx = AgentContext.get(mesh_ctx_id)
    if ctx:
        return ctx

    # Create a fresh context with the current agent config
    from initialize import initialize_agent

    config = initialize_agent()

    ctx = AgentContext(
        config=config,
        id=mesh_ctx_id,
        name="AgentMesh Worker",
        type=AgentContextType.TASK,
    )
    logger.info("Created dedicated AgentMesh context (id=%s)", mesh_ctx_id)
    return ctx


async def _execute_task(
    task_id: str,
    payload: dict[str, Any],
    correlation_id: str | None,
) -> None:
    """Execute a task using a dedicated mesh context."""
    bridge = _get_bridge()
    if not bridge:
        logger.error("No AgentMesh bridge available")
        return

    # Emit accepted
    await bridge.emit(
        event_type="task.accepted",
        aggregate_id=task_id,
        payload={"taskId": task_id, "executedBy": "agent-jumbo"},
        correlation_id=correlation_id,
    )

    category = payload.get("category", "general")
    profile = payload.get("suggestedProfile") or CATEGORY_PROFILE_MAP.get(category, "base")
    title = payload.get("title", "Untitled task")
    description = payload.get("description", "")
    context_data = payload.get("context", {})

    # Build a prompt for the agent
    prompt_parts = [
        f"[AgentMesh Task: {task_id}]",
        f"Profile hint: {profile}",
        f"Task: {title}",
    ]
    if description:
        prompt_parts.append(f"Description: {description}")
    if context_data:
        prompt_parts.append(f"Context: {context_data}")

    task_prompt = "\n".join(prompt_parts)

    start_time = time.monotonic()
    try:
        import asyncio

        from agent import UserMessage

        ctx = _get_or_create_mesh_context()

        msg = UserMessage(message=task_prompt)
        deferred = ctx.communicate(msg)

        # Wait for the task to complete without blocking the event loop
        timeout = payload.get("timeout", 300)
        if deferred and hasattr(deferred, "result_sync"):
            result = await asyncio.to_thread(deferred.result_sync, timeout)
        else:
            result = {"status": "dispatched", "note": "Task sent to agent loop"}

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        await bridge.emit(
            event_type="task.completed",
            aggregate_id=task_id,
            payload={
                "taskId": task_id,
                "result": result if isinstance(result, dict) else str(result),
                "executedBy": f"agent-jumbo/{profile}",
                "executionTimeMs": elapsed_ms,
            },
            correlation_id=correlation_id,
        )
        logger.info("Task %s completed in %dms", task_id, elapsed_ms)

    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        error_msg = str(exc)
        logger.exception("Task %s failed: %s", task_id, error_msg)

        # Decide whether to fail or escalate
        if "beyond capability" in error_msg.lower() or "not supported" in error_msg.lower():
            await bridge.emit(
                event_type="task.escalated",
                aggregate_id=task_id,
                payload={
                    "taskId": task_id,
                    "reason": error_msg,
                    "escalationType": "beyond_capability",
                    "context": payload,
                },
                correlation_id=correlation_id,
            )
        else:
            await bridge.emit(
                event_type="task.failed",
                aggregate_id=task_id,
                payload={
                    "taskId": task_id,
                    "error": error_msg,
                    "executedBy": f"agent-jumbo/{profile}",
                    "executionTimeMs": elapsed_ms,
                },
                correlation_id=correlation_id,
            )


# -- Bridge singleton -------------------------------------------------------
# Set by the startup code that creates and connects the bridge.

_bridge_instance: AgentMeshBridge | None = None


def set_bridge(bridge: AgentMeshBridge) -> None:
    global _bridge_instance
    _bridge_instance = bridge


def _get_bridge() -> AgentMeshBridge | None:
    return _bridge_instance
