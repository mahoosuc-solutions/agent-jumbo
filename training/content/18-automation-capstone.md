# Module 18: Automation Capstone

> **Learning Path:** Workflow & Automation Engineer
> **Audience:** Technical operators building automations
> **Prerequisites:** Modules 15-17 (Workflow Engine, Scheduling, Integration & Scaling)

---

## Lesson: End-to-End Automation Build

### Why This Matters

Building individual workflow stages, scheduling jobs, and integrating services are component skills. The capstone challenge is assembling them into a complete, production-grade automation that handles the full lifecycle: from requirements gathering through deployment, monitoring, and maintenance.

Most automation projects fail not because any single component is broken, but because the components were not designed to work together. The gaps between components are where failures hide:

- The scheduler triggers a workflow, but the workflow expects data the scheduler does not provide
- The workflow calls an integration, but the integration's error format does not match the workflow's error handler
- The approval flow works perfectly in testing but the timeout configuration does not account for weekends
- The monitoring dashboards show green, but the underlying data is 2 hours stale

An end-to-end build forces you to confront these integration gaps before they become production incidents.

**The integration gap problem:**

| Component A | Component B | The Gap |
|---|---|---|
| Scheduler triggers workflow | Workflow expects context params | Scheduler must pass the right params in the right format |
| Workflow calls PMS API | PMS API returns paginated results | Workflow must handle pagination, not just first page |
| Approval timeout fires | Workflow expects human input | Timeout handler must produce valid "skip" input |
| Error handler logs failure | Dashboard reads error logs | Error format must match dashboard's expected schema |
| Telegram sends approval | Operator responds hours later | State must survive across long time gaps |

### How to Think About It

**The Build Process**

Every end-to-end automation follows this build sequence. Skipping steps leads to integration gaps.

```text
Requirements --> Design --> Build --> Test --> Deploy --> Monitor --> Iterate
     |            |          |        |         |          |           |
  What and     How it      Make    Verify    Put it     Watch      Make it
  why          works       it      it all    live       it run     better
                           work    works
```

**Phase time allocation for a typical automation build:**

| Phase | Time Allocation | Common Mistake |
|---|---|---|
| Requirements | 15% | Skipping to build, then discovering missing requirements |
| Design | 20% | No design doc, building from a mental model that others cannot review |
| Build | 30% | Spending all time here because requirements and design were skipped |
| Test | 20% | Spending 5% and calling it done because "it works on my machine" |
| Deploy + Monitor | 15% | Deploying and walking away without monitoring the first 48 hours |

**Requirements Checklist**

Before writing a single workflow definition, answer these questions:

1. **What triggers this automation?** (schedule, event, manual, webhook)
2. **What data does it need?** (sources, formats, freshness requirements)
3. **What decisions does it make?** (conditional logic, human approvals)
4. **What actions does it take?** (messages, API calls, data updates)
5. **What can go wrong?** (failures at each stage, external dependencies)
6. **Who needs to know what?** (notifications, dashboards, reports)
7. **What does success look like?** (measurable outcomes, SLAs)
8. **What are the edge cases?** (weekends, holidays, empty data, duplicate events)

**Design Document Template**

```text
Automation: [Name]
Version: 1.0
Owner: [Who maintains this]
Created: [Date]

TRIGGER:
  Type: [schedule | event | webhook | manual]
  Details: [cron expression, event name, webhook path, or command]

DATA SOURCES:
  - [Source 1]: [what data, how accessed, freshness requirement]
  - [Source 2]: [what data, how accessed, freshness requirement]

WORKFLOW STAGES:
  1. [Stage name] — [what it does] — [failure mode]
  2. [Stage name] — [what it does] — [failure mode]
  ...

APPROVAL GATES:
  - [What needs approval, timeout, fallback]

ERROR HANDLING:
  - Transient: [retry strategy]
  - Permanent: [notification, DLQ behavior]
  - Degraded: [what to skip, what to substitute]

OUTPUTS:
  - [What is produced, where it goes, who sees it]

SUCCESS CRITERIA:
  - [Measurable outcome 1]
  - [Measurable outcome 2]

EDGE CASES:
  - [What happens on weekends/holidays]
  - [What happens with empty data]
  - [What happens with duplicate triggers]
```

**Dependency Mapping**

Before building, map every dependency your automation has. This prevents surprises during deployment.

```text
Guest Communication Automation
  |
  +-- External Dependencies
  |     +-- PMS API (booking data) — REQUIRED
  |     +-- Weather API (forecast) — OPTIONAL
  |     +-- SendGrid (email delivery) — REQUIRED
  |
  +-- Internal Dependencies
  |     +-- Workflow Engine — REQUIRED
  |     +-- Scheduler — REQUIRED
  |     +-- Approval System — REQUIRED
  |     +-- Template Library — REQUIRED
  |
  +-- Human Dependencies
        +-- Operator (approval responses) — REQUIRED, timeout: 2h
        +-- Cleaning Team (confirmation) — REQUIRED, timeout: 2h
```

For each REQUIRED dependency, you need a failure strategy. For each OPTIONAL dependency, you need a degradation strategy.

### Step-by-Step Approach

**Scenario: Build a complete Guest Communication Automation**

This automation handles all guest communications from booking to post-stay review solicitation. We will build it end-to-end.

**Step 1: Define requirements**

The automation must:

- Detect new bookings and send a welcome message (with approval)
- Send a pre-arrival message 24 hours before check-in (with approval)
- Send a mid-stay check-in at 2 PM the day after check-in (with approval)
- Send a review solicitation 2 days after checkout (with approval)
- Handle all error cases gracefully
- Track all communications in a dashboard

**Step 2: Design the workflow architecture**

```text
{{workflow_engine(action="create", name="guest-communication-lifecycle", version=1, stages=[{"name": "detect_event", "type": "action", "action": "classify_guest_event"}, {"name": "route_by_event", "type": "decision", "condition": "context.event_type"}, {"name": "welcome_pipeline", "type": "sub_workflow", "workflow": "welcome-message-flow"}, {"name": "pre_arrival_pipeline", "type": "sub_workflow", "workflow": "pre-arrival-message-flow"}, {"name": "mid_stay_pipeline", "type": "sub_workflow", "workflow": "mid-stay-message-flow"}, {"name": "review_pipeline", "type": "sub_workflow", "workflow": "review-request-flow"}, {"name": "update_dashboard", "type": "action", "action": "update_guest_comms_dashboard"}, {"name": "log_completion", "type": "action", "action": "log_communication_lifecycle"}], transitions=[{"from": "detect_event", "to": "route_by_event", "condition": "always"}, {"from": "route_by_event", "to": "welcome_pipeline", "condition": "event_type == 'new_booking'"}, {"from": "route_by_event", "to": "pre_arrival_pipeline", "condition": "event_type == 'pre_arrival'"}, {"from": "route_by_event", "to": "mid_stay_pipeline", "condition": "event_type == 'mid_stay'"}, {"from": "route_by_event", "to": "review_pipeline", "condition": "event_type == 'post_checkout'"}, {"from": "welcome_pipeline", "to": "update_dashboard", "condition": "always"}, {"from": "pre_arrival_pipeline", "to": "update_dashboard", "condition": "always"}, {"from": "mid_stay_pipeline", "to": "update_dashboard", "condition": "always"}, {"from": "review_pipeline", "to": "update_dashboard", "condition": "always"}, {"from": "update_dashboard", "to": "log_completion", "condition": "always"}])}}
```

**Step 3: Build the sub-workflows**

Each sub-workflow follows the approval-cycle template:

```text
{{workflow_engine(action="create_from_template", template="approval-cycle", name="welcome-message-flow", params={"draft_action": "ai_draft_welcome_message", "timeout": "2h", "timeout_behavior": "skip", "on_approve_action": "send_guest_email", "on_reject_action": "log_skipped_welcome"})}}
```

```text
{{workflow_engine(action="create_from_template", template="approval-cycle", name="pre-arrival-message-flow", params={"draft_action": "ai_draft_pre_arrival", "timeout": "2h", "timeout_behavior": "skip", "on_approve_action": "send_guest_email", "on_reject_action": "log_skipped_pre_arrival"})}}
```

```text
{{workflow_engine(action="create_from_template", template="approval-cycle", name="mid-stay-message-flow", params={"draft_action": "ai_draft_mid_stay_checkin", "timeout": "4h", "timeout_behavior": "skip", "on_approve_action": "send_guest_email", "on_reject_action": "log_skipped_mid_stay"})}}
```

```text
{{workflow_engine(action="create_from_template", template="approval-cycle", name="review-request-flow", params={"draft_action": "ai_draft_review_solicitation", "timeout": null, "timeout_behavior": "queue_next_batch", "on_approve_action": "send_guest_email", "on_reject_action": "log_skipped_review"})}}
```

Note the different timeout configurations matching the approval-workflow skill: pre-arrival (2h), mid-stay (4h), review solicitation (no timeout, queues for next batch).

**Step 4: Schedule the trigger events**

```text
{{scheduler(action="create_job", name="guest-event-scanner", interval="15m", task="workflow:scan-for-guest-events", config={"overlap_policy": "skip", "active_hours": {"start": "06:00", "end": "22:00"}, "events_to_detect": ["new_booking", "pre_arrival_24h", "mid_stay_day1", "post_checkout_2d"]})}}
```

**Step 5: Configure error handling across the entire system**

```text
{{workflow_engine(action="update", workflow_id="guest-communication-lifecycle", error_handling={"circuit_breaker": "pms-api", "idempotency": {"key": "context.guest_id + context.event_type", "store": "guest_comms_sent", "ttl": "30d"}, "retry": {"strategy": "exponential_backoff", "max_retries": 3}, "on_exhausted_retries": "dead_letter_queue", "notify_on_failure": true, "graceful_degradation": {"missing_weather": "omit_weather_section", "missing_guest_history": "use_generic_template"}})}}
```

**Step 6: Set up the monitoring dashboard**

```text
{{workflow_engine(action="create_dashboard_config", name="guest-comms-monitor", dashboards=[{"name": "guest-communications", "type": "detail", "refresh_interval": "2m", "widgets": ["communications_sent_today", "pending_approvals", "failed_sends_24h", "guest_response_rate", "communication_timeline_by_guest", "approval_turnaround_time"]}])}}
```

**Step 7: Deploy with a verification period**

```text
{{workflow_engine(action="deploy", workflow_id="guest-communication-lifecycle", strategy="canary", config={"canary_percentage": 20, "verification_period": "48h", "success_criteria": {"error_rate": "< 2%", "approval_timeout_rate": "< 25%"}, "auto_rollback_on_failure": true, "notify_on_promotion": true})}}
```

### Practice Exercise

**Scenario:** Build a complete automation for a weekly client pipeline review. Requirements:

1. Every Monday at 8 AM, gather data from the customer lifecycle tool
2. For each client in "proposal" or "negotiation" stage, check days since last contact
3. Flag clients with no contact in 5+ days
4. Generate a pipeline summary digest
5. For flagged clients, draft individual follow-up messages
6. Send the digest to Telegram, and send follow-up drafts for approval
7. Track all actions in the pipeline dashboard

**Task:** Build this end-to-end: requirements doc, workflow definition, scheduler configuration, error handling, and monitoring.

```text
{{workflow_engine(action="create", name="weekly-pipeline-review", version=1, stages=[{"name": "gather_pipeline", "type": "action", "action": "customer_lifecycle_list_active"}, {"name": "analyze_contacts", "type": "action", "action": "calculate_days_since_contact"}, {"name": "flag_stale", "type": "action", "action": "flag_clients_over_threshold", "config": {"threshold_days": 5}}, {"name": "generate_digest", "type": "action", "action": "compile_pipeline_digest"}, {"name": "send_digest", "type": "action", "action": "telegram_send_digest"}, {"name": "draft_followups", "type": "action", "action": "batch_draft_followup_messages", "guards": [{"field": "context.flagged_clients.length", "operator": "greater_than", "value": 0}]}, {"name": "batch_approve", "type": "approval", "mode": "batch", "timeout": "8h", "timeout_action": "skip_and_reschedule"}, {"name": "send_approved", "type": "action", "action": "deliver_approved_followups"}, {"name": "update_lifecycle", "type": "action", "action": "customer_lifecycle_log_contacts"}, {"name": "update_dashboard", "type": "action", "action": "update_pipeline_dashboard"}], transitions=[{"from": "gather_pipeline", "to": "analyze_contacts", "condition": "always"}, {"from": "analyze_contacts", "to": "flag_stale", "condition": "always"}, {"from": "flag_stale", "to": "generate_digest", "condition": "always"}, {"from": "generate_digest", "to": "send_digest", "condition": "always"}, {"from": "send_digest", "to": "draft_followups", "condition": "context.flagged_clients.length > 0"}, {"from": "send_digest", "to": "update_dashboard", "condition": "context.flagged_clients.length == 0"}, {"from": "draft_followups", "to": "batch_approve", "condition": "always"}, {"from": "batch_approve", "to": "send_approved", "condition": "any_approved"}, {"from": "batch_approve", "to": "update_dashboard", "condition": "all_skipped"}, {"from": "send_approved", "to": "update_lifecycle", "condition": "always"}, {"from": "update_lifecycle", "to": "update_dashboard", "condition": "always"}])}}
```

```text
{{scheduler(action="create_job", name="weekly-pipeline-review", cron="0 8 * * 1", timezone="US/Eastern", task="workflow:weekly-pipeline-review", config={"overlap_policy": "skip", "retry_on_failure": true, "max_retries": 2})}}
```

**Self-check:** Trace the entire automation from trigger to completion. At each stage, ask: what data does this stage need, where does it come from, and what happens if it is missing? Every gap you find now is a production incident you prevent. Also verify: what happens if Monday is a holiday and nobody is available to approve follow-ups within 8 hours? Your timeout behavior should handle this gracefully.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Building bottom-up without a design doc | Eagerness to start coding | Spend 30 minutes on requirements and design; save hours of rework |
| Not testing the full end-to-end path | Testing stages in isolation only | Run a complete test with realistic data before deploying |
| Forgetting idempotency on the scanner | Assuming the scanner only sees each event once | Add idempotency keys; scanners often re-detect events on subsequent runs |
| No graceful degradation plan | Assuming all services are always available | Define fallback behavior for every external dependency |
| Deploying at 5 PM on Friday | Wanting to finish before the weekend | Deploy Monday-Wednesday morning; give yourself time to monitor |

---

## Lesson: Load Testing and Optimization

### Why This Matters

An automation that works for 3 properties and 10 bookings per week may collapse when scaled to 15 properties and 50 bookings per week. Without load testing:

- **Hidden bottlenecks surface in production** — The PMS API call that takes 200ms for 1 booking takes 45 seconds when fetching 50
- **Rate limits hit unexpectedly** — Your daily request count grows linearly but your schedule creates burst patterns that exceed per-minute limits
- **Database queries slow down** — Execution history that was fast with 1,000 rows becomes unusable at 100,000
- **Memory pressure increases** — Workflow contexts that hold guest data grow linearly with concurrent executions

Load testing reveals these problems before your operator experiences them at 3 AM with guests arriving in the morning.

**Scaling thresholds to watch:**

| Resource | Small Scale | Medium Scale | Large Scale | Watch For |
|---|---|---|---|---|
| Concurrent executions | 1-3 | 10-20 | 50+ | Context memory, database locks |
| API calls per minute | 5-10 | 50-100 | 500+ | Rate limits, latency spikes |
| Execution history rows | < 10K | 100K+ | 1M+ | Query performance, storage growth |
| Pending approvals | 1-2 | 5-10 | 20+ | Operator cognitive load, timeout cascades |
| Scheduled jobs | 3-5 | 10-20 | 50+ | Trigger collisions, resource contention |

### How to Think About It

**Bottleneck Categories**

```text
COMPUTE              NETWORK              STORAGE              HUMAN

CPU-bound            API latency          DB query time        Approval queue
stages               Rate limits          History growth       Notification
                     Timeout frequency    Cache size           fatigue

Optimize:            Optimize:            Optimize:            Optimize:
Parallel exec,       Caching, batching,   Indexing, archiving, Batch approvals,
async processing     connection pooling   pruning              auto-approve rules
```

**Performance Measurement Framework**

Measure at three levels:

1. **Stage level** — How long does each stage take? Where is time spent?
2. **Workflow level** — Total execution time, broken down by stage
3. **System level** — Concurrent executions, resource utilization, queue depths

```text
Stage Metrics:
  ├── p50 duration (median — your "normal day")
  ├── p95 duration (95th percentile — your "bad day")
  ├── p99 duration (99th percentile — your "worst case")
  ├── error rate (percentage of executions that fail)
  └── throughput (executions per minute)

Workflow Metrics:
  ├── End-to-end duration (trigger to completion)
  ├── Time waiting (approval stages, queue time)
  ├── Time working (actual computation and API calls)
  ├── Success rate (completed / total)
  └── Approval turnaround (time from request to response)

System Metrics:
  ├── Concurrent executions (peak and average)
  ├── API calls per minute (by service)
  ├── Memory utilization (total and per-execution)
  ├── Database query latency (p50, p95)
  └── Queue depth (pending approvals, DLQ entries, scheduled jobs)
```

**The Performance Degradation Curve**

Most systems do not degrade linearly. They have an inflection point where performance falls off a cliff:

```text
Response
Time (s)
    |
 15 |                              .-X  UNACCEPTABLE
    |                           .-'
 10 |                        .-'
    |                     .-'
  5 |                  .-'
    |            ___--'
  2 |    ___---''           <-- inflection point
    |---''
  1 |
    +--+--+--+--+--+--+--+--+--+--
    1  2  3  5  8  10 15 20 30 50
         Concurrent Executions
```

Your job in load testing is to find this inflection point before your users do.

**Optimization Strategies**

| Bottleneck | Diagnosis | Optimization |
|---|---|---|
| Slow API calls | p95 latency > 5s for external calls | Add caching, batch requests, parallel fetch |
| Rate limit hits | Error logs show 429 responses | Spread load with jitter, implement request queuing |
| Large execution contexts | Memory growth correlates with concurrent executions | Prune context between stages, externalize large data |
| Slow history queries | Dashboard load time increasing over time | Add database indexes, archive old history, paginate queries |
| Operator bottleneck | Approval queue depth growing daily | Implement auto-approve for low-risk items, batch approvals |
| Trigger collisions | Multiple schedulers firing at the same second | Stagger schedule times by 1-2 minutes |

### Step-by-Step Approach

**Step 1: Establish baseline performance metrics**

Before optimizing anything, measure the current state:

```text
{{workflow_engine(action="get_metrics", workflow_id="guest-communication-lifecycle", period="7d", metrics=["stage_durations_p50", "stage_durations_p95", "end_to_end_duration", "success_rate", "concurrent_peak", "api_calls_per_minute"])}}
```

Record these numbers. They are your baseline. Any optimization is measured against this.

**Step 2: Run a load test simulation**

```text
{{workflow_engine(action="load_test", workflow_id="guest-communication-lifecycle", config={"scenario": "scale_test", "concurrent_executions": [1, 5, 10, 20], "duration_per_level": "5m", "mock_external_services": true, "mock_latency": {"pms_api": "200ms", "email_service": "100ms"}, "measure": ["throughput", "latency_p95", "error_rate", "memory_usage"]})}}
```

**Step 3: Analyze load test results**

Look for the inflection point where performance degrades:

```text
{{workflow_engine(action="get_load_test_results", test_id="lt-2026-0320-001")}}
```

Expected output pattern:

```text
Concurrent 1:  p95=2.1s,  errors=0%,   memory=45MB
Concurrent 5:  p95=2.4s,  errors=0%,   memory=120MB
Concurrent 10: p95=4.8s,  errors=2%,   memory=230MB   <-- degradation starts
Concurrent 20: p95=12.3s, errors=15%,  memory=480MB   <-- unacceptable
```

The inflection point is between 5 and 10 concurrent executions. That is where you focus optimization efforts.

**Step 4: Apply targeted optimizations**

Based on the bottleneck identified:

```text
{{workflow_engine(action="optimize", workflow_id="guest-communication-lifecycle", optimizations=[{"type": "cache", "stage": "fetch_guest_data", "config": {"ttl": "15m", "key": "guest_{{guest_id}}"}}, {"type": "context_pruning", "config": {"prune_after_stage": "generate_message", "keep_fields": ["guest_name", "message_draft", "approval_status"], "remove_fields": ["full_guest_history", "raw_pms_response"]}}, {"type": "parallel", "stages": ["fetch_guest_data", "fetch_property_data", "fetch_weather"], "group": "data_gather"}])}}
```

**Step 5: Re-run load test and compare**

```text
{{workflow_engine(action="load_test", workflow_id="guest-communication-lifecycle", config={"scenario": "post_optimization", "concurrent_executions": [1, 5, 10, 20], "duration_per_level": "5m", "compare_to": "lt-2026-0320-001"})}}
```

The comparison shows the impact of each optimization. If the inflection point moved from 10 to 20, your optimizations worked.

### Practice Exercise

**Scenario:** Your morning briefing workflow has been taking progressively longer to execute over the past month. When it started, it completed in 3 seconds. Now it takes 18 seconds, and last Tuesday it timed out entirely.

**Task:**

1. Pull the performance metrics for the past 30 days
2. Identify which stage is causing the slowdown
3. Determine the root cause (data growth, API degradation, or resource contention)
4. Apply targeted optimizations
5. Verify the fix with a load test

```text
{{workflow_engine(action="get_metrics", workflow_id="morning-briefing-assembly", period="30d", metrics=["stage_durations_p50_trend", "stage_durations_p95_trend", "total_duration_trend", "api_latency_by_service", "execution_history_row_count"])}}
```

Based on the trend data, if the PMS fetch stage shows linear growth:

```text
{{workflow_engine(action="optimize", workflow_id="morning-briefing-assembly", optimizations=[{"type": "cache", "stage": "fetch_pms_data", "config": {"ttl": "10m", "key": "pms_daily_{{date}}"}}, {"type": "pagination", "stage": "fetch_pms_data", "config": {"page_size": 50, "parallel_pages": true}}, {"type": "history_archival", "config": {"archive_after": "30d", "archive_destination": "cold_storage"}}])}}
```

Then verify:

```text
{{workflow_engine(action="get_metrics", workflow_id="morning-briefing-assembly", period="3d", metrics=["total_duration_trend", "stage_durations_p50_trend"])}}
```

**Self-check:** After applying optimizations, is the 30-day trend line now flat instead of climbing? If it is still climbing (just more slowly), you have addressed a symptom but not the root cause. Common root causes that produce linear growth: unbounded query results (fix: pagination), growing execution history (fix: archival), accumulating context data (fix: pruning).

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| No baseline metrics before optimizing | Rushing to fix perceived slowness | Measure first; you cannot improve what you cannot measure |
| Optimizing the wrong stage | Guessing instead of profiling | Profile every stage; the bottleneck is often not where you expect |
| Caching without invalidation strategy | Cache makes things faster, but stale data causes bugs | Every cache needs a TTL and an explicit invalidation trigger |
| Load testing with mock data only | Real data is hard to use in tests | Test with production-like data volumes; mocks hide data-dependent bottlenecks |
| One-time optimization with no monitoring | "Fixed it, moving on" | Set up alerts on the metrics you optimized; regressions happen |

---

## Lesson: Automation Governance

### Why This Matters

As your automation portfolio grows from 2 workflows to 20, governance becomes the difference between a manageable system and an unmaintainable mess. Without governance:

- **Nobody knows what automations exist** — A workflow created 6 months ago keeps running but nobody remembers why or what it does
- **Changes break things** — Modifying one workflow causes unexpected failures in others because dependencies are undocumented
- **Rollbacks are impossible** — When a change causes problems, there is no way to revert because previous versions are not preserved
- **Compliance questions go unanswered** — When a client asks "what data does your system access and when?", you cannot answer confidently
- **Knowledge walks out the door** — When the person who built a workflow leaves, the workflow becomes a black box

Governance is not bureaucracy. It is the minimum set of practices that keep your automation portfolio understandable, changeable, and auditable over time.

**The cost of missing governance:**

| Situation | Without Governance | With Governance |
|---|---|---|
| "What automations do we have?" | Grep through files, ask colleagues | Check the registry, everything listed |
| "Something changed and X broke" | Hours of investigation | Check change log, see what deployed recently |
| "We need to roll back" | Rebuild from memory, hope for the best | Revert to previous version, documented procedure |
| "The person who built this left" | Black box, fear of touching it | Design doc, runbook, ownership transferred |
| "Client asks about data access" | "Let me get back to you" (weeks) | Pull audit report (minutes) |

### How to Think About It

**The Governance Triad**

```text
       DOCUMENTATION
       (what and why)
          /     \
         /       \
        /         \
CHANGE MGMT --- AUDIT
(how to change)    (proof it works)
```

| Pillar | Purpose | Artifacts |
|---|---|---|
| Documentation | Anyone can understand what an automation does and why | Automation registry, design docs, runbooks |
| Change Management | Changes are deliberate, tested, and reversible | Version control, staging environments, rollback procedures |
| Audit | Prove what happened, when, and why | Execution logs, approval records, change history |

All three pillars must be present. Documentation without change management means you know what the system does but cannot safely modify it. Change management without audit means you can modify the system but cannot prove it is working correctly. Audit without documentation means you have data but no context to interpret it.

**Automation Registry**

Every automation in production must be registered. The registry is the single source of truth for "what automations exist and what do they do."

```text
Registry Entry:
  Name: guest-communication-lifecycle
  Version: 2.1
  Owner: ops-team
  Created: 2026-01-15
  Last Modified: 2026-03-18
  Status: active

  Description: Manages all guest communications from booking
               through post-stay review solicitation.

  Trigger: Event-driven (new booking, pre-arrival window,
           mid-stay window, post-checkout window)
  Schedule: Scanner runs every 15 minutes

  Dependencies:
    - Services: PMS API, SendGrid, Telegram
    - Workflows: welcome-message-flow, pre-arrival-message-flow,
                 mid-stay-message-flow, review-request-flow
    - Data: guest profiles, booking records, property details

  SLA: Messages sent within 2 hours of trigger event
  Last Review: 2026-03-01
  Next Review: 2026-04-01
```

**Registry health indicators:**

| Indicator | Healthy | Unhealthy |
|---|---|---|
| Review date | Within 30 days | Overdue by > 30 days |
| Owner | Assigned, active team member | Unassigned or former employee |
| Status | Active or explicitly paused | Unknown or "needs_review" for > 7 days |
| Dependencies | All listed, all healthy | Missing entries, unhealthy services |
| SLA | Met > 99% of the time | Violated > 5% of the time |

**Change Management Process**

```text
Propose --> Review --> Test --> Stage --> Deploy --> Verify --> Document
   |          |         |        |         |          |           |
 What and   Peer      Unit    Run in    Push to    Confirm     Update
 why        review    + E2E   staging   prod       success     registry
                                                   and docs
```

| Change Type | Review Required | Testing Required | Rollback Plan |
|---|---|---|---|
| New workflow | Design review + peer review | Unit + E2E + staging | Delete workflow |
| Stage modification | Peer review | Unit + affected E2E | Revert to previous version |
| Parameter change | Self-review | Smoke test | Revert parameter value |
| Template update | Design review | All instances tested | Revert template version |
| Integration change | Peer review + security review | Integration tests + staging | Revert credentials/config |

**Rollback Procedures**

Every deployment must have a documented rollback:

```text
Rollback Checklist:
  1. Identify the change that caused the problem
  2. Verify the previous version is available
  3. Pause the affected scheduler jobs
  4. Revert the workflow to the previous version
  5. Drain any in-flight executions (wait for completion or cancel)
  6. Resume scheduler jobs with the reverted workflow
  7. Verify the reverted workflow executes correctly
  8. Document the incident and rollback in the change log
  9. Schedule a post-mortem within 48 hours
```

### Step-by-Step Approach

**Step 1: Create the automation registry**

```text
{{workflow_engine(action="create_registry", config={"required_fields": ["name", "version", "owner", "description", "trigger", "dependencies", "sla"], "review_interval": "30d", "alert_on_overdue_review": true, "alert_channel": "telegram"})}}
```

**Step 2: Register all existing automations**

```text
{{workflow_engine(action="register_automation", data={"name": "guest-communication-lifecycle", "version": "2.1", "owner": "ops-team", "description": "Manages all guest communications from booking through post-stay review solicitation", "trigger": {"type": "event", "scanner": "guest-event-scanner", "interval": "15m"}, "dependencies": {"services": ["pms-hospitable", "sendgrid-email", "telegram-bot"], "workflows": ["welcome-message-flow", "pre-arrival-message-flow", "mid-stay-message-flow", "review-request-flow"], "data": ["guest_profiles", "booking_records", "property_details"]}, "sla": {"message_delivery": "2h from trigger", "success_rate": "99%"}, "runbook": "docs/runbooks/guest-communications.md"})}}
```

**Step 3: Implement version-controlled changes**

```text
{{workflow_engine(action="propose_change", workflow_id="guest-communication-lifecycle", change={"type": "stage_modification", "description": "Add weather data to pre-arrival message", "stages_affected": ["pre_arrival_pipeline"], "risk_level": "low", "testing_plan": "unit test for weather integration, E2E test for pre-arrival flow", "rollback_plan": "revert to version 2.1, weather section omitted from messages"})}}
```

After review and testing:

```text
{{workflow_engine(action="deploy_change", change_id="chg-2026-0320-001", method="rolling", verification={"check_after": "30m", "success_criteria": {"error_rate": "< 1%", "latency_p95": "< 5s"}, "auto_rollback_on_failure": true, "notify_on_promotion": true})}}
```

**Step 4: Set up audit reporting**

```text
{{workflow_engine(action="create_audit_report", config={"name": "monthly-automation-audit", "schedule": "0 9 1 * *", "timezone": "US/Eastern", "sections": [{"name": "execution_summary", "metrics": ["total_runs", "success_rate", "avg_duration", "error_breakdown"]}, {"name": "approval_audit", "data": ["all_approval_decisions", "timeout_actions", "edit_revisions"]}, {"name": "change_log", "data": ["all_changes_deployed", "rollbacks_performed"]}, {"name": "sla_compliance", "data": ["sla_met_percentage", "sla_violations_detail"]}, {"name": "data_access_log", "data": ["external_apis_called", "data_accessed", "credentials_used"]}], "delivery": "telegram_and_archive"})}}
```

**Step 5: Document runbooks for common incidents**

```text
{{workflow_engine(action="create_runbook", name="guest-comms-incidents", sections=[{"title": "Workflow Not Triggering", "symptoms": ["No morning briefing received", "Guest event scanner shows 0 executions"], "diagnosis": ["Check scheduler: is the job paused?", "Check circuit breaker: is PMS API circuit open?", "Check DLQ: are executions failing silently?"], "resolution": ["If paused: resume with reason documented", "If circuit open: verify PMS API status, wait for recovery", "If DLQ: review entries, fix root cause, replay"]}, {"title": "Wrong Message Sent to Guest", "symptoms": ["Guest received message with wrong name or details"], "diagnosis": ["Pull execution history for the specific execution", "Check context data at each stage", "Verify PMS data freshness"], "resolution": ["Contact guest to apologize", "Fix data source or transformation", "Add guard condition to prevent recurrence"]}, {"title": "Approval Queue Backlog", "symptoms": ["Multiple pending approvals piling up", "Timeout rate increasing"], "diagnosis": ["Check operator availability", "Review approval volume trends", "Check if auto-approve candidates exist"], "resolution": ["Process queue immediately", "Consider batch approval for low-risk items", "Add auto-approve rules for repeat patterns"]}])}}
```

### Practice Exercise

**Scenario:** You are taking over a system with 12 automations that were built over 6 months by different people. There is no registry, no documentation, and no change management process. Two of the automations appear to do similar things, and one has been failing silently for 3 weeks.

**Task:**

1. Audit all existing automations and create registry entries
2. Identify and resolve the silent failure
3. Consolidate the two similar automations
4. Establish a change management process going forward
5. Create an audit report template

```text
{{workflow_engine(action="list_all_workflows", include=["status", "last_execution", "error_count", "created_by", "created_at"])}}
```

Review each workflow and create a registry entry:

```text
{{workflow_engine(action="register_automation", data={"name": "unknown-workflow-7", "version": "1.0", "owner": "unassigned", "description": "TO BE DOCUMENTED — appears to check PMS for rate changes", "trigger": {"type": "schedule", "cron": "0 */6 * * *"}, "status": "needs_review", "notes": "Last successful execution: 2026-02-28. Failing since 2026-03-01 with 401 errors — likely expired API credentials."})}}
```

For the silently failing automation:

```text
{{workflow_engine(action="get_history", workflow_id="unknown-workflow-7", period="30d", filter={"action": "error"})}}
```

For the duplicate automations, compare them side by side:

```text
{{workflow_engine(action="compare_workflows", workflow_ids=["daily-booking-check", "booking-monitor-v2"], output=["stage_differences", "trigger_differences", "output_differences"])}}
```

Then consolidate:

```text
{{workflow_engine(action="create_from_merge", source_workflows=["daily-booking-check", "booking-monitor-v2"], name="unified-booking-monitor", keep_from={"stages": "booking-monitor-v2", "schedule": "daily-booking-check"}, deprecate=["daily-booking-check", "booking-monitor-v2"])}}
```

**Self-check:** After completing this exercise, can you answer these questions for every automation in the system?

1. What does it do and why?
2. Who owns it?
3. When did it last run successfully?
4. What would happen if it stopped running?
5. How do you roll back the last change?

If you cannot answer any of these for any automation, your governance is incomplete. Schedule a follow-up review in 7 days to fill the remaining gaps.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Treating documentation as optional | "The code is self-documenting" | Code shows what; documentation shows why and when to use it |
| No rollback plan before deploying | Confidence that the change will work | Every deployment must have a tested rollback; confidence is not a strategy |
| Skipping reviews for "small changes" | "It's just a parameter tweak" | Small changes cause big outages; parameter changes need at least self-review |
| Audit reports that nobody reads | Reports generated but not reviewed | Schedule a monthly 15-minute audit review; make it a recurring calendar event |
| Registry that decays over time | Initial setup but no maintenance habit | Set review reminders; overdue reviews generate Telegram alerts automatically |
