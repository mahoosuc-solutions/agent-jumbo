# Module 17: Integration & Scaling

> **Learning Path:** Workflow & Automation Engineer
> **Audience:** Technical operators building automations
> **Prerequisites:** Modules 15-16 (Workflow Engine Deep Dive, Scheduling & Automation)

---

## Lesson: Telegram Integration Patterns

### Why This Matters

Telegram is the primary operator interface for Agent Jumbo. It is where you receive briefings, approve messages, monitor workflows, and issue commands. A poorly integrated Telegram setup means:

- **Missed notifications** — Messages are formatted badly, too long, or lost in noise
- **Slow response loops** — The operator cannot quickly approve, skip, or command from the chat
- **State management failures** — The bot loses track of which approval request maps to which workflow, leading to wrong actions
- **No command structure** — The operator types free-form text and hopes the bot understands

Telegram is not just a notification channel. It is a bidirectional control interface. Treating it as a simple message pipe leaves most of its value on the table.

**What good Telegram integration enables:**

| Capability | Without Integration | With Integration |
|---|---|---|
| Approval flow | Email chain, minutes to respond | Inline keyboard, tap to approve in 2 seconds |
| Status checks | Log into dashboard, navigate to workflow | `/status` command, instant response |
| Error alerts | Email that gets buried | Formatted alert with one-tap action buttons |
| Batch operations | Review each item in a separate tool | Inline keyboards with "Approve All" option |
| On-the-go control | Must be at a computer | Full control from phone while walking the dog |

### How to Think About It

**Webhook Architecture**

Telegram communicates with your bot via webhooks. When a user sends a message or taps a button, Telegram sends an HTTP POST to your webhook URL.

```text
User taps "Approve"
      |
      v
Telegram servers
      |
      v
POST https://your-domain.com/webhook/telegram
      |
      v
Agent Jumbo webhook handler
      |
      v
Route to appropriate workflow execution
      |
      v
Execute approved action
      |
      v
Send confirmation back to Telegram
```

**Webhook setup considerations:**

- Your webhook URL must be HTTPS with a valid certificate
- Telegram retries failed webhook deliveries for up to 24 hours
- If your server is down, messages queue on Telegram's side
- The `secret_token` header lets you verify requests are genuinely from Telegram
- You should respond to webhooks within 10 seconds to avoid timeouts

**Key integration points:**

1. **Webhook registration** — Tell Telegram where to send updates
2. **Message formatting** — Structure messages for mobile readability
3. **Inline keyboards** — Add tap-to-action buttons to messages
4. **Callback queries** — Handle button tap responses
5. **State management** — Track which message maps to which workflow execution
6. **Bot commands** — Register slash commands for direct interaction

**Message Formatting Rules**

Following the daily-ops-rhythm skill:

- Lead with the most actionable item
- Use bullet points, never paragraphs
- Include counts: "3 check-ins, 2 check-outs" not "several check-ins"
- Timestamps in 12h format with timezone: "2:30 PM ET"
- Currency with dollar sign and two decimals: "$1,234.56"
- Keep total message under 30 lines (operator scans on mobile)

**Icons by message category (from daily-ops-rhythm):**

| Category | Icon | Use For |
|---|---|---|
| Property ops | house | Check-ins, check-outs, cleaning |
| Calendar | calendar | Appointments, deadlines |
| Finance | chart | Revenue, expenses, metrics |
| Client/project | clipboard | Pipeline, proposals, follow-ups |
| Alert/urgent | warning | Errors, failures, time-sensitive |
| Success/complete | checkmark | Completed tasks, confirmations |
| BizDev/pipeline | handshake | New leads, deals, partnerships |

**Inline Keyboard Patterns**

```text
Simple approval:
+----------+--------+
|  Approve |  Skip  |
+----------+--------+

Approval with edit:
+----------+--------+--------+
|  Approve |  Edit  |  Skip  |
+----------+--------+--------+

Batch operations:
+--------------+------------+
|  Approve All |  Skip All  |
+--------------+------------+
| Review #1    | Review #2  |
+--------------+------------+

Multi-step decision:
+----------+--------+-----------+
|  Urgent  | Normal | Defer     |
+----------+--------+-----------+

Confirmation with details:
+----------+--------+
|  Confirm | Cancel |
+----------+--------+
| View Details      |
+-------------------+
```

**State Management Model**

Telegram conversations are stateful. When the bot sends an approval request, it must remember which workflow execution that message belongs to. When the operator responds, the bot must route the response to the correct execution.

```text
State Store:
  chat_id: "operator-123"
  pending_interactions:
    msg_12345:
      type: "approval"
      execution_id: "exec-a1b2c3"
      workflow: "guest-message-approval"
      stage: "await_response"
      created_at: "2026-03-20T07:15:00Z"
      timeout_at: "2026-03-20T09:15:00Z"
    msg_12346:
      type: "edit_prompt"
      execution_id: "exec-a1b2c3"
      original_draft: "Hi Sarah..."
      awaiting_text: true
```

When the operator sends a text message, the handler checks: is there a pending `edit_prompt` with `awaiting_text: true`? If yes, treat the text as edit instructions. If no, treat it as a new command.

### Step-by-Step Approach

**Step 1: Set up the Telegram webhook**

```text
{{telegram_bot(action="set_webhook", url="https://your-tunnel.example.com/webhook/telegram", secret_token="wh-secret-abc123", allowed_updates=["message", "callback_query", "my_chat_member"])}}  # pragma: allowlist secret
```

The `secret_token` is included in every webhook request header so your handler can verify it came from Telegram. The `allowed_updates` filter ensures you only receive relevant event types, reducing webhook traffic.

**Step 2: Register bot commands**

```text
{{telegram_bot(action="set_commands", commands=[{"command": "status", "description": "Show current workflow status"}, {"command": "pending", "description": "List pending approvals"}, {"command": "schedule", "description": "Show today's scheduled tasks"}, {"command": "pause", "description": "Pause a scheduled job"}, {"command": "resume", "description": "Resume a paused job"}, {"command": "health", "description": "System health check"}])}}
```

Registered commands appear in Telegram's command menu when the operator types `/`. This provides discoverability without memorization.

**Step 3: Send a formatted digest message**

```text
{{telegram_bot(action="send", chat_id="operator-chat-123", text="MORNING BRIEFING — Mar 20, 2026\n\nToday's Operations:\n- 2 check-ins: Sarah Chen (3 PM), Mike Rodriguez (4 PM)\n- 1 check-out: Julia Walters (11 AM)\n- Cleaning: Lakeside Retreat at 11:30 AM\n\nRevenue:\n- Yesterday: $847.00\n- MTD: $12,453.00\n- Occupancy: 78%\n\nAction Required:\n- Pre-arrival message for Sarah Chen pending approval", parse_mode="Markdown")}}
```

**Step 4: Send a message with inline keyboard for approval**

```text
{{telegram_bot(action="send", chat_id="operator-chat-123", text="[APPROVE] Pre-arrival message for Sarah Chen:\n\nHi Sarah! We're thrilled to welcome you to Lakeside Retreat tomorrow. Check-in is at 3 PM — the lockbox code will be sent at noon. The weather looks beautiful, perfect for the deck!\n\nAnything you need before arrival, just reply here.", reply_markup={"inline_keyboard": [[{"text": "Send", "callback_data": "approve:exec-a1b2c3:send"}, {"text": "Edit", "callback_data": "approve:exec-a1b2c3:edit"}, {"text": "Skip", "callback_data": "approve:exec-a1b2c3:skip"}]]})}}
```

The `callback_data` field encodes three pieces of information: the action type (`approve`), the execution ID (`exec-a1b2c3`), and the decision (`send`/`edit`/`skip`). This allows the handler to route the response without looking up state.

**Step 5: Handle callback queries (button taps)**

```text
{{telegram_bot(action="handle_callback", callback_data="approve:exec-a1b2c3:send", handler={"parse": {"pattern": "approve:{execution_id}:{action}"}, "on_send": {"workflow_action": "resume_execution", "execution_id": "{execution_id}", "response": "approved"}, "on_skip": {"workflow_action": "resume_execution", "execution_id": "{execution_id}", "response": "skipped"}, "on_edit": {"workflow_action": "prompt_for_edits", "execution_id": "{execution_id}"}, "acknowledge": {"text": "Message approved and sending...", "show_alert": false}})}}
```

Always acknowledge callback queries immediately. Telegram shows a loading spinner until you respond, and the user sees "an error occurred" after 30 seconds without acknowledgment.

**Step 6: Manage conversation state**

Track which Telegram message maps to which workflow execution:

```text
{{telegram_bot(action="set_state", chat_id="operator-chat-123", state={"awaiting_edit_for": "exec-a1b2c3", "edit_stage": "pre_arrival_message", "original_message_id": 12345, "context": {"guest_name": "Sarah Chen", "property": "Lakeside Retreat"}})}}
```

When the operator's next text message arrives, the state tells the handler to treat it as edit instructions for the pending approval, not as a new command.

**Step 7: Update messages after action is taken**

After the operator approves, update the original message to reflect the decision:

```text
{{telegram_bot(action="edit_message", chat_id="operator-chat-123", message_id=12345, text="[SENT] Pre-arrival message for Sarah Chen\n\nDelivered at 7:23 AM ET", reply_markup=null)}}
```

Removing the inline keyboard and updating the text prevents accidental double-taps and provides a clear audit trail in the chat history.

### Practice Exercise

**Scenario:** Build the complete Telegram integration for a property turnover workflow. The integration should:

1. Send a notification when checkout is detected
2. Send a cleaning dispatch with inline keyboard (Urgent/Normal)
3. Wait for cleaning team confirmation (inline keyboard: Done/Issue)
4. If there is a next guest, send pre-arrival message for approval (Send/Edit/Skip)
5. Send a completion summary

**Task:** Create the message templates and keyboard configurations for each step.

```text
{{telegram_bot(action="create_message_template", name="checkout-detected", template="CHECKOUT DETECTED\n\nProperty: {{property_name}}\nGuest: {{guest_name}}\nTime: {{checkout_time}}\nNext booking: {{next_booking_summary}}\n\nCleaning dispatch will follow.", keyboard=null)}}
```

```text
{{telegram_bot(action="create_message_template", name="cleaning-dispatch", template="CLEANING DISPATCH\n\nProperty: {{property_name}}\nNext check-in: {{next_checkin_time}}\nTurnover window: {{hours_available}} hours\nChecklist: {{checklist_summary}}\n\nSet priority:", keyboard={"inline_keyboard": [[{"text": "URGENT", "callback_data": "cleaning:{{execution_id}}:urgent"}, {"text": "Normal", "callback_data": "cleaning:{{execution_id}}:normal"}]]})}}
```

```text
{{telegram_bot(action="create_message_template", name="cleaning-confirmation", template="CLEANING STATUS — {{property_name}}\n\nAssigned: {{cleaner_name}}\nPriority: {{priority}}\nStarted: {{start_time}}\n\nMark status:", keyboard={"inline_keyboard": [[{"text": "Done", "callback_data": "clean_done:{{execution_id}}"}, {"text": "Issue Found", "callback_data": "clean_issue:{{execution_id}}"}]]})}}
```

```text
{{telegram_bot(action="create_message_template", name="turnover-complete", template="TURNOVER COMPLETE\n\nProperty: {{property_name}}\nCleaning: Done at {{completion_time}}\nNext guest: {{next_guest_name}} at {{next_checkin_time}}\nPre-arrival message: {{message_status}}\n\nAll clear for next guest.", keyboard=null)}}
```

**Self-check:** What happens when the operator taps "Issue Found"? Your system should prompt for a description, log the issue, and decide whether the property is still ready for the next guest. Design the state machine for this interaction flow. Does your state management handle the case where the operator taps a button on a stale message from yesterday?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Messages longer than 30 lines | Trying to include everything | Summarize in the message, link to details; operator is on mobile |
| No callback_data mapping to executions | Treating Telegram as one-way | Include execution_id in every callback_data so responses route correctly |
| Losing state between messages | Not using conversation state | Track pending interactions in state; clear state when resolved |
| No error handling on webhook failures | Trusting network reliability | Retry webhook sends once after 60s; log failures per the approval-workflow skill |
| Not updating messages after action | Stale approval buttons remain tappable | Edit the message to show the outcome and remove the keyboard |

---

## Lesson: External Service Integration

### Why This Matters

Workflows become powerful when they connect to external services: PMS systems, payment processors, email providers, calendar APIs, weather services, and more. But each external integration is a potential point of failure, security risk, and maintenance burden.

Without structured integration practices:

- **API keys leak** into logs and error messages
- **Rate limits trigger** because you did not track your request budget
- **Breaking changes** in external APIs silently corrupt your data
- **Authentication expires** and workflows fail at 3 AM with cryptic errors
- **Data format mismatches** between services cause silent data corruption

Every external service you integrate with is a dependency you must manage. The more integrations, the more surface area for failures.

**The dependency risk matrix:**

| Dependency Count | Risk Level | Mitigation Strategy |
|---|---|---|
| 1-3 services | Manageable | Monitor each individually, manual oversight |
| 4-7 services | Moderate | Automated health checks, circuit breakers needed |
| 8+ services | High | Integration layer mandatory, fallback strategies for each |

### How to Think About It

**Integration Architecture**

Never call external services directly from workflow stages. Use an integration layer that handles authentication, rate limiting, retries, and data transformation:

```text
Workflow Stage
      |
      v
Integration Layer
  ├── Authentication Manager (tokens, keys, refresh)
  ├── Rate Limiter (per-service request budgets)
  ├── Request Builder (construct API calls)
  ├── Response Parser (normalize responses)
  ├── Error Classifier (transient vs permanent)
  └── Cache (avoid redundant calls)
      |
      v
External Service API
```

The integration layer provides a consistent interface to every external service. Your workflow stages never deal with raw HTTP calls, authentication headers, or response parsing. They call the integration layer and receive normalized data.

**Authentication Patterns**

| Pattern | Use Case | Management | Rotation Strategy |
|---|---|---|---|
| API Key | Simple services, server-to-server | Store in secrets manager | Rotate quarterly, alert 14 days before expiry |
| OAuth 2.0 | User-delegated access, Google/Microsoft | Refresh tokens automatically | Monitor refresh failures, re-auth on permanent failure |
| JWT | Service-to-service, short-lived | Generate on demand, cache until expiry | No rotation needed; tokens are ephemeral |
| Webhook Secret | Inbound webhooks (e.g., Telegram) | Verify on every request | Rotate annually, update both sides simultaneously |
| mTLS | High-security service-to-service | Certificate management | Rotate before certificate expiry, typically annually |

**Rate Limiting Strategies**

External services impose rate limits. Exceeding them causes failures and potential bans.

```text
Token Bucket Algorithm:

  Bucket capacity: 100 requests
  Refill rate: 10 requests/second

  [████████████████████░░░░░░░░░░]  80 tokens remaining

  Each request costs 1 token.
  When bucket is empty, requests queue until tokens refill.
```

| Strategy | How It Works | When to Use |
|---|---|---|
| Token bucket | Fixed capacity, steady refill | Most APIs with rate limits |
| Sliding window | Count requests in rolling time window | APIs with "X requests per minute" limits |
| Concurrency limit | Max simultaneous requests | APIs with concurrent connection limits |
| Request queuing | Queue excess requests, drain at allowed rate | Bursty workloads that exceed instantaneous limits |

**Best practice:** Set your rate limiter to 80% of the documented limit. This provides a safety margin for timing imprecision and concurrent requests from other parts of your system.

**Data Transformation**

External services return data in their format. Your workflows need data in your format. The transformation layer handles this mapping.

```text
External Format (PMS API):          Internal Format:
{                                   {
  "reservation_id": "R-123",          "booking_id": "R-123",
  "guest": {                          "guest_name": "Sarah Chen",
    "first": "Sarah",                 "check_in": "2026-03-21",
    "last": "Chen"                    "check_out": "2026-03-24",
  },                                  "property": "lakeside-retreat",
  "arrival": "2026-03-21",            "nights": 3,
  "departure": "2026-03-24",          "total_revenue": 847.00
  "property_code": "LSR",           }
  "total": 847.00
}
```

Transformations serve three purposes:

1. **Normalization** — Consistent field names and formats across all services
2. **Computation** — Derived fields like `nights` calculated from date differences
3. **Isolation** — If the external API changes its format, only the transformation changes; workflows are unaffected

**Integration Health Monitoring**

Every integration should have a health check that runs independently of workflow executions:

```text
Health Check Dashboard:

Service             Status    Latency   Error Rate   Last Check
─────────────────────────────────────────────────────────────────
PMS Hospitable      GREEN     180ms     0.2%         2 min ago
SendGrid Email      GREEN     95ms      0.0%         3 min ago
Google Calendar     YELLOW    2.1s      1.5%         1 min ago
Stripe Payments     GREEN     120ms     0.1%         2 min ago
Weather API         RED       timeout   100%         30 sec ago
```

### Step-by-Step Approach

**Step 1: Register an external service integration**

```text
{{workflow_engine(action="register_integration", name="pms-hospitable", config={"base_url": "https://api.hospitable.com/v1", "auth": {"type": "api_key", "header": "Authorization", "prefix": "Bearer", "secret_ref": "secrets.pms_api_key"}, "rate_limit": {"strategy": "token_bucket", "capacity": 100, "refill_rate": 10, "refill_interval": "1s"}, "timeout": "15s", "retry": {"strategy": "exponential_backoff", "max_retries": 3, "initial_delay": "2s"}, "health_check": {"endpoint": "/health", "interval": "5m", "alert_on_failure": true}})}}  # pragma: allowlist secret
```

**Step 2: Define data transformations**

```text
{{workflow_engine(action="create_transform", name="pms-booking-to-internal", source="pms-hospitable", mapping={"booking_id": "$.reservation_id", "guest_name": "$.guest.first + ' ' + $.guest.last", "check_in": "$.arrival", "check_out": "$.departure", "property": "$.property_code | lookup(property_map)", "nights": "daysBetween($.arrival, $.departure)", "total_revenue": "$.total"})}}
```

**Step 3: Create a workflow stage that uses the integration**

```text
{{workflow_engine(action="create", name="fetch-upcoming-bookings", version=1, stages=[{"name": "call_pms", "type": "integration", "service": "pms-hospitable", "endpoint": "/reservations", "method": "GET", "params": {"check_in_from": "{{today}}", "check_in_to": "{{today_plus_7}}", "status": "confirmed"}, "transform": "pms-booking-to-internal", "cache": {"ttl": "15m", "key": "upcoming_bookings_{{today}}"}}, {"name": "process_bookings", "type": "action", "action": "evaluate_upcoming_bookings"}], transitions=[{"from": "call_pms", "to": "process_bookings", "condition": "always"}])}}
```

The `cache` configuration prevents redundant API calls when multiple workflows need the same data within a short window.

**Step 4: Set up authentication rotation alerts**

```text
{{scheduler(action="create_job", name="api-key-expiry-check", cron="0 9 1 * *", timezone="US/Eastern", task="check_integration_credentials", config={"integrations": ["pms-hospitable", "stripe-payments", "google-calendar"], "alert_days_before_expiry": 14, "notify": "telegram"})}}
```

**Step 5: Monitor integration health**

```text
{{workflow_engine(action="get_integration_metrics", name="pms-hospitable", period="24h", metrics=["request_count", "error_rate", "avg_latency", "p95_latency", "rate_limit_hits", "cache_hit_rate", "auth_refresh_count"])}}
```

**Step 6: Handle API versioning and breaking changes**

```text
{{workflow_engine(action="update_integration", name="pms-hospitable", config={"api_version": "v2", "version_header": "X-API-Version", "migration_mode": {"enabled": true, "fallback_version": "v1", "log_differences": true, "auto_switch_after": "7d"}})}}
```

Migration mode calls both API versions in parallel, logs differences, and automatically switches to the new version after a confidence period.

### Practice Exercise

**Scenario:** You need to integrate with a new email service (SendGrid) for sending guest communications. The service has:

- API key authentication
- Rate limit: 100 emails/second
- Webhook for delivery status updates
- Different endpoints for single send vs. batch send

**Task:**

1. Register the integration with proper auth, rate limiting, and retry configuration
2. Create data transformations for outbound emails and inbound status webhooks
3. Build a workflow stage that sends an email through the integration layer
4. Set up health monitoring

```text
{{workflow_engine(action="register_integration", name="sendgrid-email", config={"base_url": "https://api.sendgrid.com/v3", "auth": {"type": "api_key", "header": "Authorization", "prefix": "Bearer", "secret_ref": "secrets.sendgrid_api_key"}, "rate_limit": {"strategy": "token_bucket", "capacity": 80, "refill_rate": 80, "refill_interval": "1s"}, "timeout": "10s", "retry": {"strategy": "exponential_backoff", "max_retries": 3, "initial_delay": "1s"}, "webhooks": {"delivery_status": {"path": "/webhook/sendgrid/status", "secret_ref": "secrets.sendgrid_webhook_key", "events": ["delivered", "bounced", "failed", "opened"]}}, "health_check": {"endpoint": "/scopes", "interval": "10m", "alert_on_failure": true}})}}  # pragma: allowlist secret
```

```text
{{workflow_engine(action="create_transform", name="internal-to-sendgrid-email", target="sendgrid-email", mapping={"personalizations[0].to[0].email": "$.recipient_email", "personalizations[0].to[0].name": "$.recipient_name", "from.email": "$.sender_email", "from.name": "$.sender_name", "subject": "$.subject", "content[0].type": "'text/html'", "content[0].value": "$.html_body", "custom_args.execution_id": "$.execution_id", "custom_args.message_type": "$.message_type"})}}
```

```text
{{workflow_engine(action="create_transform", name="sendgrid-status-to-internal", source="sendgrid-email", webhook="delivery_status", mapping={"message_id": "$.sg_message_id", "execution_id": "$.custom_args.execution_id", "status": "$.event", "recipient_email": "$.email", "timestamp": "$.timestamp | toISO8601", "bounce_reason": "$.reason | default(null)"})}}
```

**Self-check:** What happens when SendGrid's delivery webhook reports a bounce? Your system should update the guest record to flag the email as invalid, prevent future sends to that address, and notify the operator. Did you account for this in your integration? Also note: the rate limit capacity is set to 80, not 100. That is the 80% safety margin in action.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Hardcoding API keys in workflow definitions | Quick setup, "I'll fix it later" | Always use secret references; never put keys in code or logs |
| No rate limiting on outbound calls | Not reading the API documentation | Configure rate limits to 80% of the documented limit for safety margin |
| Skipping data transformation | "The formats are close enough" | Always transform; format drift between services causes subtle bugs over time |
| No caching for repeated reads | Not measuring call frequency | Cache reads with appropriate TTL; check cache hit rate monthly |
| Ignoring webhook verification | Trusting inbound requests blindly | Always verify webhook signatures; unverified webhooks are a security hole |

---

## Lesson: Multi-Dashboard Operations

### Why This Matters

As your automation footprint grows, you move from a single dashboard to multiple dashboards covering different operational domains: property operations, client pipelines, financial metrics, system health, and workflow monitoring.

Without a multi-dashboard strategy:

- **Information silos** — The operator checks one dashboard and misses critical information on another
- **Inconsistent data** — The same metric shows different values on different dashboards because they query at different times
- **Alert fragmentation** — Alerts from different dashboards arrive in different channels with different formats
- **No unified view** — The operator cannot get a single-glance overview of overall system health
- **Context switching overhead** — The mental cost of moving between dashboards causes important signals to be missed

Multi-dashboard operations is about creating a coherent information architecture across all your monitoring surfaces. The goal is not more dashboards. It is the right information at the right time in the right place.

**The dashboard proliferation trap:**

| Number of Dashboards | Operator Experience | Recommendation |
|---|---|---|
| 1 | Too much on one screen, slow to load | Split into hierarchy |
| 2-4 | Manageable with clear roles | Sweet spot for most operations |
| 5-8 | Requires executive summary to navigate | Add executive dashboard |
| 9+ | Nobody checks them all | Consolidate; you have too many |

### How to Think About It

**Dashboard Hierarchy**

```text
Executive Dashboard (single screen, key metrics only)
  |
  +-- Operations Dashboard (property-level detail)
  |     +-- Property A status, bookings, cleaning
  |     +-- Property B status, bookings, cleaning
  |
  +-- Workflow Dashboard (automation health)
  |     +-- Active workflows, success rates
  |     +-- Pending approvals, failed executions
  |     +-- Scheduler status, upcoming jobs
  |
  +-- Integration Dashboard (external service health)
  |     +-- PMS API status, latency, error rate
  |     +-- Email service delivery rate
  |     +-- Payment processor status
  |
  +-- Financial Dashboard (revenue and costs)
        +-- Daily/weekly/monthly revenue
        +-- Occupancy rates
        +-- Expense tracking
```

**Dashboard Design Principles**

| Principle | Description | Example |
|---|---|---|
| Glanceability | Key status visible in under 3 seconds | Red/yellow/green indicators at the top |
| Drill-down | Summary leads to detail on demand | Click a red indicator to see which workflow failed |
| Consistency | Same metric looks the same everywhere | Revenue always formatted as "$X,XXX.XX" |
| Freshness | Data age is visible | "Updated 2 minutes ago" on every dashboard |
| Actionability | Every alert has a clear next step | "Workflow failed" links to the replay button |
| Mobile-first | Operators check on phones | Design for portrait orientation, tap targets |

**The Information Flow Model**

Data flows from sources through processing to dashboards. Understanding this flow prevents stale data and inconsistencies.

```text
Data Sources          Processing             Dashboards
─────────────        ─────────────          ─────────────
PMS API        ──>   Transform     ──>      Operations
Stripe API     ──>   Aggregate     ──>      Financial
Workflow Engine──>   Cache (5min)  ──>      Workflow
Email Service  ──>   Alert Rules   ──>      Integration
                          |
                     Telegram Digest  ──>   Operator Phone
```

**Cross-Dashboard Workflows**

Some workflows span multiple dashboards. A new booking event might:

1. Appear on the Operations Dashboard (new booking card)
2. Trigger a workflow visible on the Workflow Dashboard (pre-arrival pipeline)
3. Update metrics on the Financial Dashboard (revenue forecast)
4. Require an integration call visible on the Integration Dashboard (PMS sync)

The operator should not need to check four dashboards to understand this event. Cross-dashboard linking ensures context flows between views.

**Alert Consolidation**

Multiple dashboards generating independent alerts is a recipe for notification fatigue. Unified alerting consolidates, deduplicates, and prioritizes:

```text
Without Unified Alerting:
  - Operations: "Property turnover needed"
  - Workflow: "Turnover workflow triggered"
  - Integration: "PMS API called successfully"
  = 3 messages for 1 event

With Unified Alerting:
  - "Turnover started for Lakeside Retreat. Cleaning dispatched, ETA 2h."
  = 1 message with all relevant context
```

### Step-by-Step Approach

**Step 1: Define your dashboard topology**

```text
{{workflow_engine(action="create_dashboard_config", name="operations-hub", dashboards=[{"name": "executive-summary", "type": "overview", "refresh_interval": "5m", "widgets": ["system_health_indicator", "todays_bookings_count", "pending_approvals_count", "revenue_today", "active_workflows_count"]}, {"name": "property-ops", "type": "detail", "refresh_interval": "2m", "widgets": ["property_status_grid", "todays_checkins", "todays_checkouts", "cleaning_status", "maintenance_alerts"]}, {"name": "workflow-monitor", "type": "detail", "refresh_interval": "1m", "widgets": ["active_executions", "failed_executions_24h", "pending_approvals", "scheduler_status", "circuit_breaker_status"]}, {"name": "integration-health", "type": "detail", "refresh_interval": "1m", "widgets": ["service_status_grid", "api_latency_chart", "error_rate_chart", "rate_limit_usage"]}])}}
```

**Step 2: Create cross-dashboard links**

```text
{{workflow_engine(action="create_dashboard_links", links=[{"source": {"dashboard": "executive-summary", "widget": "pending_approvals_count"}, "target": {"dashboard": "workflow-monitor", "widget": "pending_approvals"}, "type": "drill_down"}, {"source": {"dashboard": "property-ops", "widget": "cleaning_status"}, "target": {"dashboard": "workflow-monitor", "filter": {"workflow": "property-turnover"}}, "type": "context_link"}, {"source": {"dashboard": "workflow-monitor", "widget": "failed_executions_24h"}, "target": {"dashboard": "integration-health", "filter": {"status": "error"}}, "type": "root_cause"}, {"source": {"dashboard": "executive-summary", "widget": "revenue_today"}, "target": {"dashboard": "financial", "widget": "revenue_detail"}, "type": "drill_down"}])}}
```

**Step 3: Set up unified alerting across dashboards**

```text
{{workflow_engine(action="create_unified_alerts", config={"channels": [{"name": "telegram-critical", "type": "telegram", "chat_id": "operator-chat-123", "severity": ["critical"]}, {"name": "telegram-standard", "type": "telegram", "chat_id": "operator-chat-123", "severity": ["warning", "info"]}], "deduplication": {"window": "15m", "group_by": ["source_service", "error_type"]}, "quiet_hours": {"start": "22:00", "end": "06:00", "timezone": "US/Eastern", "override_for": ["critical"]}, "suppression": {"repeated_alerts": {"threshold": 3, "window": "1h", "action": "summarize"}}, "alert_format": {"title": "[{severity}] {dashboard}: {summary}", "body": "{details}\n\nAction: {recommended_action}\nDashboard: {dashboard_url}"}})}}
```

**Step 4: Create a cross-dashboard workflow status view**

```text
{{workflow_engine(action="create_unified_view", name="booking-lifecycle", entity="booking", stages_across_dashboards=[{"stage": "New Booking Detected", "dashboard": "property-ops", "metric": "new_bookings_today"}, {"stage": "Pre-arrival Pipeline", "dashboard": "workflow-monitor", "metric": "pre_arrival_active"}, {"stage": "Message Approved", "dashboard": "workflow-monitor", "metric": "approvals_today"}, {"stage": "Guest Communication Sent", "dashboard": "integration-health", "metric": "emails_sent_today"}, {"stage": "Revenue Recorded", "dashboard": "financial", "metric": "revenue_today"}])}}
```

This view lets the operator trace a booking across all dashboards to see where things stand at a glance.

**Step 5: Build a Telegram digest that summarizes all dashboards**

Instead of checking each dashboard, the operator gets a unified summary:

```text
{{telegram_bot(action="send", chat_id="operator-chat-123", text="SYSTEM OVERVIEW — Mar 20, 2026 5:00 PM ET\n\nOperations: 2 check-ins complete, 1 pending\nWorkflows: 12 runs today, 11 success, 1 pending approval\nIntegrations: All services healthy\nRevenue: $847.00 today, $12,453.00 MTD\n\nAction needed:\n- 1 pending approval (pre-arrival for Chen)\n\nCommands: /ops /workflows /integrations /finance", parse_mode="Markdown")}}
```

The slash commands at the bottom let the operator drill into any area directly from Telegram without opening a browser.

**Step 6: Configure data consistency across dashboards**

Ensure all dashboards show the same data by using shared data sources:

```text
{{workflow_engine(action="create_shared_data_source", name="daily-metrics-cache", config={"refresh_interval": "5m", "sources": [{"name": "bookings", "query": "SELECT * FROM bookings WHERE date = today()", "cache_key": "bookings_today"}, {"name": "revenue", "query": "SELECT SUM(amount) FROM transactions WHERE date = today()", "cache_key": "revenue_today"}, {"name": "workflow_stats", "query": "SELECT status, COUNT(*) FROM executions WHERE date = today() GROUP BY status", "cache_key": "workflow_stats_today"}], "consumers": ["executive-summary", "property-ops", "workflow-monitor", "financial"]})}}
```

All dashboards read from the same cache, so the numbers are always consistent regardless of when each dashboard refreshes.

### Practice Exercise

**Scenario:** You manage 5 properties, 8 recurring workflows, 3 external integrations, and a client pipeline. The operator currently checks 3 different dashboards and Telegram throughout the day. They report feeling overwhelmed and sometimes miss important items.

**Task:**

1. Design a dashboard hierarchy appropriate for this operation
2. Create an executive summary dashboard that fits on one mobile screen
3. Set up cross-dashboard links for the most common drill-down paths
4. Configure unified alerting that prevents notification fatigue
5. Build a morning Telegram digest that summarizes all dashboards

```text
{{workflow_engine(action="create_dashboard_config", name="5-property-ops", dashboards=[{"name": "mobile-executive", "type": "overview", "refresh_interval": "5m", "layout": "mobile_single_screen", "widgets": [{"name": "health_traffic_light", "type": "indicator", "sources": ["property-ops", "workflow-monitor", "integration-health"]}, {"name": "todays_numbers", "type": "stat_row", "metrics": ["check_ins", "check_outs", "pending_approvals", "revenue_today"]}, {"name": "needs_attention", "type": "list", "max_items": 5, "filter": "action_required", "sources": ["all_dashboards"]}, {"name": "property_grid", "type": "status_grid", "items": ["property_1", "property_2", "property_3", "property_4", "property_5"], "status_colors": {"occupied": "blue", "vacant_clean": "green", "vacant_dirty": "yellow", "maintenance": "red"}}]}])}}
```

Then configure the morning digest that replaces manual dashboard checking:

```text
{{scheduler(action="create_job", name="morning-dashboard-digest", cron="0 7 * * *", timezone="US/Eastern", task="workflow:compile-cross-dashboard-digest", config={"dashboards": ["property-ops", "workflow-monitor", "integration-health", "financial"], "format": "telegram_digest", "include_action_items": true})}}
```

**Self-check:** Can the operator understand the state of the entire operation from the executive summary alone? If they need to drill down, can they do so in one tap? If any metric on the executive summary is ambiguous or requires context from another dashboard to interpret, your hierarchy needs adjustment. Count the total number of widgets across all dashboards. If it exceeds 25, you are likely showing too much.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Too many widgets on one dashboard | Trying to show everything at once | Limit executive view to 5-7 widgets; use drill-down for detail |
| Dashboards with no cross-links | Building dashboards independently | Plan the dashboard hierarchy first; links are part of the design, not an afterthought |
| Alerts from each dashboard separately | Each dashboard configured in isolation | Use unified alerting with deduplication and quiet hours |
| No "freshness" indicator on data | Assuming data is always current | Show "last updated" on every widget; stale data is worse than no data |
| Same metric calculated differently on different dashboards | Using different queries for the same number | Use shared data sources; one query, one cache, many consumers |
