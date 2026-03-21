# Module 23: Security & Monitoring

> **Learning Path:** Platform Administrator
> **Audience:** Sysadmins/DevOps operators managing the platform
> **Prerequisites:** Module 22 — Platform Configuration

---

## Lesson: Security Configuration

### Why This Matters

Security configuration is the difference between a platform that protects its data and one that leaks it. As a platform administrator, you are the last line of defense. Every API key left in a log file, every environment variable committed to version control, every access control left at its default is a door you left unlocked.

The consequences are not theoretical:

- **Exposed API keys** — a single leaked key to a paid service can generate thousands of dollars in charges within hours
- **Unrotated secrets** — credentials that have not been changed in 6 months are credentials that have had 6 months to be compromised
- **Overprivileged access** — when every operator has admin access, a single account compromise gives an attacker full control
- **Missing audit trails** — without logs of who did what, you cannot investigate incidents or prove compliance

**The security incident cost table:**

| Incident Type | Detection Time (no controls) | Remediation Cost | Preventable? |
|---|---|---|---|
| Leaked API key | Days to weeks | $500-$50,000 (service abuse) | Yes — secret scanning |
| Unauthorized config change | Unknown (no audit log) | Hours of forensic investigation | Yes — access controls + audit log |
| Stale credentials compromised | Months | Full credential rotation + incident review | Yes — automated rotation |
| Data exposed via misconfigured endpoint | Days to never | Regulatory fines, reputation damage | Yes — access controls + testing |

Security is not a feature you add later. It is a configuration discipline you practice from day one.

### How to Think About It

**The Secret Lifecycle**

Every secret (API key, token, password) follows a lifecycle. Your job is to manage every stage:

```text
Generate --> Store --> Distribute --> Use --> Rotate --> Revoke
    |           |          |           |        |          |
 Strong     .env file   Env vars    Code     Schedule   When
 entropy    encrypted   at runtime  refs     periodic   compromised
 only       at rest     only        only     rotation   or unused
```

**Environment Variable Best Practices**

The `.env` file is the single source of truth for secrets. Its management follows strict rules:

```text
# .env file structure — CORRECT
# ─────────────────────────────────
# Section: External API Keys
TELEGRAM_BOT_TOKEN=bot123456:ABC-DEF...
OPENAI_API_KEY=sk-proj-...

# Section: Database
DATABASE_URL=sqlite:///data/platform.db

# Section: Security
SESSION_SECRET=<64-char-random-string>
WEBHOOK_SECRET=<32-char-random-string>
CSRF_SECRET_KEY=<32-char-random-string>
```

**What never goes in `.env`:**

| Do Not Store | Why | Where Instead |
|---|---|---|
| Passwords in plaintext comments | Comments are not encrypted | Use a password manager reference |
| Test credentials mixed with production | Easy to confuse environments | Separate `.env.test` file |
| Credentials for decommissioned services | Attack surface with no benefit | Delete immediately |
| Full connection strings with embedded passwords | Too many secrets in one value | Break into separate variables |

**Access Control Model**

The platform uses role-based access control (RBAC). Understand the permission matrix:

| Permission | Viewer | Operator | Admin | Super Admin |
|---|---|---|---|---|
| View dashboards | Assigned only | All operational | All | All |
| Execute workflows | No | Assigned workflows | All | All |
| Modify configuration | No | Own scope only | Platform-wide | Platform-wide |
| Manage users | No | No | Yes | Yes |
| Rotate secrets | No | No | Assigned secrets | All secrets |
| Access audit logs | No | Own actions | All actions | All + system events |
| Modify security settings | No | No | No | Yes |

**The Principle of Least Privilege:** Every account gets the minimum permissions needed for its role. No exceptions. No "just give me admin for now." Escalation is temporary and logged.

### Step-by-Step Approach

**Step 1: Audit current secret configuration**

Review all configured secrets and their status:

```text
{{platform_config(action="get_status", scope="secrets")}}
```

This shows which secrets are configured, when they were last rotated, and whether any are missing or expired.

**Step 2: Check for leaked secrets**

Scan the codebase and logs for accidentally exposed credentials:

```text
{{platform_config(action="security_scan", target="secret_leaks", scope=["codebase", "logs", "config_files"])}}
```

**Step 3: Set up secret rotation schedule**

Define rotation intervals based on risk level:

```text
{{platform_config(action="configure_rotation", secrets=[{"name": "OPENAI_API_KEY", "rotation_days": 90, "alert_days_before": 14}, {"name": "TELEGRAM_BOT_TOKEN", "rotation_days": 180, "alert_days_before": 30}, {"name": "SESSION_SECRET", "rotation_days": 30, "alert_days_before": 7}, {"name": "WEBHOOK_SECRET", "rotation_days": 90, "alert_days_before": 14}])}}
```

**Step 4: Configure access controls**

Set up roles and assign appropriate permissions:

```text
{{platform_config(action="configure_access", role="operator", permissions={"dashboards": "view_all", "workflows": "execute_assigned", "config": "own_scope", "secrets": "none", "audit_log": "own_actions"})}}  # pragma: allowlist secret
```

**Step 5: Enable audit logging**

Ensure all security-relevant actions are logged:

```text
{{platform_config(action="configure_audit_log", settings={"log_auth_events": true, "log_config_changes": true, "log_secret_access": true, "log_permission_changes": true, "retention_days": 365, "storage": "data/audit/security.log"})}}
```

**Step 6: Verify `.env` file permissions**

The `.env` file should only be readable by the service account:

```text
{{platform_config(action="check_file_permissions", path=".env", expected_mode="600")}}
```

### Practice Exercise

**Scenario:** You have taken over a platform that was set up by a developer who "just wanted to get it working." You suspect security was not a priority.

**Task:** Perform a security audit and remediate findings.

1. Run a comprehensive security scan:

```text
{{platform_config(action="security_scan", target="comprehensive", scope=["secrets", "permissions", "config", "network"])}}
```

1. Check the age of all secrets:

```text
{{platform_config(action="get_status", scope="secrets", include_age=true)}}
```

1. Review current access control configuration:

```text
{{platform_config(action="get_config", scope="access_control")}}
```

1. Set up a rotation schedule for any secrets older than 90 days:

```text
{{platform_config(action="configure_rotation", secrets=[{"name": "ALL_EXPIRED", "rotation_days": 90, "immediate": true}])}}
```

1. Restrict file permissions on sensitive files:

```text
{{platform_config(action="set_file_permissions", files=[{"path": ".env", "mode": "600"}, {"path": "data/platform.db", "mode": "640"}, {"path": "data/audit/", "mode": "750"}])}}
```

**Self-check:** After your audit, answer these questions:

- How many secrets have not been rotated in 90+ days?
- Are there any API keys visible in log files?
- Does every user account have the minimum required permissions?
- Is the audit log capturing all security events?

If any answer concerns you, you have more work to do.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Committing `.env` to version control | Forgetting to add to `.gitignore` | Verify `.gitignore` includes `.env`; use `git log` to check if it was ever committed |
| Using the same API key for dev and production | Convenience during setup | Generate separate keys per environment; label them clearly |
| Giving everyone admin access | "We're a small team" | Start with least privilege; escalate temporarily when needed |
| Never rotating secrets | No reminder system in place | Configure automated rotation alerts; treat rotation as scheduled maintenance |
| Logging request bodies containing secrets | Default verbose logging | Configure log sanitization to redact sensitive fields |
| Disabling security features during debugging | "I'll turn it back on" | Use a debug role with elevated but still scoped permissions |

---

## Lesson: Observability and Health Monitoring

### Why This Matters

Observability is the ability to understand what your platform is doing without having to guess. Without it, your operational model is reactive: you learn about problems from users complaining. With it, your model is proactive: you see problems forming and fix them before anyone notices.

The three pillars of observability are:

- **Logs** — what happened (event records)
- **Metrics** — how much happened (numerical measurements over time)
- **Traces** — how it happened (request flow through components)

**The cost of flying blind:**

| Scenario | Without Observability | With Observability |
|---|---|---|
| API response time doubles | Users complain hours later | Alert fires in 5 minutes, you see the cause in the dashboard |
| Workflow starts failing at 2 AM | Nobody knows until 9 AM standup | PagerDuty alert, fixed by 2:15 AM |
| Database disk at 95% | Platform crashes, emergency recovery | Trend chart predicted this 2 weeks ago, you expanded storage |
| External API starts rate-limiting | Intermittent failures, hard to reproduce | Rate limit counter dashboard shows the pattern immediately |

**The observability maturity model:**

| Level | Capability | You Can Answer |
|---|---|---|
| 0 — None | No monitoring | "Is it up?" — maybe, check manually |
| 1 — Basic | Health checks only | "Is it up?" — yes/no, right now |
| 2 — Reactive | Health checks + error logs | "What broke?" — after it broke |
| 3 — Proactive | Metrics + alerting + dashboards | "Is something about to break?" — usually |
| 4 — Predictive | Trends + baselines + anomaly detection | "When will we need to scale?" — with data to back it up |

Your target is Level 3 minimum, Level 4 for production-critical components.

### How to Think About It

**Health Check Architecture**

Health checks verify that components are functional. They should be layered:

```text
Platform Health
  │
  ├── Infrastructure Checks
  │   ├── Database connectivity and response time
  │   ├── Disk space and I/O performance
  │   ├── Memory utilization
  │   └── Network connectivity
  │
  ├── Application Checks
  │   ├── API server responding
  │   ├── Workflow engine processing
  │   ├── Scheduler running on time
  │   └── WebSocket connections active
  │
  ├── Integration Checks
  │   ├── External API reachability
  │   ├── Webhook delivery success
  │   ├── MCP server connections
  │   └── Tunnel status
  │
  └── Data Checks
      ├── Database integrity
      ├── Queue depth (processing backlog)
      ├── Cache hit rates
      └── Storage growth rate
```

**Key Metrics to Track**

| Metric | What It Tells You | Warning Threshold | Critical Threshold |
|---|---|---|---|
| API response time (p95) | User experience | > 500ms | > 2000ms |
| Workflow success rate | Core functionality | < 98% | < 90% |
| Error rate (5xx) | Application stability | > 1% of requests | > 5% of requests |
| Queue depth | Processing backlog | > 100 items | > 500 items |
| Disk usage | Storage capacity | > 80% | > 90% |
| Memory usage | Application stability | > 75% | > 90% |
| External API latency | Integration health | > 1000ms | > 5000ms |
| Failed health checks | Component status | Any single failure | Multiple failures |

**Alerting Rules: Signal vs. Noise**

The goal of alerting is to notify you when action is needed — not when something is merely interesting. Every alert should pass the "wake me up at 3 AM" test: if this fired at 3 AM, would I need to do something right now?

```text
Alert Levels:
  │
  ├── CRITICAL — Immediate action required
  │   ├── Service down
  │   ├── Data loss risk
  │   └── Security breach detected
  │   → Notification: PagerDuty / SMS / Phone
  │
  ├── WARNING — Action needed within hours
  │   ├── Performance degraded
  │   ├── Resource trending toward limit
  │   └── Error rate elevated
  │   → Notification: Dashboard + Email
  │
  └── INFO — For awareness and trending
      ├── Deployment completed
      ├── Config change applied
      └── Scheduled maintenance done
      → Notification: Dashboard only
```

### Step-by-Step Approach

**Step 1: Run a comprehensive health check**

Start with the current state of all components:

```text
{{platform_config(action="health_check")}}
```

**Step 2: Establish performance baselines**

You cannot detect anomalies without knowing what normal looks like. Collect baseline metrics:

```text
{{platform_config(action="collect_baseline", duration="7d", metrics=["api_response_time", "workflow_success_rate", "error_rate", "queue_depth", "disk_usage", "memory_usage"])}}
```

**Step 3: Configure health check schedule**

Set up automated health checks at appropriate intervals:

```text
{{platform_config(action="configure_health_checks", checks=[{"name": "database", "interval_seconds": 30, "timeout_seconds": 5, "on_failure": "alert_critical"}, {"name": "api_server", "interval_seconds": 15, "timeout_seconds": 3, "on_failure": "alert_critical"}, {"name": "workflow_engine", "interval_seconds": 60, "timeout_seconds": 10, "on_failure": "alert_warning"}, {"name": "external_apis", "interval_seconds": 300, "timeout_seconds": 15, "on_failure": "alert_warning"}, {"name": "disk_space", "interval_seconds": 3600, "timeout_seconds": 5, "on_failure": "alert_warning"}])}}
```

**Step 4: Set up alerting rules**

Define what triggers alerts and where they go:

```text
{{platform_config(action="configure_alerts", rules=[{"name": "high_error_rate", "condition": "error_rate_5xx > 5%", "window": "5m", "severity": "critical", "channel": "admin_dashboard"}, {"name": "slow_responses", "condition": "api_p95_latency > 2000ms", "window": "5m", "severity": "warning", "channel": "admin_dashboard"}, {"name": "disk_warning", "condition": "disk_usage > 80%", "window": "1h", "severity": "warning", "channel": "admin_dashboard"}, {"name": "workflow_failures", "condition": "workflow_success_rate < 90%", "window": "15m", "severity": "critical", "channel": "admin_dashboard"}])}}
```

**Step 5: Configure log management**

Set up structured logging with appropriate retention:

```text
{{platform_config(action="configure_logging", settings={"format": "json", "levels": {"application": "info", "security": "debug", "performance": "info"}, "rotation": {"max_size_mb": 100, "max_files": 10, "compress": true}, "retention_days": 90, "sensitive_field_redaction": ["api_key", "token", "password", "secret"]})}}
```

**Step 6: Create a monitoring dashboard**

Build a dashboard that shows all health signals in one view:

```text
{{platform_config(action="create_dashboard", name="System Health", layout="grid", description="Real-time platform health and performance monitoring")}}
```

```text
{{platform_config(action="add_widget", dashboard="System Health", widget_type="status_indicator", config={"title": "Component Health", "sources": ["database", "api_server", "workflow_engine", "scheduler", "external_apis"], "position": {"row": 1, "col": 1, "width": 4}})}}
```

### Practice Exercise

**Scenario:** The platform has been running for 3 months with no monitoring beyond "is the web page loading." You need to implement proper observability.

**Task:** Build a monitoring stack from scratch.

1. Run the initial health check to understand current state:

```text
{{platform_config(action="health_check")}}
```

1. Collect a 7-day baseline of key metrics:

```text
{{platform_config(action="collect_baseline", duration="7d", metrics=["api_response_time", "workflow_success_rate", "queue_depth", "disk_usage"])}}
```

1. Configure health checks and alerts:

```text
{{platform_config(action="configure_health_checks", checks=[{"name": "all_components", "interval_seconds": 60, "on_failure": "alert_warning"}])}}
```

1. Set up log rotation to prevent disk exhaustion:

```text
{{platform_config(action="configure_logging", settings={"rotation": {"max_size_mb": 50, "max_files": 5, "compress": true}})}}
```

**Self-check:** After setup, verify:

- Can you see the current health status of every component from a single dashboard?
- Will you be alerted if the API goes down at 3 AM?
- Do you know what "normal" looks like for response times and error rates?
- Are your logs being rotated before they fill the disk?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Alerting on every error | Setting thresholds too low | Alert on rates and trends, not individual events |
| No baseline metrics | Skipping the "what is normal" step | Collect 7 days of baseline data before setting thresholds |
| Log files growing unbounded | Forgetting to configure rotation | Set up rotation from day one; check disk usage weekly |
| Health checks with no alerts | Checking but not notifying | Every health check must have a failure action defined |
| Monitoring only infrastructure, not application | Focus on CPU/memory instead of business metrics | Track workflow success rates and queue depths alongside system metrics |
| Same alert severity for everything | Not differentiating urgency | Use critical for "action now," warning for "action today," info for awareness |

---

## Lesson: Backup and Recovery

### Why This Matters

Backups are the insurance policy you hope you never need. But when you need them — a corrupted database, an accidental deletion, a failed upgrade, a compromised system — they are the only thing standing between you and catastrophe.

**The backup paradox:** The time you most need a backup is the time you are least prepared for it. Systems fail during upgrades, during high load, during the middle of the night. If your backup process requires manual steps, calm conditions, and an awake operator, it will fail when it matters most.

**What data loss actually looks like:**

| Scenario | Without Backups | With Backups |
|---|---|---|
| Database corruption after power loss | All data since last manual export gone | Restore from last automated backup, lose minutes not days |
| Accidental deletion of config files | Rebuild from memory and guesswork | Restore exact configuration from backup |
| Failed upgrade corrupts data | Roll back code but data is unrecoverable | Restore pre-upgrade snapshot, retry |
| Ransomware encrypts data directory | Pay ransom or lose everything | Wipe, restore from offsite backup |

**The 3-2-1 backup rule:**

- **3** copies of your data (production + 2 backups)
- **2** different storage types (local disk + remote/cloud)
- **1** offsite copy (survives physical disasters)

### How to Think About It

**What to Back Up**

Not all data is equal. Prioritize by how hard it would be to recreate:

| Data Type | Location | Backup Priority | Recreatable? |
|---|---|---|---|
| Database | `data/platform.db` | Critical | No — contains all runtime state |
| Configuration | `.env`, `config/`, `skills/registry.json` | Critical | Partially — but getting it exactly right takes hours |
| Knowledge base | `knowledge/` | High | Maybe — depends on whether sources still exist |
| Training content | `training/content/` | High | Yes, but expensive (hours of writing) |
| Log files | `data/logs/` | Medium | No, but old logs decrease in value quickly |
| Cache files | `data/cache/` | Low | Yes — rebuilt automatically |
| Temporary files | `/tmp/`, scratch dirs | None | Yes — ephemeral by definition |

**Backup Strategies Compared**

| Strategy | Speed | Storage Cost | Recovery Time | Complexity |
|---|---|---|---|---|
| Full backup | Slow | High | Fast | Low |
| Incremental | Fast | Low | Slower (needs base + increments) | Medium |
| Differential | Medium | Medium | Medium (needs base + latest diff) | Medium |
| Snapshot | Instant | Varies | Fast | Low (if platform supports) |
| Replication | Continuous | High | Near-zero | High |

**Recommended approach for this platform:**

```text
Backup Schedule
  │
  ├── Database
  │   ├── Full backup:        Daily at 02:00
  │   ├── Incremental backup: Every 6 hours
  │   └── Retention:          30 days full, 7 days incremental
  │
  ├── Configuration
  │   ├── Full backup:        On every change (event-triggered)
  │   ├── Snapshot:           Daily at 02:00
  │   └── Retention:          90 days
  │
  ├── Knowledge Base
  │   ├── Full backup:        Weekly (Sunday 03:00)
  │   ├── Incremental:        Daily at 03:00
  │   └── Retention:          60 days
  │
  └── Verification
      ├── Backup integrity check: After every backup
      ├── Restore test:           Monthly
      └── Full DR drill:          Quarterly
```

**Recovery Point Objective (RPO) vs. Recovery Time Objective (RTO)**

Two numbers define your backup requirements:

- **RPO** — How much data can you afford to lose? If RPO is 1 hour, you need backups at least every hour.
- **RTO** — How long can you afford to be down? If RTO is 30 minutes, your restore process must complete in under 30 minutes.

```text
     Data Loss Window            Downtime Window
  ◄──────────────────►      ◄──────────────────────►
  Last backup         Failure                    Service restored
      |                  |                           |
  ────●──────────────────X───────────────────────────●────
      RPO = time since    Incident                 RTO = time
      last backup         occurs                   to recover
```

### Step-by-Step Approach

**Step 1: Inventory your critical data**

Identify what needs to be backed up and its priority:

```text
{{platform_config(action="get_status", scope="data_inventory")}}
```

**Step 2: Configure automated database backup**

Set up the backup schedule for your most critical asset:

```text
{{platform_config(action="backup", target="database", config={"schedule": "0 2 * * *", "type": "full", "destination": "data/backups/db/", "retention_days": 30, "compression": true, "verify_after_backup": true})}}
```

Add incremental backups between full backups:

```text
{{platform_config(action="backup", target="database", config={"schedule": "0 */6 * * *", "type": "incremental", "destination": "data/backups/db/incremental/", "retention_days": 7, "compression": true})}}
```

**Step 3: Configure configuration backup**

Back up configuration on every change:

```text
{{platform_config(action="backup", target="configuration", config={"trigger": "on_change", "paths": [".env", "config/", "skills/registry.json"], "destination": "data/backups/config/", "retention_days": 90, "include_metadata": true})}}
```

**Step 4: Set up backup verification**

A backup you have not tested is not a backup. It is a hope.

```text
{{platform_config(action="verify_backup", target="database", backup_id="latest", checks=["integrity", "completeness", "restorability"])}}
```

**Step 5: Test the restore process**

Perform a restore to a test location to verify it works:

```text
{{platform_config(action="restore", target="database", backup_id="latest", destination="data/restore-test/", dry_run=true)}}
```

**Step 6: Document the disaster recovery procedure**

Create a step-by-step runbook that anyone on the team can follow:

```text
{{platform_config(action="create_runbook", name="disaster_recovery", steps=[{"order": 1, "action": "Assess the scope of data loss or corruption", "command": "platform_config(action='health_check')"}, {"order": 2, "action": "Stop all services to prevent further damage", "command": "platform_config(action='stop_services')"}, {"order": 3, "action": "Identify the best backup to restore from", "command": "platform_config(action='list_backups', target='database')"}, {"order": 4, "action": "Restore database from selected backup", "command": "platform_config(action='restore', target='database', backup_id='<selected>')"}, {"order": 5, "action": "Restore configuration if affected", "command": "platform_config(action='restore', target='configuration', backup_id='latest')"}, {"order": 6, "action": "Verify restored data integrity", "command": "platform_config(action='health_check', target='database')"}, {"order": 7, "action": "Restart services and verify functionality", "command": "platform_config(action='start_services')"}])}}
```

### Practice Exercise

**Scenario:** It is Friday afternoon. You discover that a script accidentally deleted half the records from the workflow history table. The last known good state was at 10:00 AM today. It is now 3:00 PM.

**Task:** Execute the recovery procedure.

1. Stop services to prevent further writes:

```text
{{platform_config(action="health_check", target="database")}}
```

1. List available backups to find the one closest to 10:00 AM:

```text
{{platform_config(action="list_backups", target="database", filter={"date": "2026-03-20", "before": "10:00"})}}
```

1. Test the restore in a dry-run first:

```text
{{platform_config(action="restore", target="database", backup_id="db-2026-03-20-0800", destination="data/restore-test/", dry_run=true)}}
```

1. If dry-run succeeds, perform the actual restore:

```text
{{platform_config(action="restore", target="database", backup_id="db-2026-03-20-0800", destination="data/platform.db", confirm=true)}}
```

1. Verify the restored data:

```text
{{platform_config(action="health_check", target="database")}}
```

**Self-check:** After recovery, answer:

- How much data was lost? (RPO: 5 hours, from 10 AM backup to 3 PM incident)
- How long did recovery take? (RTO: measure your actual recovery time)
- Could you have lost less data? (Yes — if incremental backups ran every 6 hours, the 2 PM incremental would have been available)
- What will you change to prevent this in the future? (More frequent backups, restricted delete permissions, pre-script backup requirement)

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Never testing restores | "We have backups, so we're fine" | Test restores monthly; an untested backup is just a file |
| Backing up to the same disk | Convenience and cost | Use at least one offsite or separate-volume destination |
| No retention policy | Keeping everything forever | Set retention periods; old backups consume space and slow operations |
| Manual backup process | Automation seemed like overkill | Automate from day one; manual processes get skipped under pressure |
| Not backing up configuration | Focusing only on database | Config is often harder to recreate than data; back it up on every change |
| Ignoring backup verification errors | "It probably worked" | Every verification failure is a backup that will fail when you need it most |
