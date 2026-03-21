# Module 6: Optimization & Support

> **Learning Path:** AI Solution Architect
> **Audience:** Non-technical business operators learning AI solution architecture
> **Prerequisites:** Completed Module 5: Deployment & Operations

---

## Lesson: Monitoring AI Performance

### Why This Matters

Deploying an AI solution is not the finish line. It is the starting line. The moment real users interact with your system, reality diverges from your test data. Models drift, usage patterns shift, edge cases multiply, and costs creep upward. Without monitoring, you discover these problems when a client calls to complain -- or worse, when they quietly stop using the system.

**What goes wrong without monitoring:**

| Blind Spot | What Happens | How You Find Out |
|---|---|---|
| Quality degradation | AI outputs slowly get worse over time | Client mentions they have been "manually fixing" outputs for weeks |
| Latency creep | Response times increase as data grows | Users abandon the tool because it "feels slow" |
| Cost overrun | Token usage climbs as prompts grow | End-of-month invoice is 3x what you quoted |
| Usage decline | Adoption drops after initial enthusiasm | Client does not renew, cites "low ROI" |

The purpose of monitoring is to know before your client knows. Every metric you track is an early warning system that gives you time to fix problems while they are still small.

**The monitoring ROI:**

```text
Without monitoring:
  Client notices problem  -->  Client reports it  -->  You investigate  -->  You fix
  Timeline: Days to weeks. Trust damage: High.

With monitoring:
  Alert fires  -->  You investigate  -->  You fix  -->  Client never knows
  Timeline: Minutes to hours. Trust damage: Zero.
```

### How to Think About It

**The Four Pillars Framework**

Every AI solution needs four categories of metrics. Missing any one pillar leaves a blind spot that will eventually cause a problem.

```text
FOUR PILLARS OF AI MONITORING

PILLAR 1: ACCURACY / QUALITY
  "Is the AI producing good outputs?"
  +-----------------------------------------+
  | Metrics:                                |
  |   - Quality score (automated check)     |
  |   - Human review pass rate              |
  |   - Error categorization breakdown      |
  |   - Hallucination rate                  |
  |   - Format compliance rate              |
  |                                         |
  | Healthy signals:                        |
  |   - Quality score stable or improving   |
  |   - Human override rate < 10%           |
  |   - No new error categories appearing   |
  +-----------------------------------------+

PILLAR 2: LATENCY / SPEED
  "Is it fast enough for users?"
  +-----------------------------------------+
  | Metrics:                                |
  |   - End-to-end response time (p50/p95)  |
  |   - AI model API call duration          |
  |   - Pre/post processing time            |
  |   - Queue wait time (async tasks)       |
  |                                         |
  | Healthy signals:                        |
  |   - p50 < 3s, p95 < 10s                |
  |   - No upward trend over weeks          |
  |   - Queue backlog stays near zero       |
  +-----------------------------------------+

PILLAR 3: COST / EFFICIENCY
  "Is it economically sustainable?"
  +-----------------------------------------+
  | Metrics:                                |
  |   - Cost per request                    |
  |   - Cost per customer per month         |
  |   - Token usage per request             |
  |   - Cache hit rate                      |
  |   - Compute cost vs AI API cost ratio   |
  |                                         |
  | Healthy signals:                        |
  |   - Cost per request stable or falling  |
  |   - Cache hit rate > 20%                |
  |   - Within quoted budget                |
  +-----------------------------------------+

PILLAR 4: USER SATISFACTION
  "Are people actually getting value?"
  +-----------------------------------------+
  | Metrics:                                |
  |   - Daily/weekly active users           |
  |   - Feature usage breakdown             |
  |   - Task completion rate                |
  |   - Support ticket volume               |
  |   - NPS / satisfaction score            |
  |                                         |
  | Healthy signals:                        |
  |   - Usage steady or growing             |
  |   - Support tickets declining           |
  |   - High task completion rate           |
  +-----------------------------------------+
```

**Alerting Strategy: Who Gets Woken Up and When**

Not every metric needs an alert. Not every alert needs to wake someone up. Use a tiered approach:

```text
ALERT SEVERITY FRAMEWORK

SEVERITY 1 -- CRITICAL (immediate response required)
  Trigger: System is down or producing harmful outputs
  Examples:
    - Error rate > 50% for 2 minutes
    - Health check failing
    - Security breach detected
  Notify: On-call operator, phone call + SMS
  Response time: < 15 minutes
  Escalation: If no response in 15 min, notify team lead

SEVERITY 2 -- WARNING (response within business hours)
  Trigger: Performance degraded but system is functional
  Examples:
    - p95 latency > 15s for 10 minutes
    - Error rate > 5% for 10 minutes
    - Quality score dropped > 10% over 24 hours
    - Daily cost > 150% of budget
  Notify: Team Slack channel
  Response time: < 4 hours
  Escalation: If unresolved in 24 hours, create incident

SEVERITY 3 -- INFO (review in weekly ops check)
  Trigger: Trend requires attention but no immediate impact
  Examples:
    - Usage declining 10% week-over-week
    - Cost per request slowly rising
    - New error category appearing at low rate
    - Cache hit rate declining
  Notify: Weekly ops report
  Response time: Next scheduled review
  Escalation: If trend continues 3 weeks, upgrade to warning
```

**Dashboard Design: What to Put Where**

```text
DASHBOARD LAYOUT FRAMEWORK

EXECUTIVE DASHBOARD (for client stakeholders)
  Show: Business value metrics only
  Refresh: Daily
  Metrics:
    - Tasks completed this week/month
    - Time saved (hours)
    - Error rate (simple %)
    - System uptime (%)
  Avoid: Technical metrics, raw numbers, jargon

OPERATIONS DASHBOARD (for your team)
  Show: All four pillars, real-time
  Refresh: Every 30 seconds
  Layout:
    Top row:     System health (up/down), active alerts, error rate
    Middle row:  Latency charts (p50, p95, p99), throughput
    Bottom row:  AI metrics (quality score, cost per request, token usage)
  Key feature: Click any metric to drill down to individual requests

COST DASHBOARD (for project economics)
  Show: Financial metrics
  Refresh: Hourly
  Metrics:
    - Daily spend (actual vs budget)
    - Cost breakdown by service (AI API, compute, storage)
    - Cost per customer
    - Projected monthly total
    - Trend lines (are costs rising or falling?)
```

### Step-by-Step Approach

**Step 1: Create the monitoring configuration**

```text
{{monitoring_setup(
  action="create",
  project="acme-invoice-processor",
  pillars={
    "quality": {
      "metrics": ["quality_score", "human_override_rate", "format_compliance"],
      "check_schedule": "hourly",
      "sample_size": 20
    },
    "latency": {
      "metrics": ["e2e_response_time", "model_api_duration", "queue_wait_time"],
      "percentiles": ["p50", "p95", "p99"]
    },
    "cost": {
      "metrics": ["cost_per_request", "daily_spend", "token_usage", "cache_hit_rate"],
      "budget_monthly": 500.00
    },
    "satisfaction": {
      "metrics": ["daily_active_users", "task_completion_rate", "support_tickets"],
      "tracking": "weekly_trend"
    }
  }
)}}
```

**Step 2: Configure alerts**

```text
{{monitoring_setup(
  action="configure_alerts",
  project="acme-invoice-processor",
  alerts=[
    {
      "name": "system_down",
      "severity": "critical",
      "condition": "health_check_failing for 2m",
      "notify": ["phone:ops-oncall", "sms:ops-oncall", "slack:ops-critical"]
    },
    {
      "name": "high_error_rate",
      "severity": "critical",
      "condition": "error_rate > 50% for 2m",
      "notify": ["phone:ops-oncall", "slack:ops-critical"]
    },
    {
      "name": "latency_degraded",
      "severity": "warning",
      "condition": "p95_latency > 15s for 10m",
      "notify": ["slack:ops-warnings"]
    },
    {
      "name": "quality_drop",
      "severity": "warning",
      "condition": "quality_score < 0.80 for 1h",
      "notify": ["slack:ops-warnings"]
    },
    {
      "name": "cost_spike",
      "severity": "warning",
      "condition": "daily_spend > 25.00",
      "notify": ["slack:ops-warnings", "email:team-lead"]
    },
    {
      "name": "usage_decline",
      "severity": "info",
      "condition": "weekly_active_users down 10% week_over_week",
      "notify": ["weekly_report"]
    }
  ]
)}}
```

**Step 3: Create dashboards**

```text
{{monitoring_setup(
  action="create_dashboard",
  project="acme-invoice-processor",
  dashboards=[
    {
      "name": "executive",
      "audience": "client",
      "refresh": "daily",
      "panels": ["tasks_completed", "time_saved", "uptime", "error_rate_simple"]
    },
    {
      "name": "operations",
      "audience": "team",
      "refresh": "30s",
      "panels": ["health_status", "active_alerts", "latency_chart", "throughput",
                  "quality_score_trend", "cost_per_request", "token_usage"]
    },
    {
      "name": "cost",
      "audience": "team_lead",
      "refresh": "hourly",
      "panels": ["daily_spend_vs_budget", "cost_breakdown", "cost_per_customer",
                  "monthly_projection", "cost_trend"]
    }
  ]
)}}
```

**Step 4: Verify monitoring is active**

```text
{{monitoring_setup(
  action="validate",
  project="acme-invoice-processor",
  checks=["all_pillars_covered", "alerts_configured", "dashboards_loading",
           "data_flowing", "escalation_paths_defined"]
)}}
```

### What Good Looks Like

**A properly monitored AI solution has these properties:**

- All four pillars have at least 2 metrics each -- no blind spots
- Critical alerts have been tested (trigger a test alert, confirm it reaches the right person)
- Dashboards load in under 5 seconds and show data from the last 5 minutes
- The executive dashboard is comprehensible to a non-technical client
- Historical data is retained for at least 90 days (for trend analysis)
- Weekly ops review covers all four pillars, not just the ones that alerted

**Common mistakes to avoid:**

| Mistake | Risk | Fix |
|---|---|---|
| Monitoring only infrastructure (CPU/memory) | Miss AI-specific problems (quality drift, cost overrun) | Add all four pillars, not just compute metrics |
| Too many alerts | Alert fatigue -- team ignores everything | Use three severity tiers; review and prune monthly |
| No client-facing dashboard | Client has no visibility into the value they are getting | Build an executive dashboard on day one |
| Alerting on every blip | 3 AM wake-up for a 30-second latency spike | Require sustained duration (e.g., "> 15s for 10 minutes") |
| Not tracking cost per request | Margin erosion invisible until invoice arrives | Track cost as a first-class metric from day one |
| No historical baseline | Cannot tell if a metric is "normal" or "degraded" | Collect 2 weeks of data before setting alert thresholds |

### Practice Exercise

Set up monitoring for one of your deployed projects:

1. Run `{{monitoring_setup(action="create", ...)}}` with all four pillars configured
2. Configure at least 5 alerts across all three severity levels
3. Create an executive dashboard and an operations dashboard
4. Run `{{monitoring_setup(action="validate", ...)}}` and fix any gaps
5. Trigger a test alert and confirm it reaches the correct notification channel
6. Review the operations dashboard and identify one metric that needs a baseline

**Success criteria:**

- All four pillars have active metrics with data flowing
- Critical alerts are tested and reach the right person within 2 minutes
- Executive dashboard answers: "Is it working? How much value did it create?"
- Operations dashboard answers: "What is happening right now? Is anything degraded?"
- You can explain what every metric measures and what triggers each alert

---

## Lesson: Prompt Iteration

### Why This Matters

The prompt is the most impactful and least stable component of any AI solution. A 10-word change to a prompt can improve output quality by 30% -- or break it entirely. Without a structured approach to prompt iteration, you are guessing. And guessing with prompts is expensive because:

- **Every test costs money** -- each prompt assessment calls the AI API
- **Results are probabilistic** -- the same prompt produces different outputs on different runs
- **Regression is silent** -- improving one case often breaks another, and you will not notice until a client does
- **Version control is missing** -- most teams have no idea which prompt version is running in production or why it was changed

The operators who deliver consistently high-quality AI solutions are the ones who treat prompt iteration as an engineering discipline, not an art form.

**The prompt iteration stakes:**

```text
Undisciplined iteration:
  "Let me try changing this..."  -->  "That seems better"  -->  "Wait, it broke the other thing"
  Result: Weeks of back-and-forth, no measurable progress, client loses patience

Disciplined iteration:
  Measure baseline  -->  Analyze failures  -->  Hypothesize fix  -->  Test  -->  Compare  -->  Deploy
  Result: Steady improvement, data-backed decisions, client sees progress
```

### How to Think About It

**The Prompt Iteration Cycle**

Every prompt change should follow this cycle. Skipping steps is how regressions reach production.

```text
THE ITERATION CYCLE

     +-----------+
     |  MEASURE  |  Establish current performance with fixed test suite
     +-----+-----+
           |
           v
     +-----------+
     |  ANALYZE  |  Categorize failures, find patterns, identify root cause
     +-----+-----+
           |
           v
     +-----------+
     | HYPOTHESIZE|  Form a specific, testable theory about what to change
     +-----+-----+
           |
           v
     +-----------+
     |   TEST    |  Run the change against the test suite, compare to baseline
     +-----+-----+
           |
           v
     +-----------+
     |  DEPLOY   |  If improved and no regression, promote to production
     +-----+-----+
           |
           v
     (back to MEASURE)
```

**A/B Testing Prompts: The Framework**

You cannot assess a prompt by looking at a few examples. You need structured comparison.

```text
A/B TEST STRUCTURE

CONTROL:  Current production prompt (version N)
VARIANT:  Modified prompt (version N+1)

Test Parameters:
  - Same test suite for both (minimum 30 test cases)
  - Same model and parameters (temperature, max tokens)
  - Same scoring criteria
  - Run both, then compare

Sample Size Guide:
  Quick check:     30 cases   (directional signal, not conclusive)
  Confident test:  50 cases   (good for most decisions)
  High-stakes:     100+ cases (when the change affects critical outputs)

Decision Criteria:
  DEPLOY if:
    - Overall quality score improved by >= 5%
    - No individual category regressed by > 10%
    - Cost per request did not increase by > 20%

  HOLD if:
    - Quality improved but one category regressed
    - Improvement is < 5% (not worth the risk)

  REJECT if:
    - Overall quality decreased
    - Cost increased with no quality improvement
    - Any critical failure category worsened
```

**Failure Analysis: Categorizing Errors**

Before you can fix a prompt, you need to understand how it fails. Use a standard error taxonomy:

```text
ERROR CATEGORIZATION FRAMEWORK

Category            Description                         Fix Strategy
-----------------   ---------------------------------   ----------------------
HALLUCINATION       AI invents facts not in input        Add grounding constraints,
                                                         "only use information from
                                                         the provided text"

FORMAT ERROR        Output structure is wrong             Add explicit format
                    (missing fields, wrong JSON)          examples, use structured
                                                         output mode

INCOMPLETE          Missing information that was          Add checklist to prompt,
                    present in input                      "ensure you include X, Y, Z"

WRONG TONE          Too formal, too casual, off-brand    Add tone examples,
                                                         "write in the style of..."

OVER-VERBOSE        Output is 3x longer than needed      Add length constraints,
                                                         "respond in under N words"

EDGE CASE           Fails on unusual inputs               Add handling instructions,
                    (empty fields, special characters)    "if X is missing, then..."

INSTRUCTION DRIFT   Ignores part of the prompt            Move critical instructions
                    (especially late in long prompts)     to beginning or end,
                                                         repeat key constraints
```

**Version Control for Prompts**

Every prompt version should be traceable: what changed, why it changed, what the test results were.

```text
PROMPT VERSION RECORD

version: v3
date: 2026-03-15
author: operator-name
parent: v2

change_summary: "Added explicit grounding constraint to reduce hallucinations"
change_detail: |
  Added line: "Only use information explicitly stated in the provided document.
  If information is not present, respond with 'Not found in document' rather
  than inferring."

test_results:
  test_suite: tests/prompts/invoice_extraction/
  sample_size: 50
  overall_quality: 0.91 (v2 was 0.84)
  hallucination_rate: 0.02 (v2 was 0.12)
  format_compliance: 0.98 (v2 was 0.97)
  regression_check: no categories worsened

decision: DEPLOY
deployed_to_production: 2026-03-16
```

### Step-by-Step Approach

**Step 1: Measure the current baseline**

```text
{{prompt_test(
  action="run_baseline",
  project="acme-invoice-processor",
  prompt="invoice_extractor",
  version="current_production",
  test_suite="tests/prompts/invoice_extraction/",
  sample_size=50,
  metrics=["quality_score", "hallucination_rate", "format_compliance",
           "completeness", "cost_per_request"]
)}}
```

This establishes the baseline you will measure all changes against.

**Step 2: Analyze failures**

```text
{{prompt_test(
  action="analyze_failures",
  project="acme-invoice-processor",
  prompt="invoice_extractor",
  baseline_run="latest",
  categorize_by=["error_type", "input_characteristics"],
  output="failure_report"
)}}
```

This generates a report showing which error categories are most common, which inputs cause failures, and where the biggest improvement opportunities are.

**Step 3: Create a variant prompt**

```text
{{prompt_manager(
  action="create_version",
  project="acme-invoice-processor",
  prompt="invoice_extractor",
  parent_version="v2",
  new_version="v3",
  change_summary="Added grounding constraint to reduce hallucinations",
  change_type="targeted_fix",
  target_error_category="hallucination"
)}}
```

**Step 4: Run the A/B test**

```text
{{prompt_test(
  action="ab_test",
  project="acme-invoice-processor",
  prompt="invoice_extractor",
  control_version="v2",
  variant_version="v3",
  test_suite="tests/prompts/invoice_extraction/",
  sample_size=50,
  metrics=["quality_score", "hallucination_rate", "format_compliance",
           "completeness", "cost_per_request"],
  decision_criteria={
    "deploy_if": "quality_score_improved >= 5% AND no_category_regressed > 10%",
    "reject_if": "quality_score_decreased OR any_critical_category_worsened"
  }
)}}
```

**Step 5: Review results and decide**

```text
{{prompt_test(
  action="compare",
  project="acme-invoice-processor",
  prompt="invoice_extractor",
  runs=["v2_baseline", "v3_ab_test"],
  format="side_by_side",
  highlight="regressions"
)}}
```

**Step 6: Deploy or iterate**

If the variant passed:

```text
{{prompt_manager(
  action="promote",
  project="acme-invoice-processor",
  prompt="invoice_extractor",
  version="v3",
  target_environment="production",
  record={
    "test_results_run": "v3_ab_test",
    "approved_by": "operator-name",
    "rollback_version": "v2"
  }
)}}
```

If the variant needs more work, return to Step 2 with the new failure data.

### What Good Looks Like

**A properly managed prompt iteration process has these properties:**

- Every prompt version in production has test results that justify its deployment
- Failure analysis precedes every change (you know what you are fixing before you change anything)
- A/B tests use a fixed test suite with at least 30 cases
- No prompt change is deployed without a regression check
- Version history shows a clear trail: what changed, why, and what the results were
- Rollback is possible in under 2 minutes (previous version is always tagged and ready)

**Common mistakes to avoid:**

| Mistake | Risk | Fix |
|---|---|---|
| "It looks better on 3 examples" | Confirmation bias, sample too small | Use test suite with 30+ cases, compare metrics |
| Changing multiple things at once | Cannot tell which change helped or hurt | One change per version; test each independently |
| No regression check | Fix hallucinations, break formatting | Always check all categories, not just the target |
| Prompt versions not tracked | "Which version is in production? Not sure." | Use prompt_manager for every change, tag production |
| Optimizing for quality only | Cost doubles, latency triples | Include cost and latency in every assessment |
| Never rolling back | Bad prompt stays in production because "we will fix forward" | Set a rollback trigger: if quality drops > 10%, auto-revert |

### Practice Exercise

Run a complete prompt iteration cycle on one of your project prompts:

1. Run `{{prompt_test(action="run_baseline", ...)}}` to establish current performance
2. Run `{{prompt_test(action="analyze_failures", ...)}}` to identify the top error category
3. Create a variant that targets the top error category
4. Run `{{prompt_test(action="ab_test", ...)}}` with at least 30 test cases
5. Compare results side by side and make a deploy/reject decision
6. If deploying, use `{{prompt_manager(action="promote", ...)}}` with a complete version record

**Success criteria:**

- Baseline metrics are recorded for at least 5 quality dimensions
- Failure analysis identified a specific, addressable error category
- A/B test used the same test suite and conditions for both versions
- Decision was based on data, not gut feeling
- Version record documents what changed, why, and what the test showed
- You know how to roll back in under 2 minutes if the new version underperforms

---

## Lesson: Customer Success

### Why This Matters

Acquiring a new client costs 5-7x more than retaining an existing one. Yet most AI solution operators focus almost exclusively on new sales, treating existing clients as "done" after deployment. This is a mistake with direct financial consequences:

- **Churn** -- a client who does not feel supported leaves at renewal time. You lose recurring revenue and gain a detractor.
- **Missed expansion** -- happy clients will buy more if prompted. A client using one AI workflow will adopt three more -- but only if someone notices they are ready.
- **Silent failure** -- the most dangerous client is the one who stops using your solution but does not tell you. By the time they cancel, it is too late.

Customer success is the discipline of proactively ensuring clients get value from your solution. It is not customer support (reactive, ticket-based). It is a continuous process of monitoring health, identifying risk, and creating expansion opportunities.

**The economics of customer success:**

```text
Scenario A: No customer success
  10 clients, $2,000/month each = $20,000/month
  Annual churn: 40% (4 clients leave)
  Year-end revenue: $12,000/month
  New clients needed to grow: 8+ (4 to replace + 4 to grow)

Scenario B: Active customer success
  10 clients, $2,000/month each = $20,000/month
  Annual churn: 10% (1 client leaves)
  Expansion: 3 clients upgrade to $3,500/month
  Year-end revenue: $22,500/month
  New clients needed to grow: 3-4
```

### How to Think About It

**Customer Health Score Framework**

A health score is a single number (0-100) that predicts whether a client is likely to renew, expand, or churn. It is built from four weighted signals:

```text
HEALTH SCORE FORMULA

SIGNAL 1: ENGAGEMENT (weight: 35%)
  What to measure:
    - Login frequency (daily, weekly, monthly)
    - Active users vs licensed users
    - Feature breadth (how many features used)
  Scoring:
    90-100: Daily active use, >80% of users active, multiple features
    60-89:  Weekly use, 50-80% active, core features only
    30-59:  Monthly or less, <50% active, minimal feature usage
    0-29:   Rarely or never used

SIGNAL 2: OUTCOMES (weight: 30%)
  What to measure:
    - Tasks completed per week
    - Time saved (compared to baseline)
    - Error rate reduction
    - Business KPIs moving in right direction
  Scoring:
    90-100: Exceeding promised outcomes
    60-89:  Meeting promised outcomes
    30-59:  Below expectations
    0-29:   No measurable outcomes

SIGNAL 3: SUPPORT HEALTH (weight: 20%)
  What to measure:
    - Support ticket volume (trending up = bad)
    - Ticket severity distribution
    - Time to resolution
    - Repeated issues
  Scoring:
    90-100: Rare tickets, quickly resolved, no repeat issues
    60-89:  Occasional tickets, reasonable resolution
    30-59:  Frequent tickets, escalations, slow resolution
    0-29:   Constant issues, unresolved problems, frustration

SIGNAL 4: RELATIONSHIP (weight: 15%)
  What to measure:
    - NPS score (last survey)
    - Executive sponsor engagement
    - Responsiveness to communications
    - Referral willingness
  Scoring:
    90-100: Promoter, engaged sponsor, quick responses
    60-89:  Passive, some engagement
    30-59:  Detractor signals, slow responses
    0-29:   Unresponsive, sponsor departed, complaints

OVERALL HEALTH = (Engagement x 0.35) + (Outcomes x 0.30) +
                 (Support x 0.20) + (Relationship x 0.15)
```

**Health Score Action Triggers**

```text
HEALTH SCORE RESPONSE FRAMEWORK

Score 80-100: HEALTHY
  Action: Quarterly check-in, look for expansion opportunities
  Cadence: Monthly automated report, quarterly personal review
  Focus: "How can we help you do more?"

Score 60-79: ATTENTION NEEDED
  Action: Bi-weekly check-in, investigate which signal is low
  Cadence: Bi-weekly personal check-in
  Focus: "We noticed X -- let us get it back on track"

Score 40-59: AT RISK
  Action: Weekly check-in, create improvement plan, escalate internally
  Cadence: Weekly personal call
  Focus: "Here is our plan to fix the issues you are experiencing"

Score 0-39: CRITICAL
  Action: Immediate intervention, executive-to-executive conversation
  Cadence: Multiple times per week
  Focus: "We understand there are serious issues and we are making this our top priority"
```

**Expansion Signals: When Clients Are Ready for More**

```text
EXPANSION SIGNAL DETECTION

Signal                              What It Means                   Action
----------------------------------  ----------------------------    -----------------
Usage hitting capacity limits       They need more scale            Offer tier upgrade
New department asking for access    Demand spreading organically    Propose department rollout
Client asking "can it also do X?"   They see value, want more       Scope the "X" as an add-on
Consistently exceeding KPIs         Strong ROI, budget available    Propose additional use case
Champion promoted internally        AI initiative got credit        Leverage their success story
Contract renewal approaching        Natural expansion conversation  Bundle expansion into renewal
```

**Churn Early Warning Signs**

```text
CHURN RISK INDICATORS (ordered by urgency)

CRITICAL (act this week):
  - Executive sponsor left the company
  - Client requested data export
  - Support tickets tripled in 30 days
  - Client missed 2+ scheduled check-ins

HIGH (act this month):
  - Active usage down 30%+ over 60 days
  - Client stopped using key features
  - Negative NPS score (detractor)
  - Client reviewing competitor tools

MODERATE (investigate):
  - Usage plateaued (not growing, not shrinking)
  - Client rescheduling or shortening check-ins
  - New decision-maker unfamiliar with the solution
  - Invoice payment delays
```

### Step-by-Step Approach

**Step 1: Set up health scoring for all clients**

```text
{{customer_lifecycle(
  action="configure_health_scoring",
  scoring_model={
    "engagement": {"weight": 0.35, "source": "usage_analytics"},
    "outcomes": {"weight": 0.30, "source": "kpi_tracking"},
    "support": {"weight": 0.20, "source": "ticket_system"},
    "relationship": {"weight": 0.15, "source": "nps_surveys"}
  },
  thresholds={
    "healthy": 80,
    "attention": 60,
    "at_risk": 40,
    "critical": 0
  },
  update_frequency="weekly"
)}}
```

**Step 2: Generate the current portfolio health report**

```text
{{customer_lifecycle(
  action="health_report",
  scope="all_customers",
  include=["health_score", "score_trend", "top_risk_factor", "recommended_action"],
  sort_by="health_score_ascending"
)}}
```

This produces a ranked list of all clients, worst-health first, with specific recommended actions for each.

**Step 3: Set up churn detection alerts**

```text
{{customer_lifecycle(
  action="configure_alerts",
  alerts=[
    {
      "name": "usage_drop",
      "condition": "active_usage_down_30_percent_over_60_days",
      "severity": "high",
      "notify": "account-manager"
    },
    {
      "name": "sponsor_change",
      "condition": "executive_sponsor_role_changed_or_departed",
      "severity": "critical",
      "notify": ["account-manager", "team-lead"]
    },
    {
      "name": "support_spike",
      "condition": "ticket_volume_3x_baseline_over_30_days",
      "severity": "critical",
      "notify": "account-manager"
    },
    {
      "name": "expansion_signal",
      "condition": "usage_near_capacity_or_new_department_requesting_access",
      "severity": "info",
      "notify": "account-manager"
    },
    {
      "name": "renewal_approaching",
      "condition": "contract_renewal_within_90_days",
      "severity": "info",
      "notify": ["account-manager", "team-lead"]
    }
  ]
)}}
```

**Step 4: Create an intervention playbook for at-risk clients**

```text
{{customer_lifecycle(
  action="create_playbook",
  playbook_name="at_risk_intervention",
  trigger="health_score < 60",
  steps=[
    {
      "day": 1,
      "action": "review_all_four_health_signals",
      "tool": "{{customer_lifecycle(action='health_detail', customer_id='...')}}"
    },
    {
      "day": 2,
      "action": "schedule_call_with_client_champion",
      "goal": "understand_their_perspective"
    },
    {
      "day": 3,
      "action": "create_improvement_plan",
      "includes": ["root_cause", "actions", "timeline", "success_criteria"]
    },
    {
      "day": 7,
      "action": "deliver_improvement_plan_to_client",
      "goal": "demonstrate_proactive_ownership"
    },
    {
      "day": 14,
      "action": "first_progress_check",
      "tool": "{{customer_lifecycle(action='health_detail', customer_id='...')}}"
    },
    {
      "day": 30,
      "action": "reassess_health_score",
      "success": "score_improved_by_10_points_or_more"
    }
  ]
)}}
```

**Step 5: Set up the feedback collection loop**

```text
{{customer_lifecycle(
  action="configure_feedback",
  channels=[
    {
      "type": "nps_survey",
      "frequency": "quarterly",
      "audience": "all_active_users",
      "follow_up": "personal_outreach_to_detractors"
    },
    {
      "type": "feature_request_tracking",
      "source": "support_tickets_tagged_feature_request",
      "review_cadence": "monthly",
      "prioritize_by": "customer_health_score_weighted"
    },
    {
      "type": "usage_analytics",
      "track": ["feature_adoption", "abandoned_workflows", "error_points"],
      "review_cadence": "weekly"
    }
  ]
)}}
```

### What Good Looks Like

**A properly managed customer success program has these properties:**

- Every client has a health score that is updated at least weekly
- At-risk clients are identified before they express dissatisfaction
- Expansion conversations happen during health check-ins, not as cold sales calls
- Churn rate is under 15% annually (under 10% is excellent)
- Feedback from clients directly influences the product roadmap
- Every client interaction is logged, creating a relationship history
- Renewal preparation starts 90 days before contract end, not 30

**Common mistakes to avoid:**

| Mistake | Risk | Fix |
|---|---|---|
| Treating all clients the same | Over-investing in healthy clients, neglecting at-risk ones | Use health scores to allocate attention proportionally |
| Relying on gut feeling for health | Miss silent churn signals | Use data-driven health scoring with weighted signals |
| Only contacting clients when selling | Clients feel used, not supported | Regular value-focused check-ins, not sales calls |
| Ignoring detractor NPS responses | Detractors churn and tell others | Personal outreach within 48 hours of detractor response |
| No expansion playbook | Leave revenue on the table | Track expansion signals, have a ready proposal for each |
| Waiting for contract renewal to check in | Problems compound for months unaddressed | Monthly or quarterly check-ins, minimum |

### Practice Exercise

Set up a customer success program for your current client portfolio:

1. Run `{{customer_lifecycle(action="configure_health_scoring", ...)}}` with all four signals weighted
2. Run `{{customer_lifecycle(action="health_report", ...)}}` to see your current portfolio health
3. Identify your lowest-health client and investigate which signal is driving the score down
4. Set up churn detection alerts for at least 3 risk indicators
5. Create an intervention playbook for at-risk clients
6. Configure a quarterly NPS survey with automatic detractor follow-up

**Success criteria:**

- Every client has a health score and you can explain what drives it
- You can rank your clients from healthiest to most at-risk
- At least 3 churn alerts are configured and tested
- An intervention playbook exists with specific steps and timelines
- You can identify one client showing expansion signals and propose a concrete next step
- Feedback collection is configured across at least 2 channels
