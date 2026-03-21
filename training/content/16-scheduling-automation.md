# Module 16: Scheduling & Automation

> **Learning Path:** Workflow & Automation Engineer
> **Audience:** Technical operators building automations
> **Prerequisites:** Basic workflow_design skill, Module 15 (Workflow Engine Deep Dive)

---

## Lesson: Scheduler Deep Dive

### Why This Matters

The scheduler is what turns workflows from things you manually trigger into things that run themselves. Without a solid understanding of scheduling:

- **Tasks fire at the wrong time** — A morning briefing arrives at 7 AM UTC instead of 7 AM in the operator's timezone, waking nobody up and informing nobody
- **Tasks pile up** — Multiple overlapping schedules compete for resources and produce duplicate outputs
- **Missed runs go undetected** — A nightly report silently stops running and nobody notices for a week
- **Timezone bugs surface seasonally** — Everything works until daylight saving time shifts and half your schedules break

Scheduling seems simple until it is not. The difference between "run every morning" and a production-grade schedule is handling timezones, missed runs, overlapping executions, and graceful error recovery.

**The hidden complexity of "every day at 7 AM":**

| Assumption | Reality |
|---|---|
| "7 AM" is obvious | 7 AM in which timezone? What happens during DST transitions? |
| "Every day" means every day | What about weekends? Holidays? Server maintenance windows? |
| One run per day | What if the 7 AM run is still executing when 8 AM triggers another workflow? |
| It will always succeed | What if it fails? Should it retry? When? How many times? |

### How to Think About It

**Cron Expressions**

Cron is the standard language for expressing schedules. Every operator must be fluent in reading and writing cron expressions.

```text
 ┌───────────── minute (0-59)
 │ ┌───────────── hour (0-23)
 │ │ ┌───────────── day of month (1-31)
 │ │ │ ┌───────────── month (1-12)
 │ │ │ │ ┌───────────── day of week (0-6, Sunday=0)
 │ │ │ │ │
 * * * * *
```

**Common patterns:**

| Schedule | Cron Expression | Notes |
|---|---|---|
| Every day at 7:00 AM | `0 7 * * *` | Simple daily |
| Weekdays at 7:00 AM | `0 7 * * 1-5` | Skips Saturday and Sunday |
| Every 15 minutes | `*/15 * * * *` | Interval-based |
| First Monday of month at 9 AM | `0 9 1-7 * 1` | Day-of-month range + day-of-week |
| Twice daily: 7 AM and 5 PM | `0 7,17 * * *` | Multiple values |
| Every 6 hours | `0 */6 * * *` | Fires at 0:00, 6:00, 12:00, 18:00 |

**Scheduling Types**

The scheduler supports three scheduling modes:

```text
CRON-BASED              INTERVAL-BASED          ONE-SHOT
(recurring, fixed)      (recurring, relative)   (single fire)

  7:00 AM daily           every 30 min            once at specific
  ────●────●────●──       ──●──●──●──●──          time, then done
      |    |    |           |  |  |  |                  |
   run  run  run         run run run run              run
```

| Mode | Use When | Example |
|---|---|---|
| Cron | Time-of-day matters, human rhythm | Morning briefing at 7 AM, EOD report at 5 PM |
| Interval | Frequency matters more than exact time | Check for new bookings every 15 minutes |
| One-shot | Single future event | Send reminder 24 hours before guest arrival |

**Timezone Handling**

Always specify timezone explicitly. Never rely on server timezone.

```text
WRONG:  cron="0 7 * * *"                    # 7 AM in... server time? UTC? Who knows?
RIGHT:  cron="0 7 * * *" timezone="US/Eastern"  # 7 AM Eastern, DST-aware
```

During DST transitions:

- **Spring forward** (2 AM becomes 3 AM): A job scheduled for 2:30 AM will be skipped. The scheduler detects this and logs a `skipped_dst` event.
- **Fall back** (2 AM happens twice): A job scheduled for 1:30 AM will run once (first occurrence). The scheduler deduplicates by default.

### Step-by-Step Approach

**Step 1: Create a cron-based recurring job**

```text
{{scheduler(action="create_job", name="morning-briefing", cron="0 7 * * *", timezone="US/Eastern", task="workflow:morning-briefing-assembly", config={"overlap_policy": "skip", "retry_on_failure": true, "max_retries": 2, "retry_delay": "5m"})}}
```

Key configuration:

- `overlap_policy: "skip"` — If the previous run is still executing, skip this trigger instead of starting a second instance
- `retry_on_failure` — Automatically retry if the workflow fails
- `max_retries` and `retry_delay` — Control retry behavior

**Step 2: Create an interval-based job**

```text
{{scheduler(action="create_job", name="booking-monitor", interval="15m", task="workflow:check-new-bookings", config={"overlap_policy": "queue", "active_hours": {"start": "06:00", "end": "22:00"}, "active_days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]})}}
```

The `active_hours` setting prevents the job from running overnight when nobody would act on the results.

**Step 3: Create a one-shot scheduled task**

```text
{{scheduler(action="create_job", name="prearrrival-chen-2026-03-21", type="one_shot", run_at="2026-03-20T10:00:00", timezone="US/Eastern", task="workflow:pre-arrival-message", params={"guest_name": "Sarah Chen", "booking_id": "BK-2026-0321"})}}
```

One-shot jobs are created dynamically when bookings arrive. They fire once and are marked as completed.

**Step 4: List and manage scheduled jobs**

```text
{{scheduler(action="list_jobs", status="active")}}
```

```text
{{scheduler(action="pause_job", name="booking-monitor", reason="PMS maintenance window 2026-03-21 02:00-06:00")}}
```

```text
{{scheduler(action="resume_job", name="booking-monitor")}}
```

**Step 5: Review job execution history**

```text
{{scheduler(action="get_job_history", name="morning-briefing", period="7d")}}
```

Check for missed runs, late executions, and error patterns.

### Practice Exercise

**Scenario:** Set up the complete daily operations schedule for a short-term rental operation. The operator is in the US/Eastern timezone and the rhythm follows the pattern from the daily-ops-rhythm skill:

- 6:30 AM: System health check and PMS scan
- 7:00 AM: Morning briefing
- 9:00 AM weekdays: Client project standup
- Every 15 minutes during business hours: New booking monitor
- 2:00 PM: Guest mid-stay check-ins
- 5:00 PM: EOD status report
- 8:00 PM: Next-day prep
- First Monday of month at 9 AM: Monthly revenue report

**Task:** Create all 8 scheduled jobs with appropriate configuration.

```text
{{scheduler(action="create_job", name="system-health-check", cron="30 6 * * *", timezone="US/Eastern", task="workflow:system-health-pms-scan", config={"overlap_policy": "skip", "retry_on_failure": true, "max_retries": 3})}}
```

```text
{{scheduler(action="create_job", name="morning-briefing", cron="0 7 * * *", timezone="US/Eastern", task="workflow:morning-briefing-assembly", config={"overlap_policy": "skip", "retry_on_failure": true, "max_retries": 2, "retry_delay": "5m"})}}
```

```text
{{scheduler(action="create_job", name="client-standup", cron="0 9 * * 1-5", timezone="US/Eastern", task="workflow:client-project-standup", config={"overlap_policy": "skip"})}}
```

```text
{{scheduler(action="create_job", name="booking-monitor", interval="15m", task="workflow:check-new-bookings", config={"active_hours": {"start": "06:00", "end": "22:00"}, "overlap_policy": "skip"})}}
```

**Self-check:** Count the total job executions per day on a weekday vs. a weekend. Weekdays should have more due to the client standup. If your booking monitor runs 24/7 instead of just business hours, you are generating unnecessary load and potential notification noise during off-hours.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Using server timezone instead of explicit timezone | Default behavior, laziness | Always pass `timezone` parameter; never rely on defaults |
| No overlap policy | Not thinking about execution duration | Set `overlap_policy` to "skip" or "queue" on every recurring job |
| Scheduling too many jobs at the same minute | Round numbers feel clean | Stagger by 1-2 minutes to avoid resource contention: `:00`, `:02`, `:04` |
| Not testing DST transitions | Only breaks twice a year | Test with mock times at 1:59 AM and 3:01 AM on transition dates |

---

## Lesson: Approval Workflow Patterns

### Why This Matters

Approval workflows are the bridge between automation and human judgment. Fully autonomous systems are fast but dangerous for anything that represents your business to the outside world. Fully manual systems are safe but slow and unsustainable.

The draft-review-approve pattern gives you the best of both worlds: AI speed for content generation with human judgment for quality control. But poorly implemented approval patterns create their own problems:

- **Approval fatigue** — Too many approvals and the operator starts blindly approving everything, defeating the purpose
- **Bottlenecks** — A single approver creates a queue that delays time-sensitive communications
- **Timeout chaos** — Messages expire before being reviewed, or worse, auto-send without review
- **Lost context** — The approver does not have enough information to make a good decision

The approval-workflow skill defines the standard pattern. This lesson teaches you how to implement it correctly and handle the edge cases that arise in production.

### How to Think About It

**The Draft-Review-Approve Cycle**

The core pattern from the approval-workflow skill:

```text
DRAFT                    REVIEW                   EXECUTE

AI generates       ──>  Operator sees in    ──>  Based on response:
message draft           Telegram with              send  → deliver as-is
                        approval prefix            skip  → discard
                                                   edit  → revise & re-present
```

**Format of approval requests:**

```text
[APPROVE] {message_type} for {recipient_name}:

{draft message content}

Reply: send | skip | edit: {changes}
```

**Approval Commands**

| Command | Action | Shortcut |
|---|---|---|
| `send` | Deliver the draft as-is | `s` |
| `skip` | Discard, no action | `sk` |
| `edit: {changes}` | Revise per instructions, re-present | `edit: shorter tone` |
| `send all` | Approve all pending in batch | — |
| `skip all` | Discard all pending in batch | — |

Commands are case-insensitive. The system recognizes partial matches for convenience.

**Which Messages Need Approval**

Not everything needs approval. The guideline: if a message represents your business to an external party, it needs approval. Internal operational messages do not.

| Needs Approval | Does Not Need Approval |
|---|---|
| Guest pre-arrival messages | Cleaning dispatch |
| Review solicitations | New booking alerts |
| Client proposals | Morning briefing (internal) |
| Mid-stay check-ins | EOD status (internal) |

**Timeout Strategies**

Every approval stage must have a timeout. The question is what to do when it fires:

| Strategy | When to Use | Risk |
|---|---|---|
| Auto-skip | Non-critical, time-sensitive messages | Message never sent; may miss engagement window |
| Escalate | Critical messages with backup approvers | Adds complexity; backup may also be unavailable |
| Auto-approve | Low-risk messages with high-quality drafts | Message sent without review; brand risk |
| Queue for next batch | Non-urgent messages | Delay is acceptable; builds up pending queue |

### Step-by-Step Approach

**Step 1: Build a basic approval workflow**

```text
{{workflow_engine(action="create", name="guest-message-approval", version=1, stages=[{"name": "gather_context", "type": "action", "action": "fetch_guest_and_booking_details"}, {"name": "generate_draft", "type": "action", "action": "ai_draft_guest_message"}, {"name": "format_approval", "type": "action", "action": "format_telegram_approval_request"}, {"name": "send_for_review", "type": "action", "action": "telegram_send_approval"}, {"name": "await_response", "type": "approval", "timeout": "2h", "timeout_action": "skip"}, {"name": "process_send", "type": "action", "action": "deliver_message_to_guest"}, {"name": "process_edit", "type": "action", "action": "revise_draft_and_resubmit"}, {"name": "process_skip", "type": "action", "action": "log_skipped_message"}], transitions=[{"from": "gather_context", "to": "generate_draft", "condition": "always"}, {"from": "generate_draft", "to": "format_approval", "condition": "always"}, {"from": "format_approval", "to": "send_for_review", "condition": "always"}, {"from": "send_for_review", "to": "await_response", "condition": "always"}, {"from": "await_response", "to": "process_send", "condition": "response == 'send'"}, {"from": "await_response", "to": "process_edit", "condition": "response.startsWith('edit')"}, {"from": "await_response", "to": "process_skip", "condition": "response == 'skip' OR timeout"}, {"from": "process_edit", "to": "send_for_review", "condition": "always"}])}}
```

Note the `process_edit` stage transitions back to `send_for_review`, creating a revision loop.

**Step 2: Implement batch approval**

When multiple drafts are generated in one run (e.g., 3 guests checking in tomorrow):

```text
{{workflow_engine(action="create", name="batch-approval", version=1, stages=[{"name": "generate_all_drafts", "type": "action", "action": "batch_draft_messages"}, {"name": "send_individual_approvals", "type": "action", "action": "telegram_send_batch_approvals"}, {"name": "send_summary", "type": "action", "action": "telegram_send_batch_summary"}, {"name": "collect_responses", "type": "approval", "mode": "batch", "timeout": "4h", "timeout_action": "skip_remaining"}, {"name": "execute_approved", "type": "action", "action": "deliver_approved_messages"}, {"name": "log_results", "type": "action", "action": "log_batch_outcome"}], transitions=[{"from": "generate_all_drafts", "to": "send_individual_approvals", "condition": "context.drafts.length > 0"}, {"from": "generate_all_drafts", "to": "COMPLETED", "condition": "context.drafts.length == 0"}, {"from": "send_individual_approvals", "to": "send_summary", "condition": "always"}, {"from": "send_summary", "to": "collect_responses", "condition": "always"}, {"from": "collect_responses", "to": "execute_approved", "condition": "all_responded OR timeout"}, {"from": "execute_approved", "to": "log_results", "condition": "always"}])}}
```

The summary message follows the pattern: "3 drafts pending approval. Reply 'send all' or review individually."

**Step 3: Configure timeout handling per message type**

```text
{{workflow_engine(action="create_config", name="approval-timeouts", config={"guest_pre_arrival": {"timeout": "2h", "on_timeout": "skip", "notify": true}, "guest_mid_stay": {"timeout": "4h", "on_timeout": "skip", "notify": true}, "review_solicitation": {"timeout": null, "on_timeout": "queue_next_batch", "notify": false}, "proposal_followup": {"timeout": "8h", "on_timeout": "skip_and_reschedule", "notify": true}})}}
```

**Step 4: Handle the escalation path**

For critical messages where skipping is not acceptable:

```text
{{workflow_engine(action="update_stage", workflow_id="guest-message-approval", stage="await_response", config={"escalation": {"enabled": true, "escalate_after": "1h", "escalate_to": "backup_operator_chat_id", "escalation_message": "Approval pending for {message_type} to {recipient}. Original reviewer has not responded in 1 hour."}, "timeout": "4h", "timeout_action": "escalate_to_manager"})}}
```

### Practice Exercise

**Scenario:** Build an approval workflow for client proposal follow-ups. Requirements:

1. Gather client data and last interaction date
2. Generate a follow-up message draft using AI
3. Send for operator approval with 8-hour timeout
4. On timeout: skip and reschedule for the next business day
5. On edit: revise and re-submit (max 3 revision rounds)
6. On approve: send via email and log in customer lifecycle
7. On skip: log reason and update next follow-up date

**Task:** Create the complete workflow with proper transitions, timeout handling, and revision loop limits.

```text
{{workflow_engine(action="create", name="proposal-followup-approval", version=1, stages=[{"name": "gather_client_data", "type": "action", "action": "customer_lifecycle_fetch"}, {"name": "check_eligible", "type": "decision", "condition": "context.days_since_last_contact >= 3"}, {"name": "generate_followup", "type": "action", "action": "ai_draft_followup"}, {"name": "submit_for_approval", "type": "action", "action": "telegram_send_approval"}, {"name": "await_decision", "type": "approval", "timeout": "8h", "timeout_action": "skip_and_reschedule"}, {"name": "send_followup", "type": "action", "action": "email_send_to_client"}, {"name": "log_sent", "type": "action", "action": "customer_lifecycle_log_contact"}, {"name": "revise_draft", "type": "action", "action": "ai_revise_followup", "guards": [{"field": "context.revision_count", "operator": "less_than", "value": 3}]}, {"name": "skip_and_reschedule", "type": "action", "action": "reschedule_followup_next_business_day"}, {"name": "log_skipped", "type": "action", "action": "customer_lifecycle_log_skip"}], transitions=[{"from": "gather_client_data", "to": "check_eligible", "condition": "always"}, {"from": "check_eligible", "to": "generate_followup", "condition": "eligible"}, {"from": "check_eligible", "to": "COMPLETED", "condition": "not_eligible"}, {"from": "generate_followup", "to": "submit_for_approval", "condition": "always"}, {"from": "submit_for_approval", "to": "await_decision", "condition": "always"}, {"from": "await_decision", "to": "send_followup", "condition": "approved"}, {"from": "await_decision", "to": "revise_draft", "condition": "edit"}, {"from": "await_decision", "to": "skip_and_reschedule", "condition": "skipped OR timeout"}, {"from": "send_followup", "to": "log_sent", "condition": "always"}, {"from": "revise_draft", "to": "submit_for_approval", "condition": "always"}, {"from": "skip_and_reschedule", "to": "log_skipped", "condition": "always"}])}}
```

**Self-check:** What happens on the 4th revision attempt? The guard on `revise_draft` will fail because `revision_count >= 3`. Your workflow needs a transition from the guard failure to a handler that auto-skips or sends a "too many revisions, please approve or skip" message. Trace that path explicitly.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| No timeout on approval stages | Assuming operator always responds | Every approval stage must have a timeout; defaults are dangerous |
| Unlimited revision loops | Not capping edit rounds | Set a revision limit (3 is reasonable) with a clear exit path |
| Approval fatigue from too many requests | Approving everything because it is annoying | Categorize what truly needs approval vs. what can auto-send |
| Not logging approval decisions | Only caring about the final action | Log the operator's exact response; it is audit trail gold |

---

## Lesson: Agent Orchestration

### Why This Matters

Complex automations rarely involve a single agent doing a single thing. Real-world operations require multiple agents coordinating across different tasks, data sources, and timelines. Without proper orchestration:

- **Agents duplicate work** — Two agents fetch the same data independently, wasting resources and risking inconsistency
- **Handoffs lose context** — Agent A generates data that Agent B needs, but the handoff drops critical details
- **Parallel execution is chaotic** — Multiple agents running simultaneously produce race conditions and conflicting outputs
- **Failures cascade** — One agent's failure brings down an entire multi-agent pipeline because dependencies are implicit

Agent orchestration is the discipline of coordinating multiple agents so they work as a cohesive system rather than a collection of independent scripts.

**Single agent vs. orchestrated agents:**

| Aspect | Single Agent | Orchestrated Agents |
|---|---|---|
| Data scope | One data source, one output | Multiple sources, aggregated output |
| Failure impact | One task fails | Need to handle partial failures |
| Execution time | Sequential, predictable | Parallel possible, faster but complex |
| Context management | Self-contained | Shared context with isolation rules |

### How to Think About It

**Orchestration Patterns**

There are four fundamental patterns for agent coordination:

```text
SEQUENTIAL HANDOFF        FAN-OUT / FAN-IN         SUPERVISOR

  [Agent A]               [Orchestrator]            [Supervisor]
      |                    /     |     \              /   |   \
  context                [A]   [B]   [C]           [A]  [B]  [C]
      |                    \     |     /              \   |   /
  [Agent B]               [Aggregator]             [Supervisor]
      |                                             decides next
  context
      |
  [Agent C]


PIPELINE WITH FEEDBACK

  [Agent A] --> [Agent B] --> [Agent C]
       ^                          |
       |     feedback loop        |
       +--------------------------+
```

| Pattern | Use When | Example |
|---|---|---|
| Sequential Handoff | Each agent builds on the previous agent's output | Fetch data -> Analyze -> Draft message -> Send |
| Fan-out/Fan-in | Multiple independent tasks can run in parallel | Check 3 PMS systems simultaneously |
| Supervisor | A coordinator agent decides what to do based on results | Route inquiries to specialized agents |
| Pipeline with Feedback | Output quality needs iterative refinement | Generate draft -> Review -> Revise -> Re-review |

**Shared Context Rules**

When multiple agents share a context, you need clear rules to prevent conflicts:

1. **Write isolation** — Each agent writes to its own namespace within the context (`context.agent_a.results`, not `context.results`)
2. **Read access** — All agents can read the full context, but only write to their namespace
3. **Conflict resolution** — If two agents need to write to the same field, the orchestrator decides who wins
4. **Context snapshots** — Before each agent runs, snapshot the context so you can roll back if the agent fails

```text
Shared Context Structure:
{
  "global": {
    "workflow_id": "exec-123",
    "started_at": "2026-03-20T07:00:00Z"
  },
  "agent_pms_scanner": {
    "bookings": [...],
    "status": "complete"
  },
  "agent_weather": {
    "forecast": {...},
    "status": "complete"
  },
  "agent_composer": {
    "briefing_draft": "...",
    "status": "in_progress"
  }
}
```

### Step-by-Step Approach

**Step 1: Create a fan-out/fan-in orchestration**

```text
{{workflow_engine(action="create", name="morning-data-gather", version=1, orchestration="fan_out_fan_in", agents=[{"name": "pms_scanner", "task": "scan_pms_bookings", "timeout": "30s", "required": true}, {"name": "weather_agent", "task": "fetch_weather_forecast", "timeout": "10s", "required": false}, {"name": "calendar_agent", "task": "fetch_calendar_events", "timeout": "10s", "required": false}, {"name": "revenue_agent", "task": "fetch_daily_revenue", "timeout": "15s", "required": true}], aggregator={"task": "compile_morning_briefing", "wait_for": "all_required", "timeout": "60s"})}}
```

The `required` flag determines behavior when an agent fails:

- Required agent fails = entire orchestration fails
- Optional agent fails = orchestration continues without that agent's data

**Step 2: Implement a sequential handoff with context passing**

```text
{{workflow_engine(action="create", name="guest-communication-pipeline", version=1, orchestration="sequential", agents=[{"name": "data_gatherer", "task": "fetch_guest_profile_and_history", "output_key": "guest_data"}, {"name": "analyzer", "task": "analyze_guest_preferences", "input_keys": ["guest_data"], "output_key": "analysis"}, {"name": "composer", "task": "draft_personalized_message", "input_keys": ["guest_data", "analysis"], "output_key": "draft"}, {"name": "reviewer", "task": "quality_check_message", "input_keys": ["draft", "analysis"], "output_key": "review_result"}], on_failure="stop_and_report")}}
```

Each agent explicitly declares what it reads (`input_keys`) and what it writes (`output_key`). This makes data flow visible and debuggable.

**Step 3: Build a supervisor pattern**

```text
{{workflow_engine(action="create", name="inquiry-supervisor", version=1, orchestration="supervisor", supervisor={"task": "classify_and_route_inquiry", "max_iterations": 5}, agents=[{"name": "booking_handler", "task": "handle_booking_inquiry", "trigger_condition": "classification == 'booking'"}, {"name": "maintenance_handler", "task": "handle_maintenance_request", "trigger_condition": "classification == 'maintenance'"}, {"name": "general_handler", "task": "handle_general_question", "trigger_condition": "classification == 'general'"}, {"name": "escalation_handler", "task": "escalate_to_human", "trigger_condition": "classification == 'unknown' OR iterations > 3"}])}}
```

The supervisor runs first, classifies the input, and routes to the appropriate specialist agent. If the specialist's output is not satisfactory, the supervisor can re-route or escalate.

**Step 4: Monitor orchestration health**

```text
{{workflow_engine(action="get_orchestration_metrics", name="morning-data-gather", period="7d", metrics=["agent_success_rates", "agent_avg_duration", "fan_out_completion_rate", "aggregator_wait_time"])}}
```

### Practice Exercise

**Scenario:** Build an orchestrated workflow for handling a new booking event. When a new booking arrives:

1. In parallel: fetch guest history, check property availability conflicts, look up guest reviews from past stays
2. The supervisor analyzes results and decides: (a) standard welcome flow, (b) VIP flow (repeat guest with good history), or (c) flag for review (conflicting bookings or negative review history)
3. The chosen flow agent generates appropriate communications
4. Output goes through the approval pipeline

**Task:** Design and create this orchestration using the supervisor pattern with fan-out data gathering.

```text
{{workflow_engine(action="create", name="new-booking-orchestration", version=1, orchestration="hybrid", phases=[{"name": "gather", "type": "fan_out_fan_in", "agents": [{"name": "guest_history", "task": "fetch_guest_history", "required": true}, {"name": "availability_check", "task": "check_conflicts", "required": true}, {"name": "review_lookup", "task": "fetch_past_reviews", "required": false}]}, {"name": "route", "type": "supervisor", "supervisor": {"task": "classify_booking_tier"}, "agents": [{"name": "standard_flow", "task": "standard_welcome_pipeline", "trigger_condition": "tier == 'standard'"}, {"name": "vip_flow", "task": "vip_welcome_pipeline", "trigger_condition": "tier == 'vip'"}, {"name": "review_flow", "task": "flag_for_manual_review", "trigger_condition": "tier == 'flagged'"}]}, {"name": "approve", "type": "sequential", "agents": [{"name": "approval", "task": "approval_cycle", "config": {"timeout": "2h"}}]}])}}
```

**Self-check:** What happens if the guest history agent fails but the other two succeed? Since it is marked `required: true`, the gather phase fails. Is that the right behavior? For a new booking, you might want to proceed with a standard flow even without history (the guest might be new). Consider whether `required: true` is correct for each agent.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| All agents marked as required | Defaulting to safe behavior | Only mark agents as required if the workflow truly cannot proceed without them |
| No timeout on individual agents | Trusting external services to respond quickly | Set timeouts on every agent; one slow agent should not block the entire orchestration |
| Flat context without namespacing | Simpler to write initially | Use namespaced context; conflicts in flat contexts are nearly impossible to debug |
| No fallback for supervisor routing | Assuming classification always works | Always include an "unknown" or "default" route that gracefully handles unrecognized inputs |

---

## Lesson: Error Handling and Recovery

### Why This Matters

Every automation will fail. The network will go down. The API will return an error. The database will be temporarily unavailable. The external service will change its response format without warning.

The question is not whether your automations will fail, but how they will fail. Poorly handled failures cause:

- **Data corruption** — A half-completed workflow leaves the system in an inconsistent state
- **Silent failures** — The workflow stops but nobody is notified, and the task simply does not get done
- **Cascade failures** — One failing workflow triggers failures in downstream workflows that depend on its output
- **Duplicate actions** — A retry sends the same message twice because the first attempt partially succeeded

Robust error handling is what separates a prototype from a production system. It is also what lets you sleep at night.

### How to Think About It

**Error Categories**

Not all errors are the same. Your response should match the error type:

```text
ERRORS
  |
  +-- Transient (will resolve on their own)
  |     +-- Network timeout
  |     +-- Rate limit (429)
  |     +-- Service temporarily unavailable (503)
  |     +-- Database connection pool exhausted
  |
  +-- Permanent (will not resolve without intervention)
  |     +-- Authentication failure (401)
  |     +-- Resource not found (404)
  |     +-- Invalid input / validation error
  |     +-- Permission denied (403)
  |
  +-- Logic Errors (bug in your workflow)
        +-- Unexpected null value
        +-- Type mismatch
        +-- Infinite loop / max iterations exceeded
```

| Error Type | Strategy | Example |
|---|---|---|
| Transient | Retry with backoff | Network timeout: retry in 5s, 15s, 45s |
| Permanent | Fail fast, notify, log | API key expired: stop, alert operator, log details |
| Logic | Fail fast, do not retry | Null pointer: retrying will produce the same error |

**Retry Strategies**

```text
FIXED DELAY          EXPONENTIAL BACKOFF      EXPONENTIAL + JITTER

  ●─5s─●─5s─●        ●─2s─●─4s─●──8s──●      ●─2.3s─●─4.7s─●──9.1s──●
  Same delay          Doubles each time        Doubles + random offset
  every time          Predictable              Prevents thundering herd
```

| Strategy | When to Use | Configuration |
|---|---|---|
| Fixed delay | Simple, low-frequency retries | `retry_delay: "5s", max_retries: 3` |
| Exponential backoff | API rate limits, service recovery | `initial_delay: "2s", multiplier: 2, max_delay: "60s"` |
| Exponential + jitter | Multiple workflows hitting the same service | `initial_delay: "2s", multiplier: 2, jitter: "1s"` |

**Circuit Breaker Pattern**

When an external service is consistently failing, stop hitting it. The circuit breaker prevents your system from wasting resources on a service that is down.

```text
CLOSED (normal)          OPEN (service down)        HALF-OPEN (testing)

  Requests flow     ──>  All requests fail    ──>  One test request
  normally                immediately                   |
       |                  (no actual call)         success? → CLOSED
  failure count                |                   failure? → OPEN
  exceeds threshold       after cooldown
       |                  period expires
  → OPEN                  → HALF-OPEN
```

```text
{{workflow_engine(action="create_circuit_breaker", name="pms-api-breaker", config={"failure_threshold": 5, "cooldown_period": "60s", "half_open_max_requests": 1, "monitored_service": "pms_api", "on_open": "notify_operator"})}}
```

**Dead Letter Queue**

When a workflow execution fails and cannot be retried, send it to the dead letter queue (DLQ) instead of losing it. The DLQ holds failed executions for later investigation and manual replay.

```text
Failed Execution ──> Retry Logic ──> Still failing? ──> Dead Letter Queue
                                                              |
                                          Operator investigates and either:
                                            - Fixes the issue and replays
                                            - Marks as permanently failed
                                            - Modifies data and replays
```

### Step-by-Step Approach

**Step 1: Add retry configuration to a workflow**

```text
{{workflow_engine(action="update", workflow_id="morning-briefing-assembly", error_handling={"default_retry": {"strategy": "exponential_backoff", "initial_delay": "5s", "multiplier": 2, "max_delay": "60s", "max_retries": 3}, "stage_overrides": {"fetch_pms_data": {"strategy": "exponential_backoff", "max_retries": 5, "initial_delay": "2s"}, "send_briefing": {"strategy": "fixed", "delay": "10s", "max_retries": 2}}, "on_exhausted_retries": "dead_letter_queue", "notify_on_failure": true})}}
```

**Step 2: Configure a circuit breaker for an external service**

```text
{{workflow_engine(action="create_circuit_breaker", name="pms-api", config={"failure_threshold": 5, "window": "60s", "cooldown_period": "120s", "on_open": {"action": "telegram_notify", "message": "PMS API circuit breaker OPEN. Service appears down. Workflows using PMS data will fail fast until service recovers."}, "on_close": {"action": "telegram_notify", "message": "PMS API circuit breaker CLOSED. Service recovered. Normal operations resumed."}})}}
```

**Step 3: Set up a dead letter queue**

```text
{{workflow_engine(action="configure_dlq", name="main-dlq", config={"retention_period": "7d", "max_entries": 1000, "notify_on_entry": true, "notification_channel": "telegram", "auto_categorize": true})}}
```

**Step 4: Review and process the dead letter queue**

```text
{{workflow_engine(action="list_dlq", name="main-dlq", status="pending")}}
```

For each entry, decide: fix and replay, or mark as permanently failed.

```text
{{workflow_engine(action="replay_dlq_entry", dlq_entry_id="dlq-entry-001", modifications={"context.api_key": "new-key-value"})}}
```

**Step 5: Implement graceful degradation**

When a non-critical service is down, continue with reduced functionality:

```text
{{workflow_engine(action="update_stage", workflow_id="morning-briefing-assembly", stage="fetch_weather", config={"on_failure": "graceful_degrade", "degraded_behavior": {"set_context": {"weather_data": null, "weather_available": false}, "continue_to": "assemble_briefing"}, "degraded_message": "Weather data unavailable. Briefing will be sent without weather section."})}}
```

### Practice Exercise

**Scenario:** Your booking monitor workflow runs every 15 minutes and calls an external PMS API. Over the past 24 hours, the API has been intermittently failing with 503 errors, causing:

- 8 failed executions sitting in the dead letter queue
- 3 duplicate booking notifications (partial failure: notification sent, but status update failed, so next run re-detected the booking)
- Operator received 8 error notifications and is now ignoring all notifications

**Task:**

1. Add a circuit breaker to the PMS API calls
2. Make the booking detection idempotent (do not re-notify for already-processed bookings)
3. Configure appropriate retry strategy
4. Set up graceful degradation for non-critical stages
5. Clean up the dead letter queue

```text
{{workflow_engine(action="update", workflow_id="check-new-bookings", error_handling={"circuit_breaker": "pms-api", "idempotency": {"key": "context.booking_id", "store": "processed_bookings", "ttl": "48h"}, "retry": {"strategy": "exponential_backoff", "initial_delay": "10s", "max_retries": 3}, "stages": {"notify_operator": {"on_failure": "graceful_degrade", "fallback": "queue_for_next_run"}, "update_booking_status": {"on_failure": "dead_letter_queue"}}, "on_exhausted_retries": "dead_letter_queue"})}}
```

**Self-check:** After implementing idempotency, replay the 8 dead letter queue entries. How many should actually produce a notification? Only the ones where the booking has not yet been processed. The idempotency check will skip bookings that were already notified, preventing duplicates even during replay. Verify this by checking the `processed_bookings` store.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Retrying permanent errors | Not categorizing error types | Check HTTP status code: 4xx = permanent (do not retry), 5xx = transient (retry) |
| No idempotency on side-effecting stages | Not thinking about partial failures | Add idempotency keys to any stage that sends messages, charges money, or updates external state |
| Too many retry attempts | "More retries = more reliable" thinking | 3-5 retries with backoff is usually sufficient; more just delays the inevitable |
| Alert flooding on repeated failures | One alert per failure, not per incident | Use circuit breaker pattern; alert once when circuit opens, once when it closes |
