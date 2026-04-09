# Module 2: Solution Design Mastery

> **Learning Path:** AI Solution Architect
> **Audience:** Non-technical business operators learning AI solution architecture
> **Prerequisites:** Completed Module 1: Discovery Fundamentals

---

## Lesson: Task Classification Framework

### Why This Matters

The single most expensive mistake in AI solution design is automating the wrong tasks. Not every task should be handled by AI, and not every task needs a human. Getting this classification wrong leads to:

- **Over-automation:** AI handles tasks it should not, producing errors that damage the client's business and reputation
- **Under-automation:** Humans do repetitive work that AI could handle perfectly, wasting time and money
- **Wrong hybrid balance:** AI and humans step on each other, creating slower processes than the original

Task classification is the bridge between discovery ("here are the problems") and design ("here is the solution"). It answers the most important question in AI solutioning: **For each task in the process, should a human do it, should AI do it, or should they do it together?**

**The cost of getting it wrong:**

| Classification Error | Consequence | Example |
|---|---|---|
| AI handles a judgment task | Bad decisions at scale | AI auto-approves refunds that should be reviewed |
| Human handles a repetitive task | Wasted labor budget | Staff manually formats 200 reports/week that AI could generate |
| No human review on high-stakes AI output | Liability exposure | AI sends incorrect insurance quotes without review |
| Human reviews every AI output | Eliminates time savings | Staff checks every AI-written email, negating the automation |

### How to Think About It

**The Human/AI/Hybrid Decision Tree**

For each task in a process, walk through this decision tree:

```text
START: Take one task from the process map
  |
  Q1: Is it repetitive (same pattern, different data)?
  |     |
  |     NO --> Q2: Does it require creative judgment or empathy?
  |     |        |
  |     |        YES --> HUMAN TASK
  |     |        |       (examples: negotiation, conflict resolution,
  |     |        |        creative strategy, relationship building)
  |     |        |
  |     |        NO --> Q3: Does it require real-time physical presence?
  |     |                 |
  |     |                 YES --> HUMAN TASK
  |     |                 NO  --> EVALUATE FURTHER (may be hybrid)
  |     |
  |     YES --> Q4: Is the output predictable and structured?
  |               |
  |               YES --> Q5: What is the error tolerance?
  |               |         |
  |               |         HIGH (errors are cheap to fix) --> FULL AI AUTOMATION
  |               |         |    (examples: data formatting, email sorting,
  |               |         |     report generation, calendar scheduling)
  |               |         |
  |               |         LOW (errors are costly) --> HYBRID: AI + HUMAN REVIEW
  |               |              (examples: financial calculations, medical info,
  |               |               legal documents, customer-facing communications)
  |               |
  |               NO --> Q6: Can the output be evaluated after the fact?
  |                       |
  |                       YES --> HYBRID: AI DRAFT + HUMAN EDIT
  |                       |       (examples: content writing, proposal drafts,
  |                       |        analysis summaries)
  |                       |
  |                       NO --> HUMAN TASK with AI ASSISTANCE
  |                              (examples: live customer calls with AI
  |                               suggestions, complex troubleshooting
  |                               with AI knowledge base)
```

**Automation Scoring Methodology**

For tasks that land in the AI or Hybrid categories, score them on 4 dimensions to prioritize which to automate first:

| Dimension | Score 1-2 | Score 3-4 | Score 5 |
|---|---|---|---|
| **Volume** | Less than 10/week | 10-100/week | 100+/week |
| **Consistency** | Every instance is different | Most follow a pattern with exceptions | Nearly identical every time |
| **Data Availability** | Data is scattered or missing | Data exists but needs preparation | Data is clean and accessible |
| **Error Tolerance** | Errors are catastrophic | Errors are costly but fixable | Errors are minor and easily caught |

**Total Automation Score** = Volume + Consistency + Data Availability + Error Tolerance (range: 4-20)

- **16-20:** Automate immediately. This is a quick win.
- **10-15:** Automate with safeguards. Include human review checkpoints.
- **4-9:** Defer automation. Either the data is not ready or the risk is too high. Address prerequisites first.

### Step-by-Step Approach

**Step 1: List all tasks from your process map**

Pull the process map from your business X-ray and list every discrete task:

```text
{{ai_migration(action="classify_tasks", company="Harbor Freight Logistics", process="freight_quoting", tasks=[{"id": "T1", "name": "Receive and parse quote request email", "description": "Read incoming email, extract shipment details (origin, destination, weight, dimensions, commodity type)", "current_time_minutes": 2, "frequency_daily": 30}, {"id": "T2", "name": "Look up carrier rates", "description": "Check 3 carrier portals for rates matching the shipment parameters", "current_time_minutes": 15, "frequency_daily": 30}, {"id": "T3", "name": "Calculate surcharges and accessorials", "description": "Apply fuel surcharges, residential delivery fees, liftgate charges based on shipment specifics", "current_time_minutes": 10, "frequency_daily": 30}, {"id": "T4", "name": "Build quote document", "description": "Create formatted quote with line items, terms, and expiration date", "current_time_minutes": 8, "frequency_daily": 30}, {"id": "T5", "name": "Manager approval for quotes over $5000", "description": "Route high-value quotes to manager for rate validation and margin check", "current_time_minutes": 10, "frequency_daily": 8}, {"id": "T6", "name": "Send quote to customer", "description": "Email formatted quote with cover note personalized to customer relationship", "current_time_minutes": 5, "frequency_daily": 30}])}}
```

**Step 2: Classify each task**

```text
{{ai_migration(action="classify_results", company="Harbor Freight Logistics", classifications=[{"task_id": "T1", "classification": "full_ai", "reasoning": "Repetitive, structured input (email), predictable output (data fields). Errors are easy to catch.", "automation_score": {"volume": 5, "consistency": 4, "data_availability": 5, "error_tolerance": 4, "total": 18}}, {"task_id": "T2", "classification": "full_ai", "reasoning": "Repetitive API calls with structured parameters. AI can query all carriers simultaneously instead of sequentially.", "automation_score": {"volume": 5, "consistency": 5, "data_availability": 4, "error_tolerance": 3, "total": 17}}, {"task_id": "T3", "classification": "hybrid_ai_review", "reasoning": "Calculations are formulaic but surcharge rules change. AI calculates, human spot-checks monthly.", "automation_score": {"volume": 5, "consistency": 4, "data_availability": 4, "error_tolerance": 3, "total": 16}}, {"task_id": "T4", "classification": "full_ai", "reasoning": "Template-based document generation from structured data. No judgment required.", "automation_score": {"volume": 5, "consistency": 5, "data_availability": 5, "error_tolerance": 4, "total": 19}}, {"task_id": "T5", "classification": "hybrid_human_lead", "reasoning": "Requires margin judgment and customer relationship context. AI can pre-check against pricing rules and flag anomalies.", "automation_score": {"volume": 3, "consistency": 3, "data_availability": 4, "error_tolerance": 2, "total": 12}}, {"task_id": "T6", "classification": "hybrid_ai_draft", "reasoning": "AI generates personalized cover note, human reviews before sending for key accounts. Auto-send for standard accounts.", "automation_score": {"volume": 5, "consistency": 4, "data_availability": 4, "error_tolerance": 3, "total": 16}}])}}
```

**Step 3: Calculate the impact**

```text
Current daily time: (2+15+10+8+10+5) x 30 = 1,500 minutes = 25 hours/day
Projected daily time after AI: ~4 hours/day (manager reviews + spot checks + key account reviews)
Daily savings: 21 hours
Annual savings at $30/hour: 21 x 260 x $30 = $163,800
```

**Step 4: Document the migration plan**

```text
{{ai_migration(action="create_plan", company="Harbor Freight Logistics", plan={"phase_1": {"tasks": ["T1", "T4"], "description": "Email parsing and quote document generation - lowest risk, highest consistency", "timeline": "weeks 1-3", "expected_savings": "10 min per quote"}, "phase_2": {"tasks": ["T2", "T3"], "description": "Carrier rate lookup and surcharge calculation - requires API setup", "timeline": "weeks 4-6", "expected_savings": "25 min per quote"}, "phase_3": {"tasks": ["T5", "T6"], "description": "Smart approval routing and personalized sending - requires training", "timeline": "weeks 7-8", "expected_savings": "10 min per applicable quote"}})}}
```

### What Good Looks Like

**Strong task classification:**

- Every task has a clear classification with written reasoning
- Automation scores are based on evidence, not optimism
- High-stakes tasks always have human review, no exceptions
- The migration plan phases tasks by risk level (low risk first)
- Savings calculations use conservative estimates

**Weak task classification:**

- Everything is classified as "full AI" (over-optimistic)
- No reasoning documented for classifications
- Error tolerance is not considered
- All tasks are planned for simultaneous deployment
- Savings calculations assume 100% AI accuracy from day one

**The critical mistake:** Classifying a task as "full AI" when it has low error tolerance. If an AI error in that task could cost the client money, reputation, or legal exposure, it must be hybrid with human review. Always. No exceptions. The time savings from removing human review are never worth the risk of a single catastrophic error.

### Practice Exercise

**Scenario:** A property management company has this tenant move-in process:

1. Receive signed lease (email attachment)
2. Extract lease terms (start date, rent amount, deposit, pet policy)
3. Create tenant record in property management software
4. Generate welcome packet (building rules, contact info, parking, utilities)
5. Schedule move-in inspection
6. Send welcome email with packet and inspection date
7. Collect security deposit and first month's rent
8. Conduct move-in inspection and document condition

**Task:** Classify each step using the decision tree. Score the automatable tasks. Create a phased migration plan.

**Self-check questions:**

- Did you classify Step 7 (collecting money) as requiring human involvement? (It should be — financial transactions need human verification)
- Did you classify Step 8 (physical inspection) as a human task? (It must be — requires physical presence)
- Is your Phase 1 the lowest-risk set of tasks? If you put lease extraction in Phase 1, reconsider — extracting legal terms incorrectly has real consequences. Document generation (Step 4) is a safer starting point.

---

## Lesson: Workflow Design Patterns

### Why This Matters

A workflow is the operational backbone of your AI solution. It defines not just what happens, but in what order, under what conditions, and what to do when things go wrong.

Without proper workflow design:

- AI outputs pile up with nobody acting on them
- Errors cascade through the system because there are no checkpoints
- Edge cases cause silent failures that nobody notices for weeks
- The client's team does not trust the system because they do not understand when it acts and when it waits

**The difference between a tool and a solution:**

A tool does one thing. A solution orchestrates multiple tools and people into a reliable, repeatable process. Workflow design is what turns your collection of AI capabilities into a solution the client can depend on.

### How to Think About It

**Pattern 1: Sequential Workflow**

Tasks execute one after another. The output of each step feeds into the next.

```text
[Step 1] --> [Step 2] --> [Step 3] --> [Step 4] --> [Done]
```

**When to use:** The process is linear, each step depends on the previous step's output, and there is no opportunity to do things in parallel.

**Example:** Invoice processing: Receive invoice --> Extract data --> Match to PO --> Flag discrepancies --> Route for approval

**Pattern 2: Parallel Workflow**

Independent tasks execute simultaneously, then results are combined.

```text
          +--> [Step 2a] --+
[Step 1] -+--> [Step 2b] --+--> [Step 3] --> [Done]
          +--> [Step 2c] --+
```

**When to use:** Multiple independent tasks can happen at the same time, and a later step needs all their outputs.

**Example:** Freight quoting: Parse request --> [Query Carrier A + Query Carrier B + Query Carrier C] --> Compare rates --> Build quote

**Pattern 3: Human-in-the-Loop**

AI processes to a decision point, then a human reviews, approves, modifies, or rejects before the workflow continues.

```text
[AI Process] --> [Decision Point] --> {Human Review}
                                         |
                              +----------+----------+
                              |          |          |
                          [Approve]  [Modify]   [Reject]
                              |          |          |
                          [Continue] [Re-process] [End/Escalate]
```

**Three flavors of human-in-the-loop:**

| Pattern | When Human Gets Involved | Best For |
|---|---|---|
| **Approval Gate** | Every output goes to human for yes/no | High-stakes outputs (legal, financial, medical) |
| **Confidence Threshold** | Only when AI confidence is below a threshold | High-volume tasks where most outputs are routine |
| **Escalation Trigger** | Only when specific conditions are met | Exception handling (unusual amounts, new customers, flagged content) |

**Confidence threshold example:**

```text
AI processes task --> Confidence score?
                        |
              +---------+---------+
              |                   |
         >= 90%              < 90%
              |                   |
      [Auto-proceed]     [Route to human]
```

**Pattern 4: Error Handling**

Every workflow needs a plan for what happens when things go wrong.

| Strategy | How It Works | When to Use |
|---|---|---|
| **Retry** | Try the same step again (with optional delay) | Transient failures (API timeout, rate limit) |
| **Fallback** | Use an alternative method | Primary method unavailable (backup API, manual process) |
| **Alert** | Notify a human and pause | Unknown error or data anomaly |
| **Circuit Breaker** | After N failures, stop trying and alert | Prevent cascading failures |

```text
[Step fails] --> Retry (up to 3 times)
                    |
                 Still failing?
                    |
              YES --+--> Fallback available?
                           |
                     YES --+--> [Use fallback]
                           |
                     NO ---+--> [Alert human, pause workflow]
```

### Step-by-Step Approach

**Step 1: Define the workflow using the workflow engine**

```text
{{workflow_engine(action="create_workflow", name="freight_quote_automation", company="Harbor Freight Logistics", data={"description": "Automated freight quoting from email request to customer delivery", "trigger": {"type": "email", "condition": "new email to quotes@harborfreight.example.com"}, "steps": [{"id": "parse_request", "type": "ai", "action": "Extract shipment details from email", "input": "incoming_email", "output": "shipment_data", "error_handling": {"strategy": "alert", "message": "Could not parse quote request email"}}, {"id": "validate_data", "type": "ai", "action": "Validate extracted data has all required fields", "input": "shipment_data", "output": "validated_data", "error_handling": {"strategy": "alert", "message": "Missing required shipment fields", "include_fields": "missing_fields"}}, {"id": "get_rates", "type": "parallel", "steps": [{"id": "rate_carrier_a", "action": "Query Carrier A API", "error_handling": {"strategy": "retry", "max_retries": 3, "delay_seconds": 5}}, {"id": "rate_carrier_b", "action": "Query Carrier B API", "error_handling": {"strategy": "retry", "max_retries": 3, "delay_seconds": 5}}, {"id": "rate_carrier_c", "action": "Query Carrier C API", "error_handling": {"strategy": "retry", "max_retries": 3, "delay_seconds": 5}}], "output": "carrier_rates", "min_required": 2, "error_handling": {"strategy": "fallback", "fallback_action": "Use cached rates from last 24 hours"}}, {"id": "calculate_total", "type": "ai", "action": "Apply surcharges and calculate final rates per carrier", "input": "carrier_rates + validated_data", "output": "final_rates"}, {"id": "generate_quote", "type": "ai", "action": "Generate formatted quote document with all carrier options", "input": "final_rates + shipment_data", "output": "quote_document"}, {"id": "approval_check", "type": "condition", "condition": "highest_rate > 5000", "if_true": "route_to_manager", "if_false": "send_quote"}, {"id": "route_to_manager", "type": "human_review", "action": "Manager reviews high-value quote", "assignee": "sales_manager", "timeout_hours": 4, "timeout_action": "escalate_to_director"}, {"id": "send_quote", "type": "ai", "action": "Generate personalized email and send quote to customer", "input": "quote_document + customer_data", "output": "sent_confirmation"}]})}}
```

**Step 2: Define escalation rules**

```text
{{workflow_engine(action="set_escalation", workflow="freight_quote_automation", rules=[{"trigger": "human_review_timeout", "after_hours": 4, "action": "notify_director", "message": "Quote awaiting approval for over 4 hours"}, {"trigger": "total_workflow_time", "after_minutes": 30, "action": "alert_ops", "message": "Quote workflow taking longer than expected"}, {"trigger": "error_count", "threshold": 3, "window_hours": 1, "action": "pause_workflow", "message": "Multiple failures detected, pausing for investigation"}])}}
```

**Step 3: Define confidence thresholds**

```text
{{workflow_engine(action="set_thresholds", workflow="freight_quote_automation", thresholds=[{"step": "parse_request", "field": "extraction_confidence", "auto_proceed": 0.90, "human_review": 0.70, "reject_below": 0.70, "reject_action": "alert human with original email"}, {"step": "calculate_total", "field": "rate_confidence", "auto_proceed": 0.95, "human_review": 0.80, "reject_below": 0.80, "reject_action": "flag for manual calculation"}])}}
```

**Step 4: Test the workflow with edge cases**

Before going live, walk through these scenarios:

```text
{{workflow_engine(action="test_scenario", workflow="freight_quote_automation", scenarios=[{"name": "Happy path", "input": "Standard shipment, all carriers respond, under $5000", "expected": "Quote sent automatically within 5 minutes"}, {"name": "High-value quote", "input": "Large shipment, quote is $8500", "expected": "Routes to manager for approval"}, {"name": "Carrier API down", "input": "Carrier A API returns 503", "expected": "Retries 3x, then uses cached rates"}, {"name": "Unparseable email", "input": "Email is a forwarded chain with no clear shipment details", "expected": "Alert human with original email, pause workflow"}, {"name": "All carriers down", "input": "All 3 carrier APIs timeout", "expected": "Fallback to cached rates if available, otherwise alert human"}])}}
```

### What Good Looks Like

**A well-designed workflow has:**

- Clear trigger conditions (what starts the workflow)
- Defined outputs for every step (what does each step produce)
- Error handling on every step that can fail (not just the "risky" ones)
- Human review at appropriate decision points based on stakes and confidence
- Timeout handling (what happens when a step or a human takes too long)
- Edge case scenarios tested before going live

**A poorly designed workflow has:**

- No error handling ("it will just work")
- Human review on every step (defeats the purpose of automation)
- No timeouts (workflows that stall silently)
- No parallel steps when they are possible (unnecessary slowness)
- Only happy path tested

**The three questions every workflow step must answer:**

1. What triggers this step?
2. What does this step produce?
3. What happens if this step fails?

If any step cannot answer all three, the workflow is not ready.

### Practice Exercise

**Scenario:** Design a workflow for automated tenant maintenance request handling at a property management company.

Process: Tenant submits request (email/text) --> Categorize urgency --> Route to appropriate vendor --> Track completion --> Notify tenant

**Requirements:**

- Emergency requests (water leak, no heat, security issue) must alert property manager immediately
- Routine requests (appliance repair, paint touch-up) can be auto-routed to the appropriate vendor
- Vendor must confirm receipt within 2 hours or escalate
- Tenant gets status updates at each stage

**Task:** Create the complete workflow using the workflow engine tool, including:

1. Parallel paths for emergency vs. routine
2. Confidence thresholds for urgency classification
3. Error handling for vendor non-response
4. At least 3 test scenarios

**Self-check:** Does your workflow handle the case where the AI misclassifies an emergency as routine? This is the most dangerous failure mode. Your confidence threshold for urgency classification should be high (95%+) and anything below that threshold should default to human review, not to "routine."

---

## Lesson: Architecture with Diagram Architect

### Why This Matters

Architecture is the blueprint of your AI solution. It answers: what systems are involved, how do they communicate, and what happens as usage grows?

Without clear architecture:

- Integrations break because nobody mapped the data flow
- The system works for 10 users but crashes at 100
- The client's IT team cannot maintain what you built because they do not understand it
- Scope creep is invisible because there are no clear boundaries

Architecture diagrams are not decorative. They are the single source of truth for what the system does and does not do. Every stakeholder, from the CEO to the IT admin, should be able to look at the architecture and understand their piece of it.

### How to Think About It

**System Boundaries: Inside vs. Outside**

The first and most important architectural decision is: what is inside your solution and what is outside it?

```text
+--------------------------------------------------+
|                YOUR SOLUTION                      |
|                                                   |
|  +-------------+  +-------------+  +----------+  |
|  | AI Engine   |  | Workflow    |  | Dashboard |  |
|  | (prompts,   |  | Engine      |  | (status,  |  |
|  |  models)    |  | (automation)|  |  reports)  |  |
|  +------+------+  +------+------+  +-----+----+  |
|         |                |               |        |
+---------+----------------+---------------+--------+
          |                |               |
    ------+----------------+---------------+--------
          |                |               |
  +-------+------+  +-----+------+  +-----+------+
  | Client's CRM |  | Email      |  | Carrier    |
  | (Salesforce) |  | (Outlook)  |  | APIs       |
  +--[OUTSIDE]---+  +--[OUTSIDE]-+  +--[OUTSIDE]-+
```

**Rules for boundaries:**

- You own and control everything inside the boundary
- You integrate with but do not control anything outside the boundary
- Every line crossing the boundary is an integration point that can fail
- Fewer boundary crossings = simpler, more reliable system

**Integration Patterns**

There are four ways systems talk to each other. Choose based on the use case:

| Pattern | How It Works | When to Use | Example |
|---|---|---|---|
| **API** | System A calls System B directly and waits for response | Real-time data needed, low-medium volume | Check carrier rates on demand |
| **Webhook** | System B notifies System A when something happens | Event-driven, do not want to poll | CRM notifies you when a deal closes |
| **Batch** | Transfer data in bulk on a schedule | High volume, no real-time need | Sync customer list nightly |
| **Streaming** | Continuous real-time data flow | High volume, real-time need | Live chat message processing |

**Decision guide:**

```text
Do you need the data in real-time?
  |
  YES --> Is the volume high (100+ events/minute)?
  |         |
  |         YES --> STREAMING
  |         NO  --> Who initiates?
  |                   |
  |                   Your system --> API
  |                   Their system --> WEBHOOK
  |
  NO --> BATCH (schedule: hourly, daily, weekly based on freshness needs)
```

**Scaling Considerations**

Your solution must handle growth. Think about scaling from day one, even if the initial deployment is small.

| Concern | Question to Ask | Design Response |
|---|---|---|
| **User growth** | What if they go from 5 to 50 users? | Ensure stateless design, no single-user bottlenecks |
| **Data growth** | What if data volume 10x in a year? | Plan for pagination, archiving, efficient queries |
| **Request spikes** | What if volume spikes (e.g., holiday season)? | Implement queuing to buffer peaks |
| **API limits** | What are the rate limits on external APIs? | Add caching layer, respect rate limits with backoff |

**Caching strategy (simplified):**

```text
Request comes in --> Is the answer in cache?
                        |
                   YES --+--> Is the cache fresh (< max age)?
                   |           |
                   |      YES --+--> Return cached answer (fast)
                   |           |
                   |      NO ---+--> Fetch fresh answer, update cache
                   |
                   NO ---+--> Fetch answer, store in cache
```

Cache things that are expensive to compute and do not change frequently. Carrier rates might be cacheable for 1 hour. Customer names can be cached for a day. Account balances should never be cached.

### Step-by-Step Approach

**Step 1: Define system components**

```text
{{diagram_architect(action="create_architecture", name="harbor_freight_quoting_system", data={"components": [{"id": "agent_mahoo", "type": "core", "name": "Agent Mahoo Platform", "description": "Central AI and workflow engine"}, {"id": "email_parser", "type": "module", "name": "Email Parser", "description": "Extracts shipment data from incoming emails", "parent": "agent_mahoo"}, {"id": "rate_engine", "type": "module", "name": "Rate Engine", "description": "Queries carriers and calculates final rates", "parent": "agent_mahoo"}, {"id": "quote_generator", "type": "module", "name": "Quote Generator", "description": "Creates formatted quote documents", "parent": "agent_mahoo"}, {"id": "workflow_engine", "type": "module", "name": "Workflow Orchestrator", "description": "Manages the quoting pipeline and approvals", "parent": "agent_mahoo"}, {"id": "dashboard", "type": "module", "name": "Operations Dashboard", "description": "Quote status, metrics, and reporting", "parent": "agent_mahoo"}, {"id": "outlook", "type": "external", "name": "Microsoft Outlook", "description": "Email system for receiving requests and sending quotes"}, {"id": "carrier_a", "type": "external", "name": "Carrier A API", "description": "Freight rate API"}, {"id": "carrier_b", "type": "external", "name": "Carrier B API", "description": "Freight rate API"}, {"id": "carrier_c", "type": "external", "name": "Carrier C API", "description": "Freight rate API"}, {"id": "crm", "type": "external", "name": "Salesforce CRM", "description": "Customer data and deal tracking"}]})}}
```

**Step 2: Define integrations**

```text
{{diagram_architect(action="add_integrations", architecture="harbor_freight_quoting_system", integrations=[{"from": "outlook", "to": "email_parser", "pattern": "webhook", "description": "New email triggers parsing", "data_flow": "raw email content", "frequency": "event-driven, ~30/day", "error_handling": "retry 3x, then alert"}, {"from": "rate_engine", "to": "carrier_a", "pattern": "api", "description": "Query carrier rates", "data_flow": "shipment params in, rates out", "frequency": "on-demand, ~30/day", "error_handling": "retry 3x, fallback to cached rates", "rate_limit": "100 calls/hour"}, {"from": "rate_engine", "to": "carrier_b", "pattern": "api", "description": "Query carrier rates", "data_flow": "shipment params in, rates out", "frequency": "on-demand, ~30/day", "error_handling": "retry 3x, fallback to cached rates", "rate_limit": "50 calls/hour"}, {"from": "rate_engine", "to": "carrier_c", "pattern": "api", "description": "Query carrier rates", "data_flow": "shipment params in, rates out", "frequency": "on-demand, ~30/day", "error_handling": "retry 3x, fallback to cached rates", "rate_limit": "200 calls/hour"}, {"from": "crm", "to": "agent_mahoo", "pattern": "batch", "description": "Sync customer data nightly", "data_flow": "customer records", "frequency": "daily at 2am", "error_handling": "alert on failure, use previous sync"}, {"from": "quote_generator", "to": "outlook", "pattern": "api", "description": "Send quote email", "data_flow": "formatted email with attachment", "frequency": "on-demand, ~30/day", "error_handling": "retry 3x, alert if still failing"}])}}
```

**Step 3: Generate the architecture diagram**

```text
{{diagram_architect(action="generate_diagram", architecture="harbor_freight_quoting_system", format="mermaid", options={"show_data_flow": true, "show_error_handling": true, "show_external_boundary": true})}}
```

**Step 4: Document scaling plan**

```text
{{diagram_architect(action="add_scaling_notes", architecture="harbor_freight_quoting_system", notes={"current_load": "30 quotes/day, 5 users", "projected_load_6mo": "100 quotes/day, 15 users", "projected_load_12mo": "300 quotes/day, 30 users", "scaling_strategy": [{"component": "rate_engine", "concern": "Carrier API rate limits", "mitigation": "Add caching layer with 1-hour TTL for repeated routes"}, {"component": "email_parser", "concern": "Volume spikes on Mondays", "mitigation": "Queue incoming emails, process at steady rate"}, {"component": "dashboard", "concern": "Report generation for large datasets", "mitigation": "Pre-compute daily aggregates, paginate detail views"}]})}}
```

### What Good Looks Like

**A strong architecture:**

- Has clear boundaries between your system and external systems
- Documents every integration point with pattern, data flow, and error handling
- Includes a scaling plan even for small initial deployments
- Can be understood by non-technical stakeholders (label things clearly, avoid jargon)
- Identifies single points of failure and has mitigation plans

**A weak architecture:**

- Everything is "inside the system" with no boundaries
- Integrations are listed but not detailed (no data flow, no error handling)
- No consideration of what happens when external systems are down
- Only shows the happy path
- Uses technical jargon that the client cannot understand

**Questions your architecture must answer:**

1. What happens when [external system] is down? (Every external system will go down eventually)
2. What happens when volume doubles? (Growth is the goal, not the exception)
3. Where does data live and who owns it? (Data ownership disputes kill projects)
4. How does a new team member understand this system? (If it requires tribal knowledge, it is too complex)

### Practice Exercise

**Scenario:** Design the architecture for the tenant maintenance request system from the previous lesson.

Systems involved:

- Agent Mahoo (your platform)
- Property management software (has API)
- Tenant communication channel (email/SMS)
- Vendor management system (spreadsheet today, suggest upgrade)
- Property manager's phone (for emergency alerts)

**Task:**

1. Define all components (internal and external)
2. Define all integrations with patterns and error handling
3. Generate a diagram
4. Identify the top 3 scaling concerns

**Self-check:** Count the lines crossing your system boundary. Each one is a potential failure point. If you have more than 6 boundary crossings, consider whether some external systems could be consolidated or whether some integrations could use batch instead of real-time to reduce failure surface.

---

## Lesson: Prompt Engineering Basics

### Why This Matters

Prompts are the instructions you give to the AI. They are the most important piece of your solution because they directly control the quality of every AI output.

Bad prompts produce:

- Inconsistent outputs (different format every time)
- Hallucinated information (AI makes up facts that sound convincing)
- Off-target responses (technically correct but not what was needed)
- Fragile behavior (works for normal inputs, breaks on edge cases)

Good prompts produce:

- Consistent, predictable outputs you can build workflows around
- Grounded responses that use provided data, not imagination
- Focused results that address exactly what was asked
- Robust behavior that handles unusual inputs gracefully

Prompt engineering is not creative writing. It is systems engineering. You are programming the AI's behavior with natural language, and the same principles of clarity, specificity, and error handling apply.

### How to Think About It

**System Prompt Structure**

Every AI task in your solution needs a system prompt. Use this 4-part structure:

```text
+------------------+
| ROLE             |  Who is the AI in this context?
+------------------+
| CONTEXT          |  What information does it have access to?
+------------------+
| CONSTRAINTS      |  What must it NOT do?
+------------------+
| OUTPUT FORMAT    |  What should the response look like?
+------------------+
```

**Detailed breakdown:**

**1. Role** — Defines the AI's expertise and perspective.

| Weak Role | Strong Role |
|---|---|
| "You are a helpful assistant" | "You are a freight rate analyst for a logistics company. You have 10 years of experience evaluating carrier quotes and calculating total shipping costs including surcharges." |
| "You help with emails" | "You are a professional customer communications specialist. You write clear, warm, and concise emails to tenants of residential properties." |

**2. Context** — What the AI needs to know for this specific task.

- Business rules ("Our standard margin is 15% on all freight quotes")
- Reference data ("Here are the current fuel surcharge rates: ...")
- History ("Previous communications with this tenant: ...")
- Current state ("This is a quote request for a 2,000 lb shipment from Chicago to Miami")

**3. Constraints** — Guardrails that prevent harmful or unwanted outputs.

Critical constraints every prompt needs:

- "Do not make up information. If you do not have enough data, say so."
- "Do not provide legal/medical/financial advice. State facts and recommend professional consultation."
- "Do not include information from outside the provided context."
- "If the input is ambiguous, list the possible interpretations and ask for clarification."

**4. Output Format** — The exact structure of the response.

Specify format precisely. Do not leave it to the AI's judgment.

```text
WEAK: "Return the results in a nice format"
STRONG: "Return the results as a JSON object with these exact fields:
{
  'carrier_name': string,
  'base_rate': number,
  'fuel_surcharge': number,
  'total_rate': number,
  'estimated_transit_days': integer,
  'confidence': number between 0 and 1
}"
```

**Few-Shot Patterns: When and How to Use Examples**

Few-shot means giving the AI examples of desired input/output pairs. This is the single most effective way to get consistent outputs.

**When to use few-shot:**

- The output format is complex or unusual
- The task requires a specific style or tone
- Simple instructions produce inconsistent results
- The task involves classification into categories you define

**When NOT to use few-shot:**

- The task is simple and well-defined
- You need the AI to handle highly variable inputs creatively
- Adding examples would make the prompt too long and expensive

**Few-shot structure:**

```text
Here are examples of correct output:

EXAMPLE 1:
Input: [example input]
Output: [example output]

EXAMPLE 2:
Input: [different example input]
Output: [different example output]

Now process this:
Input: [actual input]
Output:
```

**Golden rule of few-shot:** Use 2-3 examples. One example is not enough to establish a pattern. More than 4 adds cost without improving quality.

**Output Structuring**

Always prefer structured output (JSON, markdown with headers, tables) over free-form text. Structured output is:

- Parseable by your workflow engine
- Consistent across runs
- Validatable (you can check if required fields are present)
- Composable (outputs can feed into other steps)

| Use Case | Best Format | Why |
|---|---|---|
| Data to be processed by another step | JSON | Machine-parseable, field-level validation |
| Reports for human reading | Markdown with headers | Scannable, printable, professional |
| Multi-option responses | Numbered list or table | Easy to reference and discuss |
| Yes/no decisions | JSON with `decision` and `reasoning` fields | Forces the AI to show its work |

### Step-by-Step Approach

**Step 1: Write the system prompt for a specific task**

Example: Email parsing for the freight quoting system.

```text
{{workflow_engine(action="set_prompt", workflow="freight_quote_automation", step="parse_request", prompt={"role": "You are an expert freight logistics coordinator. You extract shipment details from incoming email quote requests. You have extensive experience reading varied email formats from different customers and identifying the key shipment parameters.", "context": "You are processing emails sent to quotes@harborfreight.example.com. These emails come from customers requesting freight shipping quotes. Emails may be well-structured or informal. Some may be forwarded chains.", "constraints": ["Extract only information explicitly stated in the email. Do not infer or assume missing values.", "If a required field is not found in the email, set its value to null and set confidence to 0.5 or lower.", "Do not attempt to calculate rates or provide quotes. Your job is extraction only.", "If the email does not appear to be a quote request, set is_quote_request to false."], "output_format": {"type": "json", "schema": {"is_quote_request": "boolean", "confidence": "number 0-1", "origin_city": "string or null", "origin_state": "string or null", "origin_zip": "string or null", "destination_city": "string or null", "destination_state": "string or null", "destination_zip": "string or null", "weight_lbs": "number or null", "dimensions": {"length": "number or null", "width": "number or null", "height": "number or null"}, "commodity_type": "string or null", "special_requirements": "array of strings", "requested_delivery_date": "date string or null", "customer_name": "string or null", "customer_email": "string or null", "raw_notes": "string - any additional context from the email"}}, "examples": [{"input": "Hi, need a quote for 3 pallets of electronics going from our Dallas TX warehouse (75201) to Miami FL 33101. Total weight about 2400 lbs. Each pallet is 48x40x48. Need it there by March 30. Thanks, Bob Smith bob@acme.example.com", "output": {"is_quote_request": true, "confidence": 0.98, "origin_city": "Dallas", "origin_state": "TX", "origin_zip": "75201", "destination_city": "Miami", "destination_state": "FL", "destination_zip": "33101", "weight_lbs": 2400, "dimensions": {"length": 48, "width": 40, "height": 48}, "commodity_type": "electronics", "special_requirements": [], "requested_delivery_date": "2026-03-30", "customer_name": "Bob Smith", "customer_email": "bob@acme.example.com", "raw_notes": "3 pallets"}}, {"input": "FW: can you guys ship some stuff for us? we have boxes in our garage that need to go to our new office. maybe 500 pounds? not sure really. - jen", "output": {"is_quote_request": true, "confidence": 0.72, "origin_city": null, "origin_state": null, "origin_zip": null, "destination_city": null, "destination_state": null, "destination_zip": null, "weight_lbs": 500, "dimensions": {"length": null, "width": null, "height": null}, "commodity_type": "general merchandise", "special_requirements": [], "requested_delivery_date": null, "customer_name": "Jen", "customer_email": null, "raw_notes": "Vague request. Origin and destination addresses not provided. Weight is estimated. Residential pickup likely (mentioned garage)."}}]}}})}}
```

**Step 2: Write prompts for each AI step in the workflow**

Repeat the process for every AI step. Each prompt should be independent and self-contained — do not assume the AI "remembers" previous steps.

```text
{{workflow_engine(action="set_prompt", workflow="freight_quote_automation", step="generate_quote", prompt={"role": "You are a professional freight quoting specialist. You create clear, accurate, and well-formatted quote documents for customers.", "context": "You will receive structured shipment data and carrier rate comparisons. Your job is to create a customer-facing quote document.", "constraints": ["Use only the rates provided. Do not calculate or estimate any rates yourself.", "Include all carriers that returned valid rates.", "Always include the terms and conditions footer.", "Quote expiration is 7 days from generation date unless specified otherwise."], "output_format": {"type": "markdown", "template": "## Freight Quote\\n\\n**Prepared for:** {customer_name}\\n**Date:** {date}\\n**Valid until:** {expiry_date}\\n\\n### Shipment Details\\n| Field | Value |\\n|---|---|\\n| Origin | {origin} |\\n| Destination | {destination} |\\n| Weight | {weight} lbs |\\n| Commodity | {commodity} |\\n\\n### Rate Comparison\\n| Carrier | Transit Time | Base Rate | Surcharges | Total |\\n|---|---|---|---|---|\\n{rate_rows}\\n\\n### Recommended Option\\n{recommendation_with_reasoning}\\n\\n---\\n*Terms: Rates subject to carrier confirmation. Fuel surcharges may vary. Quote valid for 7 days.*"}}})}}
```

**Step 3: Test prompts with edge cases**

Before deploying, test each prompt with inputs designed to break it:

```text
{{workflow_engine(action="test_prompt", workflow="freight_quote_automation", step="parse_request", test_cases=[{"name": "Normal email", "input": "Standard quote request with all fields", "expect": "All fields populated, high confidence"}, {"name": "Vague email", "input": "Hey can you ship something for me?", "expect": "Most fields null, low confidence, useful raw_notes"}, {"name": "Not a quote request", "input": "Please update our billing address to 123 Main St", "expect": "is_quote_request: false"}, {"name": "Multiple shipments in one email", "input": "Need quotes for 3 different shipments...", "expect": "Handles first shipment, notes others in raw_notes"}, {"name": "Foreign language", "input": "Necesito una cotizacion para envio de...", "expect": "Attempts extraction, notes language in raw_notes"}])}}
```

### What Good Looks Like

**A strong prompt:**

- Has all 4 parts (role, context, constraints, output format) explicitly defined
- Includes 2-3 few-shot examples that cover different scenarios
- Specifies exact output structure with field names and types
- Includes constraints about what NOT to do (hallucination guardrails)
- Has been tested with edge cases before deployment

**A weak prompt:**

- Says "you are a helpful assistant" (no specific role)
- Gives no examples (expects the AI to guess the format)
- Says "return the data in a structured format" (not specific enough)
- Has no constraints (allows hallucination and scope creep)
- Was tested only with perfect inputs

**Prompt quality checklist:**

| Criterion | Question | Pass/Fail |
|---|---|---|
| Specificity | Could two different people read this prompt and expect the same output? | |
| Completeness | Does the prompt include every piece of information the AI needs? | |
| Constraints | Are there explicit guardrails against hallucination and scope creep? | |
| Format | Is the output format specified precisely enough to parse programmatically? | |
| Examples | Are there 2-3 examples covering normal and edge cases? | |
| Testability | Can you write a test that checks if the output is correct? | |

**Evaluation Methods:**

| Method | When to Use | How It Works |
|---|---|---|
| **Human review** | During development and for high-stakes outputs | Expert reviews a sample of AI outputs and scores quality |
| **Automated metrics** | After deployment for ongoing monitoring | Check output against expected schema, measure confidence scores, flag anomalies |
| **A/B testing** | When optimizing an existing prompt | Run two prompt versions on the same inputs, compare quality metrics |

### Practice Exercise

**Scenario:** Write a system prompt for the tenant maintenance request classifier from the workflow design lesson.

The AI needs to:

- Read a tenant's maintenance request (email or text message)
- Classify it as Emergency, Urgent, or Routine
- Extract the issue type (plumbing, electrical, HVAC, appliance, structural, other)
- Determine if the tenant needs to be contacted for more information

**Task:**

1. Write the full system prompt with role, context, constraints, and output format
2. Include 3 few-shot examples (one emergency, one urgent, one routine)
3. Write 3 edge case test scenarios

**Self-check questions:**

- Does your prompt define what constitutes an "emergency" explicitly? (Do not assume the AI knows your definition. List specific conditions: water leak, gas smell, no heat below 40F, security breach, etc.)
- Does your output format include a confidence score? (It must — your workflow uses confidence thresholds for routing)
- Does your prompt tell the AI what to do with ambiguous requests? (It should default to Urgent, not Routine — the cost of under-classifying an emergency is much higher than over-classifying a routine request)
- Do your few-shot examples include the reasoning, not just the classification? (This improves consistency — the AI learns the decision pattern, not just the labels)
