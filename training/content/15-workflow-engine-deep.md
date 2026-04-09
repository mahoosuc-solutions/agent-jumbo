# Module 15: Workflow Engine Deep Dive

> **Learning Path:** Workflow & Automation Engineer
> **Audience:** Technical operators building automations
> **Prerequisites:** Basic workflow_design skill

---

## Lesson: Workflow Engine Architecture

### Why This Matters

The workflow engine is the central nervous system of every automation you build. Without understanding how it works internally, you will:

- **Build fragile workflows** that break when edge cases appear and you cannot diagnose why
- **Misuse execution contexts** leading to data leaks between workflow runs or lost state
- **Hit performance walls** because you did not understand how the engine schedules and prioritizes work
- **Struggle to debug** production failures because you cannot read the engine's internal state

Every automation that "randomly stops working" can be traced to a misunderstanding of engine internals. The operators who build reliable, production-grade automations are the ones who understand the machine underneath.

**What is at stake:**

| Failure Mode | Symptom | Root Cause |
|---|---|---|
| Workflow silently stops | No error, no output, no log | State machine entered terminal state without completion handler |
| Data appears from a previous run | Wrong guest name in message | Execution context not isolated between runs |
| Workflow runs twice | Duplicate messages sent | No idempotency guard on trigger |
| Workflow takes 10x longer than expected | Timeouts, slow responses | Synchronous execution where parallel was possible |

Understanding the engine is not academic. It is the difference between automations that work in demos and automations that work at 3 AM when nobody is watching.

### How to Think About It

**The Engine as a State Machine**

At its core, the workflow engine is a finite state machine. Every workflow you create is a definition of states (stages) and the rules for moving between them (transitions).

```text
                    +------------+
                    |  CREATED   |
                    +-----+------+
                          |
                    trigger event
                          |
                    +-----v------+
             +----->|  RUNNING   |<-----+
             |      +-----+------+      |
             |            |             |
          retry      stage complete   error
          (if allowed)    |          (recoverable)
             |      +-----v------+      |
             +------+  STAGE_N   +------+
                    +-----+------+
                          |
                   all stages done
                          |
                    +-----v------+
                    | COMPLETED  |
                    +------------+

                    +------------+
                    |   FAILED   |  <-- unrecoverable error
                    +------------+

                    +------------+
                    |  CANCELLED |  <-- manual or timeout
                    +------------+
```

**Key concepts:**

1. **Workflow Definition** — The blueprint. It describes stages, transitions, and parameters. It does not execute anything. Think of it as a class, not an instance.
2. **Workflow Execution** — A single run of a workflow definition. Think of it as an instance. Each execution has its own isolated context, its own state, and its own history.
3. **Execution Context** — The data bag that travels with an execution. Each stage can read from it and write to it. It is scoped to a single execution and never shared.
4. **Stage** — A unit of work within a workflow. Stages have an entry action, optional guard conditions, and exit transitions.
5. **Transition** — A rule that moves the execution from one stage to the next. Transitions can be conditional, timed, or event-driven.

**Database Schema (Conceptual)**

```text
workflows
  ├── id (UUID)
  ├── name (string, unique)
  ├── version (integer)
  ├── stages (JSON array)
  ├── transitions (JSON array)
  ├── parameters (JSON schema)
  ├── created_at (timestamp)
  └── updated_at (timestamp)

workflow_executions
  ├── id (UUID)
  ├── workflow_id (FK → workflows.id)
  ├── status (enum: created, running, completed, failed, cancelled)
  ├── current_stage (string)
  ├── context (JSON object)
  ├── started_at (timestamp)
  ├── completed_at (timestamp)
  └── error (text, nullable)

execution_history
  ├── id (UUID)
  ├── execution_id (FK → workflow_executions.id)
  ├── stage (string)
  ├── action (string: enter, execute, exit, transition, error)
  ├── data (JSON object)
  ├── timestamp (timestamp)
  └── duration_ms (integer)
```

Every action the engine takes is recorded in `execution_history`. This is your audit trail, your debugging tool, and your performance profiler all in one.

### Step-by-Step Approach

**Step 1: Create a workflow definition**

Start with a simple sequential workflow to understand the fundamentals:

```text
{{workflow_engine(action="create", name="guest-checkout-followup", version=1, stages=[{"name": "gather_data", "type": "action", "action": "fetch_guest_details"}, {"name": "generate_message", "type": "action", "action": "draft_review_request"}, {"name": "await_approval", "type": "approval", "timeout": "4h"}, {"name": "send_message", "type": "action", "action": "send_to_guest"}], transitions=[{"from": "gather_data", "to": "generate_message", "condition": "always"}, {"from": "generate_message", "to": "await_approval", "condition": "always"}, {"from": "await_approval", "to": "send_message", "condition": "approved"}, {"from": "await_approval", "to": "COMPLETED", "condition": "skipped"}])}}
```

**Step 2: Inspect the workflow definition**

```text
{{workflow_engine(action="get", workflow_id="guest-checkout-followup")}}
```

Verify the stage order, transition conditions, and parameter schema before executing.

**Step 3: Understand execution context isolation**

Each execution gets its own context. When you start an execution, you pass initial parameters that seed the context:

```text
{{workflow_engine(action="execute", workflow_id="guest-checkout-followup", params={"guest_name": "Sarah Chen", "checkout_date": "2026-03-20", "property": "Lakeside Retreat"})}}
```

The context for this execution is completely isolated. If another execution of the same workflow starts for a different guest, they do not share data.

**Step 4: Monitor execution state**

```text
{{workflow_engine(action="get_status", execution_id="exec-a1b2c3")}}
```

This returns the current stage, context snapshot, and elapsed time. Use this for debugging and monitoring dashboards.

### Practice Exercise

**Scenario:** You need to build a workflow for handling new booking notifications. The workflow should:

1. Fetch booking details from the PMS
2. Check if the guest is a repeat visitor
3. Generate a personalized pre-arrival message
4. Send for operator approval
5. On approval, send the message; on skip, log and complete

**Task:**

1. Design the stage list and transitions on paper first
2. Create the workflow definition using the engine
3. Start a test execution with sample data
4. Query the execution status at each stage

```text
{{workflow_engine(action="create", name="new-booking-welcome", version=1, stages=[{"name": "fetch_booking", "type": "action", "action": "pms_get_booking"}, {"name": "check_repeat_guest", "type": "decision", "condition": "context.guest_history.length > 0"}, {"name": "draft_first_time", "type": "action", "action": "draft_welcome_new"}, {"name": "draft_returning", "type": "action", "action": "draft_welcome_repeat"}, {"name": "approve_message", "type": "approval", "timeout": "2h"}, {"name": "send_message", "type": "action", "action": "send_to_guest"}], transitions=[{"from": "fetch_booking", "to": "check_repeat_guest", "condition": "always"}, {"from": "check_repeat_guest", "to": "draft_returning", "condition": "is_repeat"}, {"from": "check_repeat_guest", "to": "draft_first_time", "condition": "is_new"}, {"from": "draft_first_time", "to": "approve_message", "condition": "always"}, {"from": "draft_returning", "to": "approve_message", "condition": "always"}, {"from": "approve_message", "to": "send_message", "condition": "approved"}])}}
```

**Self-check:** Does your workflow handle the case where the PMS fetch fails? If not, you need an error transition from `fetch_booking` to a failure handler. Production workflows always account for failures at every stage.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Sharing context between executions | Storing state in global variables instead of execution context | Always use `context.*` for execution-scoped data |
| No error transitions | Assuming every stage succeeds | Add error transitions from every action stage to a handler |
| Hardcoding values in stage definitions | Quick prototyping habits | Use workflow parameters and context variables |
| Not versioning workflow definitions | Editing live workflows | Always increment version; never modify a running definition |

---

## Lesson: Stage Design and Transitions

### Why This Matters

Stages are the building blocks of every workflow. Poorly designed stages create workflows that are rigid, hard to debug, and impossible to reuse. Well-designed stages create workflows that are modular, testable, and composable.

The difference between a junior automation builder and a senior one is not the complexity of their workflows. It is the quality of their stage design. A senior builder creates stages that can be rearranged, reused, and extended without rewriting the entire workflow.

**The cost of bad stage design:**

- A monolithic "do everything" stage cannot be partially retried when it fails halfway through
- Stages without guard conditions allow invalid data to flow downstream, causing failures far from the source
- Missing transition rules create "dead end" states where executions hang forever
- Tightly coupled stages cannot be reused in other workflows, so you rebuild the same logic repeatedly

### How to Think About It

**Stage Types**

The engine supports four fundamental stage types. Every workflow is composed of combinations of these:

```text
SEQUENTIAL          PARALLEL            CONDITIONAL         APPROVAL

  [A]               [A]                    [A]                [A]
   |               / | \                   |                   |
  [B]           [B] [C] [D]          condition?          [WAIT for
   |               \ | /              /       \           human input]
  [C]               [E]            [B]       [C]              |
                                     \       /            [B or SKIP]
                                      [D]
```

| Stage Type | Use When | Example |
|---|---|---|
| Sequential | Each step depends on the previous | Fetch data, then process, then send |
| Parallel | Steps are independent and can run simultaneously | Check availability across 3 systems at once |
| Conditional | Next step depends on data or decision | Route to different handlers based on guest type |
| Approval | Human input is required before proceeding | Operator reviews draft message before sending |

**Guard Conditions**

Guards are preconditions that must be true before a stage can execute. They prevent invalid states and catch problems early.

```text
Stage: send_message
Guards:
  - context.message_draft IS NOT NULL
  - context.recipient_email IS NOT NULL
  - context.approval_status == "approved"
```

If any guard fails, the stage does not execute and the engine routes to an error handler or pauses for intervention. Guards are your safety net.

**Transition Rules**

Transitions define the edges in your state machine graph. Each transition has:

- **From** — The source stage
- **To** — The destination stage
- **Condition** — When this transition fires (always, on_success, on_error, conditional expression)
- **Priority** — When multiple transitions match, which one wins (lower number = higher priority)

```text
transitions:
  - from: "check_inventory"
    to: "fulfill_order"
    condition: "context.in_stock == true"
    priority: 1
  - from: "check_inventory"
    to: "backorder_notification"
    condition: "context.in_stock == false"
    priority: 1
  - from: "check_inventory"
    to: "error_handler"
    condition: "on_error"
    priority: 0    # errors always take precedence
```

### Step-by-Step Approach

**Step 1: Design a workflow with parallel stages**

When stages are independent, run them in parallel to cut execution time:

```text
{{workflow_engine(action="create", name="morning-briefing-assembly", version=1, stages=[{"name": "start", "type": "action", "action": "init_briefing_context"}, {"name": "fetch_pms_data", "type": "action", "action": "pms_scan", "group": "parallel_fetch"}, {"name": "fetch_weather", "type": "action", "action": "weather_lookup", "group": "parallel_fetch"}, {"name": "fetch_calendar", "type": "action", "action": "calendar_today", "group": "parallel_fetch"}, {"name": "assemble_briefing", "type": "action", "action": "compile_morning_digest"}, {"name": "send_briefing", "type": "action", "action": "telegram_send"}], transitions=[{"from": "start", "to": "parallel_fetch", "condition": "always"}, {"from": "parallel_fetch", "to": "assemble_briefing", "condition": "all_complete"}, {"from": "assemble_briefing", "to": "send_briefing", "condition": "always"}])}}
```

Stages in the same `group` run simultaneously. The engine waits for all to complete before moving to the next transition.

**Step 2: Add guard conditions to protect critical stages**

```text
{{workflow_engine(action="update_stage", workflow_id="morning-briefing-assembly", stage="send_briefing", guards=[{"field": "context.briefing_content", "operator": "is_not_null"}, {"field": "context.briefing_content.length", "operator": "greater_than", "value": 50}])}}
```

This prevents sending an empty or stub briefing if an upstream stage failed silently.

**Step 3: Design conditional branching**

```text
{{workflow_engine(action="create", name="inquiry-router", version=1, stages=[{"name": "classify_inquiry", "type": "action", "action": "ai_classify_message"}, {"name": "handle_booking", "type": "action", "action": "process_booking_inquiry"}, {"name": "handle_maintenance", "type": "action", "action": "process_maintenance_request"}, {"name": "handle_general", "type": "action", "action": "process_general_question"}, {"name": "respond", "type": "action", "action": "send_response"}], transitions=[{"from": "classify_inquiry", "to": "handle_booking", "condition": "context.category == 'booking'"}, {"from": "classify_inquiry", "to": "handle_maintenance", "condition": "context.category == 'maintenance'"}, {"from": "classify_inquiry", "to": "handle_general", "condition": "context.category == 'general'"}, {"from": "handle_booking", "to": "respond", "condition": "always"}, {"from": "handle_maintenance", "to": "respond", "condition": "always"}, {"from": "handle_general", "to": "respond", "condition": "always"}])}}
```

**Step 4: Validate your transitions for completeness**

```text
{{workflow_engine(action="validate", workflow_id="inquiry-router")}}
```

The validator checks for unreachable stages, missing transitions, dead-end states, and conflicting conditions. Always validate before deploying.

### Practice Exercise

**Scenario:** Build a property turnover workflow that handles the sequence after a guest checks out:

1. Receive checkout notification
2. In parallel: generate cleaning checklist, check next booking details, assess maintenance needs
3. Dispatch cleaning team (conditional: if next booking is same-day, mark as URGENT)
4. Wait for cleaning confirmation
5. If next booking exists, send pre-arrival message for approval

**Task:** Design and create this workflow, paying attention to:

- Parallel stage grouping for the three independent checks
- Conditional logic for urgency determination
- An approval stage for the pre-arrival message
- Error handling if the cleaning team does not respond within 2 hours

```text
{{workflow_engine(action="create", name="property-turnover", version=1, stages=[{"name": "receive_checkout", "type": "action", "action": "process_checkout_event"}, {"name": "gen_cleaning_list", "type": "action", "action": "generate_checklist", "group": "parallel_assess"}, {"name": "check_next_booking", "type": "action", "action": "pms_next_reservation", "group": "parallel_assess"}, {"name": "assess_maintenance", "type": "action", "action": "check_property_condition", "group": "parallel_assess"}, {"name": "determine_urgency", "type": "decision", "condition": "context.next_booking.is_same_day"}, {"name": "dispatch_urgent", "type": "action", "action": "dispatch_cleaning_urgent"}, {"name": "dispatch_normal", "type": "action", "action": "dispatch_cleaning_standard"}, {"name": "await_cleaning", "type": "approval", "timeout": "2h", "timeout_action": "escalate"}, {"name": "draft_prearrrival", "type": "action", "action": "draft_welcome_message"}, {"name": "approve_message", "type": "approval", "timeout": "2h"}, {"name": "send_welcome", "type": "action", "action": "send_to_guest"}], transitions=[{"from": "receive_checkout", "to": "parallel_assess", "condition": "always"}, {"from": "parallel_assess", "to": "determine_urgency", "condition": "all_complete"}, {"from": "determine_urgency", "to": "dispatch_urgent", "condition": "is_same_day"}, {"from": "determine_urgency", "to": "dispatch_normal", "condition": "not_same_day"}, {"from": "dispatch_urgent", "to": "await_cleaning", "condition": "always"}, {"from": "dispatch_normal", "to": "await_cleaning", "condition": "always"}, {"from": "await_cleaning", "to": "draft_prearrrival", "condition": "confirmed"}, {"from": "draft_prearrrival", "to": "approve_message", "condition": "context.next_booking != null"}, {"from": "approve_message", "to": "send_welcome", "condition": "approved"}])}}
```

**Self-check:** What happens when there is no next booking? Your workflow should gracefully complete after cleaning confirmation without attempting to draft a pre-arrival message. Trace every path through your state machine and verify each one reaches a terminal state.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Creating one giant stage that does everything | Faster to write initially | Break into stages of 1 responsibility each; easier to retry and debug |
| No guard conditions on critical stages | Trusting upstream stages to always produce valid data | Add guards; they cost nothing and prevent cascading failures |
| Forgetting the "else" branch in conditionals | Only thinking about the happy path | Every decision must have a default/fallback transition |
| Parallel stages that actually depend on each other | Misidentifying dependencies | Map data dependencies first; only parallelize truly independent work |

---

## Lesson: Execution Tracking and History

### Why This Matters

When a workflow runs at 3 AM and produces the wrong output, or silently stops halfway through, your only witness is the execution history. Without proper tracking:

- You cannot distinguish between "it never ran" and "it ran and failed silently"
- You cannot identify which specific stage caused a failure in a 10-stage workflow
- You cannot measure performance to identify bottlenecks
- You have no audit trail to satisfy compliance requirements or client questions
- You cannot replay a failed execution without re-triggering the original event

Execution tracking is not a nice-to-have feature. It is the foundation of operational confidence. The operators who sleep well at night are the ones who know that every workflow run is fully recorded and inspectable.

**The real cost of poor tracking:**

| Situation | Without Tracking | With Tracking |
|---|---|---|
| Guest message sent with wrong name | Hours of investigation, blaming | 30-second query: stage 3 received stale PMS data |
| Workflow stopped running last Tuesday | Rebuild from scratch, no idea why | History shows: API key expired, stage 2 failed, no retry configured |
| Client asks "when was the last report sent?" | "I think it was... let me check" | Exact timestamp, recipient, content hash, delivery status |
| Performance degraded over time | No baseline to compare against | Duration trends show stage 4 went from 200ms to 8s after data growth |

### How to Think About It

**What Gets Recorded**

Every execution generates a history trail. Each entry captures a single atomic action:

```text
execution_history entry:
  execution_id: "exec-a1b2c3"
  stage: "generate_message"
  action: "execute"
  timestamp: "2026-03-20T07:15:32.451Z"
  duration_ms: 1823
  data: {
    "input": {"guest_name": "Sarah Chen", "template": "pre_arrival_v2"},
    "output": {"message_draft": "Hello Sarah, we're excited...", "word_count": 47},
    "metadata": {"model": "claude-3", "tokens_used": 312}
  }
```

**History Action Types**

| Action | Meaning | When It Fires |
|---|---|---|
| `enter` | Execution arrived at this stage | Stage is about to begin |
| `guard_check` | Guard conditions evaluated | Before stage execution |
| `execute` | Stage action performed | During stage execution |
| `exit` | Stage completed, preparing to transition | After stage execution |
| `transition` | Moving from one stage to another | Between stages |
| `error` | Something went wrong | On any failure |
| `retry` | Stage is being re-executed | After a recoverable error |
| `timeout` | Stage exceeded its time limit | When timeout triggers |
| `approval_request` | Waiting for human input | When approval stage starts |
| `approval_response` | Human provided input | When operator responds |

**Reading an Execution Timeline**

A healthy execution timeline looks like a clean sequence of enter-execute-exit-transition cycles:

```text
07:15:30.100  fetch_booking       enter
07:15:30.105  fetch_booking       execute     {duration: 1200ms}
07:15:31.305  fetch_booking       exit        {status: "success"}
07:15:31.310  fetch_booking       transition  {to: "generate_message"}
07:15:31.315  generate_message    enter
07:15:31.320  generate_message    guard_check {passed: true}
07:15:31.325  generate_message    execute     {duration: 1823ms}
07:15:33.148  generate_message    exit        {status: "success"}
...
```

A problematic timeline shows gaps, errors, or unexpected patterns:

```text
07:15:30.100  fetch_booking       enter
07:15:30.105  fetch_booking       execute     {duration: 30200ms}  ← SLOW
07:16:00.305  fetch_booking       error       {type: "timeout"}
07:16:00.310  fetch_booking       retry       {attempt: 1}
07:16:00.315  fetch_booking       execute     {duration: 1100ms}
07:16:01.415  fetch_booking       exit        {status: "success"}
```

### Step-by-Step Approach

**Step 1: Query execution history for a specific run**

```text
{{workflow_engine(action="get_history", execution_id="exec-a1b2c3")}}
```

This returns the full timeline. Scan for `error` and `retry` actions first.

**Step 2: Filter history by stage to debug a specific problem**

```text
{{workflow_engine(action="get_history", execution_id="exec-a1b2c3", filter={"stage": "generate_message"})}}
```

**Step 3: Query aggregate performance across executions**

```text
{{workflow_engine(action="get_metrics", workflow_id="guest-checkout-followup", period="7d", metrics=["avg_duration", "success_rate", "stage_durations", "error_count"])}}
```

This shows trends. If `avg_duration` is climbing, drill into `stage_durations` to find the bottleneck.

**Step 4: Replay a failed execution**

When an execution fails due to a transient error (API timeout, rate limit), replay it without re-triggering the original event:

```text
{{workflow_engine(action="replay", execution_id="exec-a1b2c3", from_stage="generate_message")}}
```

Replay creates a new execution that starts from the specified stage, using the original execution's context up to that point. This is invaluable for recovering from transient failures without losing work done in earlier stages.

**Step 5: Set up alerts on execution patterns**

```text
{{workflow_engine(action="create_alert", workflow_id="guest-checkout-followup", conditions=[{"metric": "success_rate", "operator": "less_than", "value": 0.95, "window": "24h"}, {"metric": "avg_duration", "operator": "greater_than", "value": 30000, "window": "1h"}], notify="telegram")}}
```

### Practice Exercise

**Scenario:** Your morning briefing workflow has been reported as "flaky" by the operator. Some mornings it arrives on time, some mornings it is late, and twice this week it did not arrive at all.

**Task:**

1. Pull execution history for the last 7 days of the morning briefing workflow
2. Identify which executions failed and at which stage
3. Calculate average duration per stage to find bottlenecks
4. Determine the root cause and propose a fix

```text
{{workflow_engine(action="list_executions", workflow_id="morning-briefing-assembly", period="7d", status="all")}}
```

Then for each failed execution:

```text
{{workflow_engine(action="get_history", execution_id="exec-failed-1", filter={"action": "error"})}}
```

And for performance analysis:

```text
{{workflow_engine(action="get_metrics", workflow_id="morning-briefing-assembly", period="7d", metrics=["stage_durations", "p95_duration", "error_stages"])}}
```

**Self-check:** Did you find a pattern? Common causes of intermittent failures are: (1) external API rate limits that only trigger when multiple workflows run in the same time window, (2) database connection pool exhaustion during peak morning hours, (3) timeout values that are too tight for the slowest upstream service. Your fix should address the root cause, not just add more retries.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Ignoring history until something breaks | "It works, why look?" mindset | Review execution metrics weekly; catch degradation early |
| Replaying without understanding the failure | Urgency to fix production | Read the error history first; replaying a logic bug just repeats the bug |
| Not setting up execution alerts | Alert fatigue concerns | Start with just 2 alerts: success rate drop and duration spike |
| Logging too little context data | Privacy concerns or storage costs | Log inputs/outputs for action stages; redact sensitive fields explicitly |

---

## Lesson: Workflow Templates and Reuse

### Why This Matters

Without templates, every new workflow is built from scratch. This means:

- **Repeated effort** — You solve the same structural problems again and again (approval flows, error handling, notification patterns)
- **Inconsistent quality** — Each workflow handles errors, logging, and approvals differently depending on who built it and when
- **Knowledge silos** — The patterns that make one workflow reliable are locked in that workflow's definition, not shared
- **Slow onboarding** — New team members cannot learn from standardized examples because none exist

Templates transform workflow development from artisanal crafting into systematic engineering. A well-maintained template library means that building a new workflow takes minutes instead of hours, and the result is immediately production-grade.

**The template value multiplier:**

| Without Templates | With Templates |
|---|---|
| 2-4 hours to build a new approval workflow | 15 minutes to instantiate and customize |
| Each workflow has unique error handling (or none) | All workflows share battle-tested error handling |
| New team member takes weeks to build first workflow | New team member ships on day one using templates |
| Bug fixes applied to one workflow at a time | Fix the template, update all instances |

### How to Think About It

**What Makes a Good Template**

A template is not just a workflow definition with blanks to fill in. It is a reusable pattern that captures:

1. **Structure** — The stage sequence, transition rules, and parallel groupings
2. **Parameters** — The values that change per instance (names, timeouts, channels)
3. **Guards and Safety** — Error handling, timeout behavior, and validation rules
4. **Documentation** — What the template does, when to use it, and what parameters mean

```text
Template: approval-with-timeout
Parameters:
  - draft_action: string     # action that generates the draft
  - reviewer_channel: string # where to send for approval
  - timeout: duration        # how long to wait (default: 4h)
  - timeout_action: enum     # skip | escalate | auto_approve
  - on_approve: string       # action to run on approval
  - on_reject: string        # action to run on rejection

Stages:
  [generate_draft] → [send_for_review] → [await_approval] → [execute_decision]
                                               |
                                          [timeout_handler]
```

**Template Hierarchy**

Templates can be layered to maximize reuse:

```text
Base Templates (structural patterns)
  ├── sequential-with-error-handling
  ├── parallel-gather-and-process
  ├── approval-cycle
  └── scheduled-report

Composite Templates (combine base patterns)
  ├── daily-digest (sequential + scheduled-report)
  ├── guest-communication (sequential + approval-cycle)
  └── multi-source-report (parallel-gather + sequential)

Instance Workflows (from composite templates)
  ├── morning-briefing (from daily-digest)
  ├── pre-arrival-message (from guest-communication)
  └── weekly-revenue-report (from multi-source-report)
```

**Parameterization Best Practices**

Parameters should capture the differences between instances, not the similarities. If two instances only differ by 3 values, those 3 values are your parameters. Everything else is template structure.

| Parameter Type | Example | When to Use |
|---|---|---|
| String | `recipient_name`, `channel_id` | Names, identifiers, labels |
| Duration | `timeout`, `retry_delay` | Time-based configuration |
| Enum | `urgency: normal\|high\|critical` | Fixed set of options |
| Action reference | `draft_action: "generate_welcome"` | Pluggable behavior |
| JSON schema | `data_mapping: {...}` | Complex per-instance configuration |

### Step-by-Step Approach

**Step 1: Create a base template**

```text
{{workflow_engine(action="create_template", name="approval-cycle", description="Generic draft-review-approve pattern with timeout handling", parameters=[{"name": "draft_action", "type": "string", "required": true, "description": "Action that generates the draft content"}, {"name": "approval_channel", "type": "string", "default": "telegram", "description": "Channel for approval requests"}, {"name": "timeout", "type": "duration", "default": "4h", "description": "Time to wait for approval"}, {"name": "timeout_behavior", "type": "enum", "values": ["skip", "escalate", "auto_approve"], "default": "skip"}, {"name": "on_approve_action", "type": "string", "required": true, "description": "Action to execute on approval"}, {"name": "on_reject_action", "type": "string", "default": "log_skip", "description": "Action to execute on rejection"}], stages=[{"name": "generate_draft", "type": "action", "action": "{{draft_action}}"}, {"name": "send_for_review", "type": "action", "action": "send_approval_request", "config": {"channel": "{{approval_channel}}"}}, {"name": "await_response", "type": "approval", "timeout": "{{timeout}}", "timeout_action": "{{timeout_behavior}}"}, {"name": "handle_approved", "type": "action", "action": "{{on_approve_action}}"}, {"name": "handle_rejected", "type": "action", "action": "{{on_reject_action}}"}])}}
```

**Step 2: Instantiate a workflow from the template**

```text
{{workflow_engine(action="create_from_template", template="approval-cycle", name="review-request-workflow", params={"draft_action": "generate_review_solicitation", "timeout": "8h", "timeout_behavior": "skip", "on_approve_action": "send_review_request_to_guest", "on_reject_action": "log_skipped_review"})}}
```

**Step 3: List and manage templates**

```text
{{workflow_engine(action="list_templates")}}
```

**Step 4: Version a template update**

When you improve a template, create a new version rather than modifying the existing one:

```text
{{workflow_engine(action="update_template", name="approval-cycle", version=2, changes={"added_stage": {"name": "validate_draft", "type": "action", "action": "quality_check", "position": "after:generate_draft"}, "added_parameter": {"name": "quality_threshold", "type": "number", "default": 0.8}})}}
```

Existing workflows using version 1 continue to work. You can migrate them to version 2 individually or in bulk.

**Step 5: Share templates across the team**

```text
{{workflow_engine(action="export_template", name="approval-cycle", format="yaml")}}
```

Export produces a portable definition that can be imported into other Agent Mahoo instances.

### Practice Exercise

**Scenario:** You have built 5 workflows over the past month. Looking at them, you notice three share the same pattern: gather data from an external source, transform it into a digest, and send it via Telegram. The only differences are the data source, the transformation logic, and the send schedule.

**Task:**

1. Design a "data-digest" template that captures the shared pattern
2. Define the parameters that vary between instances
3. Create the template
4. Instantiate it for two use cases: a daily revenue report and a weekly occupancy summary

```text
{{workflow_engine(action="create_template", name="data-digest", description="Fetch external data, transform into digest, deliver via Telegram", parameters=[{"name": "data_source_action", "type": "string", "required": true}, {"name": "transform_action", "type": "string", "required": true}, {"name": "delivery_channel", "type": "string", "default": "telegram"}, {"name": "digest_title", "type": "string", "required": true}, {"name": "skip_if_empty", "type": "boolean", "default": true}], stages=[{"name": "fetch_data", "type": "action", "action": "{{data_source_action}}"}, {"name": "check_empty", "type": "decision", "condition": "context.data.length > 0 OR NOT {{skip_if_empty}}"}, {"name": "transform", "type": "action", "action": "{{transform_action}}"}, {"name": "deliver", "type": "action", "action": "send_digest", "config": {"channel": "{{delivery_channel}}", "title": "{{digest_title}}"}}])}}
```

Then instantiate:

```text
{{workflow_engine(action="create_from_template", template="data-digest", name="daily-revenue-report", params={"data_source_action": "fetch_stripe_revenue", "transform_action": "format_revenue_digest", "digest_title": "Daily Revenue Summary"})}}
```

```text
{{workflow_engine(action="create_from_template", template="data-digest", name="weekly-occupancy-summary", params={"data_source_action": "fetch_pms_occupancy", "transform_action": "format_occupancy_digest", "digest_title": "Weekly Occupancy Report", "skip_if_empty": false})}}
```

**Self-check:** Can you add a third instance (e.g., a daily maintenance summary) without modifying the template? If yes, your parameterization is good. If you need to change the template to accommodate the third use case, your parameters are too narrow.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Over-parameterizing templates | Trying to handle every possible variation | Start with 3-5 parameters; add more only when a real use case demands it |
| Never extracting templates from working workflows | "I'll do it later" | When you build your third similar workflow, stop and extract a template |
| Modifying templates without versioning | Convenience, urgency | Always create a new version; existing instances depend on the old one |
| Templates without documentation | "The parameters are self-explanatory" | Add description to every parameter; future-you will not remember |
