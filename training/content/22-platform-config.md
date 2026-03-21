# Module 22: Platform Configuration

> **Learning Path:** Platform Administrator
> **Audience:** Sysadmins/DevOps operators managing the platform
> **Prerequisites:** None

---

## Lesson: Platform Architecture Overview

### Why This Matters

Before you can configure, troubleshoot, or optimize the platform, you need to understand how it is built. Operators who skip the architecture overview make predictable mistakes:

- **Editing the wrong config file** — the platform has multiple configuration layers, and changes in the wrong one get silently overridden
- **Breaking data flow** — modifying a component without understanding what depends on it causes cascading failures
- **Debugging blind** — without a mental model of the system, every error message is a mystery that takes 10x longer to resolve
- **Unsafe upgrades** — upgrading one component without understanding its dependencies brings down adjacent services

**The cost of not knowing your architecture:**

| Failure Mode | Time Lost | Risk Level |
|---|---|---|
| Editing overridden config file | 2-4 hours debugging "why my change didn't work" | Low — no damage, just wasted time |
| Breaking a data pipeline | 4-8 hours restoring service + data reconciliation | High — possible data loss |
| Misconfiguring authentication | 1-2 hours lockout + potential security exposure | Critical — security incident |
| Upgrading incompatible components | 8-16 hours rollback and recovery | High — extended downtime |

Understanding the architecture is not optional knowledge for a platform administrator. It is the foundation every other skill builds on.

### How to Think About It

**System Component Map**

The platform is composed of layered components. Each layer depends on the one below it.

```text
┌─────────────────────────────────────────────────┐
│                   Web UI Layer                  │
│         (Dashboards, Settings, Controls)        │
├─────────────────────────────────────────────────┤
│                  API Layer                      │
│      (REST endpoints, WebSocket handlers)       │
├─────────────────────────────────────────────────┤
│               Application Core                  │
│   (Workflow engine, Skill executor, Scheduler)  │
├─────────────────────────────────────────────────┤
│              Integration Layer                   │
│  (MCP servers, External APIs, Tool connectors)  │
├─────────────────────────────────────────────────┤
│               Data Layer                         │
│    (SQLite/DB, File storage, Configuration)     │
└─────────────────────────────────────────────────┘
```

**Directory Structure**

Every operator should know these directories by heart:

```text
project-root/
  ├── config/              # Global configuration files
  ├── data/                # Runtime data, state files, databases
  ├── knowledge/           # Knowledge base content and indexes
  │   └── custom/          # Custom knowledge entries and ADRs
  ├── scripts/             # Utility and bootstrap scripts
  ├── skills/              # Registered skill definitions
  │   └── registry.json    # Master skill registry
  ├── tests/               # Test suites (unit, integration, e2e)
  ├── training/            # Training content and enrollment data
  ├── webui/               # Frontend dashboards and components
  │   ├── components/      # Reusable UI components
  │   └── dashboards/      # Dashboard views
  ├── .env                 # Environment variables (secrets, keys)
  ├── .env.example         # Template for environment variables
  └── requirements.txt     # Python dependencies
```

**Data Flow Model**

Understanding how data moves through the system prevents most configuration mistakes:

```text
User Request --> Web UI --> API Layer --> Workflow Engine
                                              |
                                    ┌─────────┴──────────┐
                                    │                      │
                              Skill Executor        Scheduler
                                    │                      │
                              Tool Connector          Cron Jobs
                                    │                      │
                              External APIs          Data Layer
                                    │                      │
                              Response ─────────> Web UI Update
```

**Configuration Hierarchy**

The platform uses a layered configuration model. Understanding precedence prevents the "my change did nothing" problem:

| Priority | Source | Location | Purpose |
|---|---|---|---|
| 1 (highest) | Environment variables | `.env` file or OS env | Secrets, deployment-specific overrides |
| 2 | Runtime config | `data/` state files | Dynamic settings changed via UI or API |
| 3 | Skill config | `skills/registry.json` | Skill-specific parameters and tool bindings |
| 4 (lowest) | Default config | Hardcoded in application | Fallback values when nothing else is set |

**Database Schema Essentials**

The data layer stores operational state. Key tables and their relationships:

```text
workflows        ──┐
  id, name,        │
  status,          ├──> workflow_steps
  created_at       │      workflow_id, step_order,
                   │      skill_id, parameters
                   │
skills           ──┘
  id, name,        ──> skill_tools
  version,              skill_id, tool_name,
  category              tool_config

instruments
  id, name, type,
  config, status
```

### Step-by-Step Approach

**Step 1: Verify current platform status**

Before making any changes, always check what is running:

```text
{{platform_config(action="get_status")}}
```

This returns the running state of all components, active connections, and any error conditions.

**Step 2: Review the configuration hierarchy**

Check which configuration sources are active and what values they provide:

```text
{{platform_config(action="get_config", scope="all")}}
```

**Step 3: Map your component dependencies**

Before modifying any component, understand what depends on it:

```text
{{platform_config(action="get_dependencies", component="workflow_engine")}}
```

**Step 4: Inspect the data layer**

Verify database integrity and current schema version:

```text
{{platform_config(action="health_check", target="database")}}
```

**Step 5: Document your baseline**

Before any change, record the current state so you can compare after:

```text
{{platform_config(action="snapshot", name="pre-change-baseline", include=["config", "status", "health"])}}
```

### Practice Exercise

**Scenario:** You are a new platform administrator taking over from a colleague who left no documentation. Your first task is to understand the current state of the system.

**Task:** Perform a full platform inventory.

1. Get the platform status and list all running components:

```text
{{platform_config(action="get_status")}}
```

1. List all registered skills and their current state:

```text
{{platform_config(action="list_instruments")}}
```

1. Check the health of every subsystem:

```text
{{platform_config(action="health_check")}}
```

1. Export the current configuration for documentation:

```text
{{platform_config(action="get_config", scope="all", format="export")}}
```

**Self-check:** After completing the inventory, you should be able to answer these questions without looking at the system:

- How many skills are registered and how many are active?
- What external integrations are configured?
- Are there any components in an error or degraded state?
- What is the database schema version?

If you cannot answer all four, your inventory is incomplete.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Editing `.env` without restarting services | Assuming env vars are read dynamically | Always restart affected services after `.env` changes |
| Modifying `registry.json` by hand while platform is running | Impatience with the admin UI | Use the API or UI to modify skills; manual edits require restart |
| Ignoring the config hierarchy | Not knowing overrides exist | Always check higher-priority sources when a config "isn't working" |
| No baseline before changes | Urgency to fix a problem | Take a snapshot before every change, even small ones |
| Assuming directory structure matches documentation | Docs may be outdated | Verify paths on the actual system before writing scripts |

---

## Lesson: Dashboard Configuration

### Why This Matters

Dashboards are how operators and users see the platform's state at a glance. A well-configured dashboard prevents problems by surfacing issues before they become incidents. A poorly configured dashboard is worse than no dashboard at all, because it creates false confidence.

**What bad dashboards cost you:**

- **Alert fatigue** — too many widgets showing non-actionable data trains operators to ignore the dashboard entirely
- **Blind spots** — missing widgets mean critical failures go unnoticed for hours
- **Slow diagnosis** — poorly organized layouts force operators to hunt for information during incidents
- **Permission confusion** — wrong visibility settings expose sensitive data or hide necessary controls from operators who need them

**The dashboard effectiveness spectrum:**

| Level | Description | Operator Experience |
|---|---|---|
| Absent | No dashboards configured | Flying blind, learn about problems from users |
| Cluttered | Every metric shown, no hierarchy | Information overload, nothing stands out |
| Basic | Key metrics shown but no alerting | Can see current state but miss trends |
| Functional | Organized layout with alerts and drill-down | Can spot and diagnose issues efficiently |
| Excellent | Role-based views with predictive indicators | Prevents problems before they occur |

Your goal is to reach "Functional" for every operator role, and "Excellent" for production-critical views.

### How to Think About It

**Dashboard Design Principles**

A good dashboard answers three questions in order:

```text
1. Is everything OK right now?        → Status indicators (green/yellow/red)
1. What needs my attention?           → Alert panels and anomaly highlights
1. What are the details?              → Drill-down views and trend charts
```

**Widget Types and When to Use Them**

| Widget Type | Best For | Example |
|---|---|---|
| Status indicator | Binary OK/not-OK states | Service health, connection status |
| Metric card | Single important number | Active workflows, error count today |
| Time series chart | Trends over time | Request volume, response latency |
| Table | Lists of items needing review | Failed jobs, pending approvals |
| Log stream | Real-time event monitoring | Incoming requests, error messages |
| Progress bar | Completion tracking | Workflow progress, migration status |

**Layout Best Practices**

```text
┌──────────────────────────────────────────────────────┐
│  TOP ROW: Critical status indicators (3-5 max)       │
│  [Service Health] [Active Errors] [Queue Depth]      │
├──────────────────────────────────────────────────────┤
│  MIDDLE: Action-required items                       │
│  ┌─────────────────────┐ ┌─────────────────────────┐ │
│  │  Alert Panel         │ │  Failed Jobs Table      │ │
│  └─────────────────────┘ └─────────────────────────┘ │
├──────────────────────────────────────────────────────┤
│  BOTTOM: Trend data and drill-down                   │
│  ┌─────────────────────┐ ┌─────────────────────────┐ │
│  │  Request Volume      │ │  Latency Trends         │ │
│  │  (24hr chart)        │ │  (24hr chart)           │ │
│  └─────────────────────┘ └─────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

**Permission Model for Dashboards**

| Role | Can View | Can Edit | Can Create | Can Delete |
|---|---|---|---|---|
| Viewer | Assigned dashboards only | No | No | No |
| Operator | All operational dashboards | Own dashboards | Yes | Own dashboards |
| Admin | All dashboards | All dashboards | Yes | All dashboards |

### Step-by-Step Approach

**Step 1: Plan your dashboard before building it**

Define the purpose, audience, and key metrics before adding any widgets:

- Who will use this dashboard? (role and skill level)
- What decisions will they make based on it?
- What are the 3-5 most critical things they need to see?

**Step 2: Create a new dashboard**

```text
{{platform_config(action="create_dashboard", name="Platform Operations", layout="grid", description="Primary operational view for platform administrators", role="admin")}}
```

**Step 3: Add status indicators for critical components**

```text
{{platform_config(action="add_widget", dashboard="Platform Operations", widget_type="status_indicator", config={"title": "Core Services", "sources": ["api_server", "workflow_engine", "scheduler", "database"], "position": {"row": 1, "col": 1, "width": 2}})}}
```

**Step 4: Add an alert panel for items needing attention**

```text
{{platform_config(action="add_widget", dashboard="Platform Operations", widget_type="table", config={"title": "Active Alerts", "source": "alert_stream", "columns": ["severity", "component", "message", "timestamp"], "filter": {"status": "active"}, "sort": "severity_desc", "position": {"row": 2, "col": 1, "width": 4}})}}
```

**Step 5: Add trend charts for capacity planning**

```text
{{platform_config(action="add_widget", dashboard="Platform Operations", widget_type="time_series", config={"title": "Request Volume (24h)", "source": "request_metrics", "timeframe": "24h", "aggregation": "5m", "position": {"row": 3, "col": 1, "width": 2}})}}
```

**Step 6: Set permissions**

```text
{{platform_config(action="set_dashboard_permissions", dashboard="Platform Operations", permissions={"admin": "edit", "operator": "view", "viewer": "none"})}}
```

### Practice Exercise

**Scenario:** Your team has asked for a "Workflow Health" dashboard that shows the status of all active workflows, highlights failures, and tracks throughput trends.

**Task:** Design and build the dashboard.

1. Create the dashboard:

```text
{{platform_config(action="create_dashboard", name="Workflow Health", layout="grid", description="Monitors active workflows, failures, and throughput", role="operator")}}
```

1. Add a metric card showing active workflow count:

```text
{{platform_config(action="add_widget", dashboard="Workflow Health", widget_type="metric_card", config={"title": "Active Workflows", "source": "workflow_count", "filter": {"status": "running"}, "position": {"row": 1, "col": 1, "width": 1}})}}
```

1. Add a table of failed workflows:

```text
{{platform_config(action="add_widget", dashboard="Workflow Health", widget_type="table", config={"title": "Failed Workflows (Last 24h)", "source": "workflow_list", "columns": ["name", "failed_step", "error_message", "failed_at"], "filter": {"status": "failed", "timeframe": "24h"}, "sort": "failed_at_desc", "position": {"row": 2, "col": 1, "width": 4}})}}
```

1. Add a throughput chart:

```text
{{platform_config(action="add_widget", dashboard="Workflow Health", widget_type="time_series", config={"title": "Workflow Completions (7d)", "source": "workflow_completions", "timeframe": "7d", "aggregation": "1h", "position": {"row": 3, "col": 1, "width": 2}})}}
```

**Self-check:** Open your new dashboard and verify: Can you tell within 5 seconds if workflows are healthy? Can you find the most recent failure in under 10 seconds? Can you spot a throughput trend over the last week? If any answer is no, your dashboard needs revision.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Too many widgets on one dashboard | Trying to show everything at once | Limit to 8-12 widgets; create separate dashboards for different concerns |
| No status indicators in the top row | Starting with detail instead of summary | Always lead with the 3-5 most critical health signals |
| Using charts where tables are better | Defaulting to visual appeal | Use tables for lists of actionable items; charts for trends |
| Same dashboard for all roles | Not considering different user needs | Create role-specific views with appropriate detail levels |
| Hardcoded time ranges | Setting "last 24h" and never adjusting | Use relative time ranges and allow user-adjustable windows |

---

## Lesson: Instrument and Tool Management

### Why This Matters

Instruments and tools are the platform's connection to the outside world and to its own capabilities. Every workflow step, every automation, every integration depends on a properly registered and configured tool. When tool management is sloppy:

- **Workflows break silently** — a misconfigured tool returns empty results instead of errors, and nobody notices until the damage is done
- **Security gaps appear** — orphaned tool registrations with old credentials remain active long after they should have been removed
- **Debugging becomes impossible** — without clear tool versioning and lifecycle tracking, you cannot determine when a behavior change was introduced
- **Scaling hits walls** — unmanaged tool connections exhaust rate limits and connection pools

**Tool management is infrastructure management.** Every tool is a dependency, and unmanaged dependencies are the number one cause of production incidents.

**The tool lifecycle:**

```text
Register --> Configure --> Test --> Activate --> Monitor --> Update --> Deprecate --> Remove
    |            |           |         |            |          |           |           |
  Define      Set keys    Verify   Enable in    Watch for   New ver    Phase out   Clean up
  interface   & params    it works  workflows    errors      or config  usage       completely
```

### How to Think About It

**Instrument Categories**

| Category | Description | Examples |
|---|---|---|
| Core instruments | Built-in platform capabilities | Workflow engine, scheduler, data store |
| Integration instruments | Connections to external services | Telegram, email, webhooks, APIs |
| Custom instruments | User-defined tools and scripts | Custom Python scripts, shell commands |
| MCP instruments | Model Context Protocol servers | Serena, Playwright, Pinecone, Linear |

**Tool Configuration Anatomy**

Every tool registration has these components:

```text
Tool Registration
  ├── Identity
  │   ├── name          (unique identifier)
  │   ├── version       (semver)
  │   └── category      (core/integration/custom/mcp)
  │
  ├── Connection
  │   ├── endpoint      (URL or local path)
  │   ├── auth_method   (api_key/oauth/none)
  │   └── credentials   (reference to .env variable)
  │
  ├── Configuration
  │   ├── parameters    (default parameter values)
  │   ├── rate_limits   (max calls per period)
  │   └── timeout       (max response wait time)
  │
  └── Lifecycle
      ├── status        (active/inactive/deprecated)
      ├── health_check  (endpoint or command to verify)
      └── last_verified (timestamp of last successful check)
```

**Tool Health States**

| State | Meaning | Action Required |
|---|---|---|
| Active | Tool is registered, configured, and responding | None — monitor normally |
| Degraded | Tool is responding but with errors or slow performance | Investigate — check logs and external service status |
| Inactive | Tool is registered but disabled | Intentional — no action unless it should be active |
| Error | Tool is failing health checks | Urgent — diagnose and fix or disable dependent workflows |
| Deprecated | Tool is marked for removal | Plan — migrate dependent workflows to replacement |
| Unregistered | Tool reference exists in workflows but not in registry | Critical — workflow will fail; register or remove references |

### Step-by-Step Approach

**Step 1: List all registered instruments**

Start with a complete inventory of what is registered:

```text
{{platform_config(action="list_instruments")}}
```

**Step 2: Check health of all tools**

Run a health check across all registered instruments:

```text
{{platform_config(action="health_check", target="instruments")}}
```

**Step 3: Register a new instrument**

When adding a new tool, provide complete configuration:

```text
{{platform_config(action="register_instrument", name="telegram_bot", config={"category": "integration", "version": "1.0.0", "endpoint": "https://api.telegram.org", "auth_method": "api_key", "credential_env": "TELEGRAM_BOT_TOKEN", "rate_limit": {"max_calls": 30, "period_seconds": 60}, "timeout_seconds": 10, "health_check": {"method": "getMe", "interval_minutes": 5}})}}
```

**Step 4: Test the instrument before activating**

Never activate an untested tool in production:

```text
{{platform_config(action="test_instrument", name="telegram_bot", test_action="getMe")}}
```

**Step 5: Activate and monitor**

Once testing passes, activate and set up monitoring:

```text
{{platform_config(action="update_instrument", name="telegram_bot", config={"status": "active", "monitoring": {"alert_on_failure": true, "alert_channel": "admin_dashboard"}})}}
```

**Step 6: Managing custom instruments**

Custom instruments require additional care because they are not maintained by external vendors:

```text
{{platform_config(action="register_instrument", name="invoice_parser", config={"category": "custom", "version": "0.3.0", "endpoint": "local://skills/invoice-parser/run.py", "auth_method": "none", "parameters": {"supported_formats": ["pdf", "png", "jpg"], "max_file_size_mb": 10}, "health_check": {"method": "self_test", "interval_minutes": 15}, "owner": "platform_admin", "documentation": "skills/invoice-parser/README.md"})}}
```

**Step 7: Deprecating and removing instruments**

When a tool needs to be retired, follow the lifecycle:

```text
{{platform_config(action="update_instrument", name="old_email_sender", config={"status": "deprecated", "deprecation_reason": "Replaced by new_email_service", "replacement": "new_email_service", "removal_date": "2026-04-30"})}}
```

Check what depends on the deprecated tool before removing:

```text
{{platform_config(action="get_dependencies", component="old_email_sender")}}
```

### Practice Exercise

**Scenario:** You need to register and configure a new webhook receiver instrument that will accept incoming events from an external CRM system.

**Task:**

1. Register the webhook instrument:

```text
{{platform_config(action="register_instrument", name="crm_webhook_receiver", config={"category": "integration", "version": "1.0.0", "endpoint": "local://webhooks/crm_inbound", "auth_method": "webhook_secret", "credential_env": "CRM_WEBHOOK_SECRET", "parameters": {"accepted_events": ["contact.created", "contact.updated", "deal.won", "deal.lost"], "payload_format": "json", "max_payload_size_kb": 512}, "health_check": {"method": "echo_test", "interval_minutes": 10}})}}
```

1. Test it with a sample payload:

```text
{{platform_config(action="test_instrument", name="crm_webhook_receiver", test_action="echo_test", test_data={"event": "contact.created", "data": {"name": "Test Contact", "email": "test@example.com"}})}}
```

1. Activate and verify it appears in the instrument list:

```text
{{platform_config(action="update_instrument", name="crm_webhook_receiver", config={"status": "active"})}}
```

```text
{{platform_config(action="list_instruments", filter={"status": "active"})}}
```

**Self-check:** Can you answer these questions about your new instrument?

- What happens if the CRM sends an event type not in the accepted list?
- What credential is used for authentication and where is it stored?
- How will you know if the webhook stops working?
- What workflows depend on this instrument?

If any answer is "I don't know," your registration is incomplete.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Hardcoding credentials in tool config | Quick setup without thinking about security | Always reference `.env` variables; never put secrets in config files |
| No health checks configured | Assuming tools will "just work" | Every tool must have a health check with an alert |
| Skipping the test step | Confidence that configuration is correct | Always test before activating; a 2-minute test prevents a 2-hour incident |
| Not tracking dependencies before removal | Forgetting tools are used by workflows | Always run dependency check before deprecating or removing |
| No rate limit configuration | Not thinking about external API constraints | Set rate limits to 80% of the provider's limit to leave headroom |
| Orphaned registrations | Removing the service but not the registration | Audit instrument list quarterly; remove anything not in active use |
