# Human-in-the-Loop Patterns

## Overview

Fully autonomous AI agents are rarely appropriate for production systems that affect real users, money, or critical infrastructure. Human-in-the-loop (HITL) patterns define when and how human judgment is injected into automated workflows. The goal is to let agents handle routine work autonomously while routing high-risk, ambiguous, or novel situations to humans.

## Core Concepts

### Confidence Thresholds

Every agent decision has an associated confidence level. The threshold model defines three zones:

```
|--- Autonomous ---|--- Review Required ---|--- Human Only ---|
0.0               0.7                     0.4                1.0
     High conf          Medium conf            Low conf
```

```python
class ConfidenceRouter:
    def __init__(self, auto_threshold: float = 0.85, reject_threshold: float = 0.4):
        self.auto_threshold = auto_threshold
        self.reject_threshold = reject_threshold

    def route(self, confidence: float, action: Action) -> Decision:
        # High-risk actions have stricter thresholds
        effective_threshold = self.auto_threshold
        if action.risk_level == "high":
            effective_threshold = 0.95

        if confidence >= effective_threshold:
            return Decision.AUTONOMOUS
        elif confidence >= self.reject_threshold:
            return Decision.HUMAN_REVIEW
        else:
            return Decision.REJECT
```

### Risk-Based Routing

Not all actions are equal. Reading data is low-risk. Deleting a production database is catastrophic. The HITL system should factor in both confidence and impact.

```python
RISK_MATRIX = {
    ("high_confidence", "low_impact"):   "autonomous",
    ("high_confidence", "high_impact"):  "human_review",
    ("low_confidence",  "low_impact"):   "autonomous_with_logging",
    ("low_confidence",  "high_impact"):  "human_required",
}
```

## Pattern 1: Approval Gates

The agent pauses at defined checkpoints and waits for human approval before proceeding. Used for irreversible or high-impact actions.

```
Agent works --> Reaches gate --> Submits proposal --> Human reviews
                                                        |
                                              Approve   |   Reject
                                                |       |     |
                                           Continue   Modify  Stop
```

**Implementation:**

```python
class ApprovalGate:
    def __init__(self, approval_service: ApprovalService):
        self.service = approval_service

    async def request_approval(
        self,
        action: Action,
        context: dict,
        timeout: timedelta = timedelta(hours=4),
    ) -> ApprovalResult:
        request = ApprovalRequest(
            action=action,
            context=context,
            requested_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timeout,
        )
        ticket = await self.service.create(request)

        # Notify reviewers
        await self.notify_reviewers(ticket, action.required_approvers)

        # Wait for decision (with timeout)
        result = await self.service.wait_for_decision(ticket.id, timeout)

        if result.status == "expired":
            return ApprovalResult(approved=False, reason="Approval timed out")
        return result
```

**When to use:**
- Financial transactions above a threshold
- Data deletion or modification in production
- Customer-facing communications
- Configuration changes to production systems

## Pattern 2: Escalation Chains

When the agent cannot resolve a situation, it escalates through a defined chain. Each level in the chain has progressively more authority and context.

```python
ESCALATION_CHAIN = [
    EscalationLevel(
        level=1,
        name="AI Agent",
        auto_resolve=True,
        max_attempts=3,
        timeout=timedelta(minutes=5),
    ),
    EscalationLevel(
        level=2,
        name="Senior Agent (AI + Tools)",
        auto_resolve=True,
        max_attempts=1,
        timeout=timedelta(minutes=15),
    ),
    EscalationLevel(
        level=3,
        name="Human Operator",
        auto_resolve=False,
        timeout=timedelta(hours=4),
        notify=["ops-team@company.com"],
    ),
    EscalationLevel(
        level=4,
        name="On-Call Engineer",
        auto_resolve=False,
        timeout=timedelta(hours=1),
        notify=["pagerduty:oncall-eng"],
    ),
]
```

**Key rules:**
- Each level must have a timeout. If it expires, escalate automatically.
- Include all context from previous levels so the next level does not start from scratch.
- Log every escalation for post-incident analysis.

## Pattern 3: Review Queues

The agent completes work but marks it as "pending review." A human reviews the output asynchronously before it takes effect.

```python
class ReviewQueue:
    async def submit_for_review(
        self,
        agent_output: AgentOutput,
        priority: str = "normal",
        review_type: str = "approval",  # "approval" | "correction" | "audit"
    ) -> ReviewTicket:
        ticket = ReviewTicket(
            output=agent_output,
            priority=priority,
            review_type=review_type,
            submitted_at=datetime.utcnow(),
            sla=self.get_sla(priority),  # e.g., 4h for normal, 1h for urgent
        )
        await self.queue.push(ticket)
        return ticket
```

**SLA patterns:**
- **Urgent**: 1 hour (customer-facing errors, security issues)
- **Normal**: 4 hours (content generation, report drafts)
- **Low**: 24 hours (training data curation, documentation updates)

## Pattern 4: Supervised Autonomy

The agent operates autonomously but all actions are logged in real-time. A human dashboard shows agent activity and allows intervention at any point.

```python
class SupervisedAgent:
    async def execute(self, task: Task) -> Result:
        plan = await self.plan(task)
        await self.dashboard.publish_plan(plan)

        for step in plan.steps:
            # Check for human override before each step
            override = await self.dashboard.check_override(step.id)
            if override:
                if override.action == "skip":
                    continue
                elif override.action == "modify":
                    step = override.modified_step
                elif override.action == "abort":
                    return Result(status="aborted_by_human")

            result = await self.execute_step(step)
            await self.dashboard.publish_result(step.id, result)

        return self.synthesize(plan)
```

**When to use:**
- New agents in production (trust-building phase)
- High-value workflows where you want human oversight without blocking
- Training data collection: human corrections improve the agent over time

## Audit Trails

Every HITL interaction must produce an audit record. This is non-negotiable for compliance, debugging, and continuous improvement.

```python
@dataclass
class AuditRecord:
    timestamp: datetime
    agent_id: str
    session_id: str
    action: str
    confidence: float
    routing_decision: str  # "autonomous" | "human_review" | "escalated"
    human_reviewer: str | None
    human_decision: str | None  # "approved" | "rejected" | "modified"
    modification_details: dict | None
    time_to_decision: timedelta | None
    context_snapshot: dict  # Full agent state at decision point
```

**What to track:**
- How often does the agent's decision get overridden? (quality metric)
- What is the average time-to-review? (operational metric)
- Which types of decisions are most frequently escalated? (training signal)
- Are there reviewers who always approve without reading? (process metric)

## Autonomous vs. Human Review Decision Framework

| Signal | Lean Autonomous | Lean Human Review |
|--------|----------------|-------------------|
| Historical accuracy for this task type | > 95% | < 90% |
| Impact of error | Easily reversible | Irreversible or costly |
| Task novelty | Seen many similar | First time or rare |
| Regulatory requirement | None | Compliance mandated |
| Customer sensitivity | Internal only | Customer-facing |
| Financial impact | < $100 | > $1,000 |

## Feedback Loops

The HITL system should feed corrections back into the agent's behavior:

```python
class FeedbackCollector:
    async def record_correction(
        self,
        original_output: AgentOutput,
        corrected_output: HumanOutput,
        correction_type: str,  # "factual", "tone", "scope", "safety"
    ):
        # Store for fine-tuning or prompt improvement
        await self.store.save(FeedbackRecord(
            original=original_output,
            corrected=corrected_output,
            type=correction_type,
        ))

        # Update confidence thresholds dynamically
        if correction_type == "safety":
            await self.threshold_manager.tighten(
                task_type=original_output.task_type,
                amount=0.05,  # Require higher confidence after safety correction
            )
```

## Common Mistakes

1. **Binary thinking**: Treating HITL as all-or-nothing. The best systems have a gradient from full autonomy to full human control.

2. **Review fatigue**: Routing too many low-risk items to humans. They stop paying attention. Only escalate what matters.

3. **Missing timeouts**: A review request without a timeout blocks the workflow forever. Always have a default action on timeout (usually: reject and notify).

4. **No context in review requests**: Sending a human a bare "approve/reject" without the agent's reasoning, confidence score, and relevant data. Reviewers need context to make fast, good decisions.

5. **Ignoring feedback**: Collecting human corrections but never using them to improve the agent. The HITL system should close the loop.
