# Module 24: Admin Capstone

> **Learning Path:** Platform Administrator
> **Audience:** Sysadmins/DevOps operators managing the platform
> **Prerequisites:** Module 22 — Platform Configuration, Module 23 — Security & Monitoring

---

## Lesson: Platform Health Audit

### Why This Matters

A platform health audit is a comprehensive, systematic review of every aspect of your platform. It is the difference between "I think everything is fine" and "I have evidence that everything is fine."

Without regular audits:

- **Configuration drift goes undetected** — small changes accumulate over weeks until the system no longer matches its documented state
- **Performance degrades gradually** — response times creep up by 10ms per week, and nobody notices until users start complaining 3 months later
- **Security gaps widen** — a temporary permission escalation from 6 weeks ago is still active because nobody checked
- **Technical debt compounds** — deprecated tools stay registered, unused dashboards clutter the interface, stale backups consume storage

**The audit pays for itself:**

| Audit Finding | Cost If Missed | Time to Find in Audit |
|---|---|---|
| Expired API key about to disrupt service | 2-4 hours of emergency response | 30 seconds (automated check) |
| Database 10x larger than expected | Surprise storage failure | 1 minute (size trending) |
| 3 operator accounts with stale admin privileges | Potential security breach | 5 minutes (permission review) |
| Backup job silently failing for 2 weeks | Data loss on next incident | 2 minutes (backup verification) |
| Config file manually edited, doesn't match source control | Mysterious behavior differences | 10 minutes (drift detection) |

A monthly audit that takes 2 hours prevents incidents that take 20 hours to resolve. The math is not complicated.

### How to Think About It

**The Audit Framework**

A complete platform health audit covers five domains:

```text
Platform Health Audit
  │
  ├── 1. Infrastructure Health
  │   ├── Resource utilization (CPU, memory, disk)
  │   ├── Service uptime and availability
  │   ├── Network connectivity
  │   └── Dependency versions and patches
  │
  ├── 2. Application Health
  │   ├── Workflow success rates
  │   ├── API response times
  │   ├── Error rates and patterns
  │   └── Queue depths and processing latency
  │
  ├── 3. Security Posture
  │   ├── Secret rotation compliance
  │   ├── Access control review
  │   ├── Audit log completeness
  │   └── Vulnerability scan results
  │
  ├── 4. Data Integrity
  │   ├── Backup status and recency
  │   ├── Database integrity checks
  │   ├── Storage growth trends
  │   └── Data retention compliance
  │
  └── 5. Configuration Compliance
      ├── Config drift detection
      ├── Deprecated component inventory
      ├── Documentation accuracy
      └── Runbook validity
```

**Performance Baselines**

A baseline is your definition of "normal." Without it, you cannot distinguish a problem from expected behavior.

| Metric | How to Establish Baseline | Review Frequency |
|---|---|---|
| API response time (p95) | Average over 30 days of normal operation | Monthly |
| Workflow completion rate | Average over 30 days | Monthly |
| Error rate | Average over 30 days | Weekly |
| Database size | Growth rate over 90 days | Monthly |
| Disk usage | Growth rate over 90 days | Monthly |
| Active user sessions | Peak and average over 30 days | Monthly |

**Baseline drift thresholds:**

- **Green:** Within 10% of baseline — no action needed
- **Yellow:** 10-25% deviation from baseline — investigate the cause
- **Red:** More than 25% deviation from baseline — take corrective action

**Configuration Drift Detection**

Configuration drift is when the running configuration no longer matches the documented or intended configuration. It happens through:

```text
Intended State ──────────────────────────── Actual State
      │                                          │
      │  "Just a quick fix"                      │
      │  "I'll document it later"                │
      │  "It's only temporary"                   │
      │  "The update changed a default"          │
      │                                          │
      └──── DRIFT ──────────────────────────────┘
```

Common drift sources:

| Source | Example | Detection Method |
|---|---|---|
| Manual hotfix | Edited config file directly during incident | File hash comparison against version control |
| Undocumented change | Operator changed a setting via UI, didn't log it | Audit log review vs. change request records |
| Software update | New version changed default values | Compare defaults before/after update |
| Environment difference | Dev and prod configs diverged | Cross-environment config comparison |

### Step-by-Step Approach

**Step 1: Infrastructure health check**

Run a comprehensive health check across all components:

```text
{{platform_config(action="health_check")}}
```

Review resource utilization:

```text
{{platform_config(action="get_status", scope="resources", metrics=["cpu", "memory", "disk", "network"])}}
```

**Step 2: Application health review**

Check workflow performance and error rates:

```text
{{platform_config(action="get_status", scope="application", metrics=["workflow_success_rate", "api_response_time_p95", "error_rate_5xx", "queue_depth"], timeframe="30d")}}
```

Compare against baselines:

```text
{{platform_config(action="compare_baseline", current_period="7d", baseline_period="30d", metrics=["api_response_time", "workflow_success_rate", "error_rate"])}}
```

**Step 3: Security posture review**

Check secret rotation compliance and access controls:

```text
{{platform_config(action="security_scan", target="comprehensive", scope=["secrets", "permissions", "vulnerabilities"])}}
```

Review audit logs for unexpected activity:

```text
{{platform_config(action="get_audit_log", filter={"timeframe": "30d", "types": ["permission_change", "config_change", "failed_auth"]}, summary=true)}}
```

**Step 4: Data integrity verification**

Verify backup status and test restore capability:

```text
{{platform_config(action="verify_backup", target="all", checks=["existence", "integrity", "recency"])}}
```

Check database integrity:

```text
{{platform_config(action="health_check", target="database", checks=["integrity", "size", "fragmentation", "index_health"])}}
```

**Step 5: Configuration drift detection**

Compare running configuration against the documented baseline:

```text
{{platform_config(action="detect_drift", sources=["env_vars", "config_files", "skill_registry", "dashboard_config"], baseline="version_control")}}
```

**Step 6: Generate the audit report**

Compile findings into a structured report:

```text
{{platform_config(action="generate_report", type="health_audit", include=["infrastructure", "application", "security", "data", "configuration"], format="summary_with_actions")}}
```

### Practice Exercise

**Scenario:** You are conducting the platform's first formal health audit. The system has been running for 4 months with no structured review.

**Task:** Execute a complete audit following the framework above.

1. Run all five domain checks (infrastructure, application, security, data, configuration).
1. For each finding, classify it as Green (no action), Yellow (investigate), or Red (act now).
1. Create a prioritized action list from your Red and Yellow findings.

Start with the health check:

```text
{{platform_config(action="health_check")}}
```

Then run the security scan:

```text
{{platform_config(action="security_scan", target="comprehensive")}}
```

Then verify backups:

```text
{{platform_config(action="verify_backup", target="all")}}
```

Then check for drift:

```text
{{platform_config(action="detect_drift", baseline="version_control")}}
```

**Self-check:** Your audit should produce:

- A clear Red/Yellow/Green status for each of the 5 domains
- At least 3 actionable findings (if you found zero, your audit was not thorough enough)
- A prioritized remediation plan with estimated effort for each item
- An updated baseline for future comparison

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Skipping the audit when everything "seems fine" | Audit feels unnecessary when nothing is broken | Schedule audits like maintenance; they find problems before they break things |
| Only checking what failed last time | Recency bias | Follow the full checklist every time; new issues emerge in different domains |
| Audit with no follow-through | Findings documented but never acted on | Assign owners and deadlines to every Red/Yellow finding |
| No baseline to compare against | First audit has nothing to compare to | Establish baselines from the first audit; they improve over time |
| Auditing production during peak hours | Squeezing audit into business hours | Schedule comprehensive checks during low-usage windows |

---

## Lesson: Onboarding New Operators

### Why This Matters

Every new operator is a risk until they are properly onboarded. A new team member with platform access but no training is more dangerous than no team member at all. They can:

- **Misconfigure critical components** because they do not understand the configuration hierarchy
- **Escalate privileges** incorrectly because they do not know the access control model
- **Break production workflows** by testing in the wrong environment
- **Create security gaps** by storing credentials insecurely

Equally, a poorly onboarded operator is an ineffective operator. They spend weeks asking questions that documentation should answer, they develop bad habits because nobody showed them the right way, and they lose confidence in a system that feels arbitrary and undocumented.

**The onboarding quality matrix:**

| Onboarding Quality | Time to Productivity | Risk of Incident | Operator Confidence |
|---|---|---|---|
| None (here's your login) | 4-8 weeks | Very high | Very low |
| Basic (read these docs) | 2-4 weeks | High | Low |
| Structured (guided training) | 1-2 weeks | Medium | Medium |
| Excellent (mentored + practiced) | 3-5 days | Low | High |

The difference between "None" and "Excellent" is not effort — it is preparation. A well-designed onboarding process runs itself. A missing one costs you every time someone joins.

### How to Think About It

**The Onboarding Checklist**

Every new operator goes through these phases:

```text
Pre-Access Setup
  │
  ├── Account creation
  ├── Role assignment
  ├── Initial permissions (minimal)
  └── Environment preparation
  │
  ▼
Guided Orientation (Day 1-2)
  │
  ├── Platform architecture walkthrough
  ├── Directory structure tour
  ├── Dashboard overview
  └── "Where to find things" guide
  │
  ▼
Supervised Practice (Day 3-5)
  │
  ├── Read-only operations (viewing status, reading logs)
  ├── Non-critical operations (test environment)
  ├── First supervised production task
  └── Shadowing an experienced operator
  │
  ▼
Independent Operation (Week 2+)
  │
  ├── Assigned operational responsibilities
  ├── Escalation procedures confirmed
  ├── Permission elevation (as competence demonstrated)
  └── Enrolled in ongoing training path
```

**Permission Escalation Model**

New operators start with minimal access and earn more as they demonstrate competence:

| Day | Access Level | What They Can Do | Gate to Next Level |
|---|---|---|---|
| Day 1-2 | Viewer | View dashboards, read logs | Complete orientation checklist |
| Day 3-5 | Limited Operator | Run read-only commands, view all configs | Complete supervised practice tasks |
| Week 2 | Operator | Execute standard workflows, manage assigned tools | Demonstrated independent troubleshooting |
| Week 4+ | Senior Operator | Full operational access, on-call eligible | Completed admin training path + mentor sign-off |
| As needed | Admin | Configuration changes, user management | Formal request + approval |

**Training Path Enrollment**

Every new operator should be enrolled in the Platform Administrator learning path:

```text
Platform Administrator Path
  │
  ├── Module 22: Platform Configuration (required)
  │   ├── Platform Architecture Overview
  │   ├── Dashboard Configuration
  │   └── Instrument and Tool Management
  │
  ├── Module 23: Security & Monitoring (required)
  │   ├── Security Configuration
  │   ├── Observability and Health Monitoring
  │   └── Backup and Recovery
  │
  └── Module 24: Admin Capstone (required)
      ├── Platform Health Audit
      ├── Onboarding New Operators
      └── Capacity Planning
```

### Step-by-Step Approach

**Step 1: Create the operator account**

Set up the account with initial minimal permissions:

```text
{{platform_config(action="create_user", username="jpark", role="viewer", data={"full_name": "Jordan Park", "email": "jpark@example.com", "team": "operations", "start_date": "2026-03-20", "onboarding_status": "pre_access"})}}
```

**Step 2: Configure initial permissions**

Apply the Day 1-2 permission set:

```text
{{platform_config(action="configure_access", user="jpark", role="viewer", permissions={"dashboards": "view_assigned", "logs": "read_only", "config": "none", "workflows": "none", "assigned_dashboards": ["System Health", "Platform Operations"]})}}
```

**Step 3: Enroll in the training path**

Register the new operator in the Platform Administrator learning path:

```text
{{workflow_training(action="enroll_path", path_id="platform-administrator", agent_id="jpark", data={"enrollment_date": "2026-03-20", "target_completion": "2026-04-17", "mentor": "admin-lead"})}}
```

**Step 4: Generate the onboarding checklist**

Create a tracked checklist for the new operator:

```text
{{platform_config(action="create_checklist", name="Operator Onboarding - Jordan Park", items=[{"task": "Account created and credentials delivered securely", "due": "Day 0", "status": "complete"}, {"task": "Platform architecture walkthrough with mentor", "due": "Day 1", "status": "pending"}, {"task": "Directory structure tour and key file locations", "due": "Day 1", "status": "pending"}, {"task": "Dashboard orientation and navigation", "due": "Day 1", "status": "pending"}, {"task": "Read-only operations practice (5 exercises)", "due": "Day 2-3", "status": "pending"}, {"task": "First supervised production task", "due": "Day 4", "status": "pending"}, {"task": "Escalation procedures review and sign-off", "due": "Day 5", "status": "pending"}, {"task": "Module 22 completion", "due": "Week 2", "status": "pending"}, {"task": "Permission elevation to Operator", "due": "Week 2", "status": "pending"}, {"task": "Module 23 completion", "due": "Week 3", "status": "pending"}, {"task": "Module 24 completion and capstone", "due": "Week 4", "status": "pending"}])}}
```

**Step 5: Elevate permissions as onboarding progresses**

After the new operator completes the orientation checklist:

```text
{{platform_config(action="configure_access", user="jpark", role="operator", permissions={"dashboards": "view_all", "logs": "read_only", "config": "own_scope", "workflows": "execute_assigned"})}}
```

**Step 6: Verify training completion and competence**

Check progress on the training path:

```text
{{workflow_training(action="get_progress", path_id="platform-administrator", agent_id="jpark")}}
```

After all modules are complete and the mentor signs off:

```text
{{platform_config(action="configure_access", user="jpark", role="senior_operator", permissions={"dashboards": "view_all", "logs": "read_all", "config": "platform_wide", "workflows": "execute_all", "on_call": true})}}
```

### Practice Exercise

**Scenario:** Two new operators are joining your team next week. One is an experienced sysadmin from another team (Alex). The other is a junior hire straight from training (Morgan). They need different onboarding speeds but the same quality bar.

**Task:** Set up onboarding for both.

1. Create accounts with appropriate initial access:

```text
{{platform_config(action="create_user", username="alex_t", role="viewer", data={"full_name": "Alex Torres", "email": "atorres@example.com", "experience": "senior_sysadmin", "start_date": "2026-03-25"})}}
```

```text
{{platform_config(action="create_user", username="morgan_l", role="viewer", data={"full_name": "Morgan Lee", "email": "mlee@example.com", "experience": "junior", "start_date": "2026-03-25"})}}
```

1. Enroll both in the training path:

```text
{{workflow_training(action="enroll_path", path_id="platform-administrator", agent_id="alex_t", data={"target_completion": "2026-04-08", "pace": "accelerated"})}}
```

```text
{{workflow_training(action="enroll_path", path_id="platform-administrator", agent_id="morgan_l", data={"target_completion": "2026-04-22", "pace": "standard", "mentor": "alex_t"})}}
```

1. Create customized checklists reflecting their different experience levels.

**Self-check:** For each new operator, verify:

- Do they have the minimum access needed for their current onboarding phase?
- Is there a clear path from their current permissions to their target role?
- Are they enrolled in training with realistic completion dates?
- Does someone know they are responsible for mentoring each person?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Giving full admin access on day one | "They'll need it eventually" | Start minimal; elevate as competence is demonstrated |
| No structured checklist | "They'll figure it out" | Create a tracked checklist; ambiguity breeds bad habits |
| Skipping the training path | "They're experienced, they don't need training" | Everyone completes the path; experienced operators can go faster |
| No mentor assigned | Assuming the team will help informally | Assign a specific mentor; informal help is inconsistent |
| Not verifying credential delivery security | Sending passwords via Slack or email | Use a secure credential delivery method; never plaintext in chat |
| Same onboarding for all experience levels | One-size-fits-all process | Adjust pace, not content; everyone covers the same material |

---

## Lesson: Capacity Planning

### Why This Matters

Capacity planning is the discipline of ensuring your platform can handle tomorrow's load, not just today's. Without it, you operate in a constant state of surprise: every growth milestone becomes an emergency, every traffic spike becomes a fire drill, and every budget conversation is reactive.

**What unplanned capacity constraints look like:**

- **Database fills up at 2 AM** — nobody knew it was growing at 500MB/week because nobody was tracking it
- **Workflow queue backs up during peak hours** — the system that handled 100 workflows/day cannot handle 300, and you did not see it coming
- **API rate limits hit during a campaign** — the external service caps at 1000 calls/hour and your new feature needs 3000
- **Response times degrade gradually** — each new feature adds 50ms of latency until the platform feels sluggish

**The capacity planning return on investment:**

| Planning Horizon | Cost of Planning | Cost of Not Planning |
|---|---|---|
| 1 month ahead | 2 hours of analysis | Emergency scaling at premium cost |
| 3 months ahead | 4 hours of analysis | Downtime during growth spikes |
| 6 months ahead | 8 hours of analysis | Architecture redesign under pressure |
| 12 months ahead | 16 hours of analysis | Platform migration or replacement |

Spending 2-16 hours on planning prevents 20-160 hours of emergency response. The leverage is 10:1.

### How to Think About It

**The Capacity Planning Framework**

Capacity planning answers four questions:

```text
1. Where are we now?        → Current utilization
1. Where are we going?      → Growth projections
1. When will we hit limits? → Threshold analysis
1. What do we do about it?  → Scaling strategy
```

**Resource Utilization Analysis**

Track utilization across all constrained resources:

| Resource | Metric | Current Usage | Capacity | Utilization % | Headroom |
|---|---|---|---|---|---|
| Storage (database) | Disk space | 2.1 GB | 10 GB | 21% | 7.9 GB |
| Storage (backups) | Disk space | 5.4 GB | 20 GB | 27% | 14.6 GB |
| Memory | RAM usage | 1.8 GB | 4 GB | 45% | 2.2 GB |
| Workflow throughput | Jobs/hour | 85 | 200 | 43% | 115 jobs/hr |
| API rate limits | Calls/hour | 450 | 1000 | 45% | 550 calls/hr |
| Concurrent users | Active sessions | 12 | 50 | 24% | 38 sessions |

**The 80% Rule:** Take action when any resource crosses 80% utilization. At 80%, you still have time to plan. At 95%, you are in emergency mode.

**Growth Projection Methods**

| Method | When to Use | Accuracy | Effort |
|---|---|---|---|
| Linear extrapolation | Stable, predictable growth | Medium | Low — extend the trend line |
| Seasonal modeling | Usage patterns repeat (monthly, quarterly) | High | Medium — need historical data |
| Event-based forecasting | Known future events (launches, migrations) | High | Medium — need event details |
| Capacity modeling | Complex interdependent resources | High | High — need system model |

**Linear extrapolation example:**

```text
Database Growth Projection
  │
  │  Current:  2.1 GB (March 2026)
  │  Growth:   +300 MB/month (observed over 4 months)
  │  Capacity: 10 GB
  │
  │  Month      Size     Utilization
  │  Mar 2026   2.1 GB   21%
  │  Jun 2026   3.0 GB   30%
  │  Sep 2026   3.9 GB   39%
  │  Dec 2026   4.8 GB   48%
  │  Mar 2027   5.7 GB   57%
  │  Jun 2027   6.6 GB   66%
  │  Sep 2027   7.5 GB   75%
  │  Dec 2027   8.4 GB   84%  ← 80% threshold crossed
  │
  │  Action needed by: Q4 2027 (20 months runway)
```

**Scaling Strategies**

| Strategy | Description | Cost | Disruption |
|---|---|---|---|
| Vertical scaling | Increase resource limits (more disk, more RAM) | Medium | Low — usually no downtime |
| Horizontal scaling | Add more instances behind a load balancer | High | Medium — requires architecture support |
| Optimization | Reduce resource consumption (cleanup, compression, caching) | Low | Low — can be done incrementally |
| Archival | Move old data to cheaper, slower storage | Low | Low — transparent if done correctly |
| Rate management | Throttle or queue low-priority work | None | Low — may affect non-critical features |

**Cost Optimization**

Capacity planning is also cost planning. Every resource has a cost, and over-provisioning is waste:

```text
Cost Efficiency = Value Delivered / Resources Consumed
```

Look for these optimization opportunities:

| Opportunity | Typical Savings | Effort |
|---|---|---|
| Delete unused data and logs | 10-30% storage reduction | Low |
| Compress backup archives | 40-60% backup storage reduction | Low |
| Cache frequently accessed data | 20-50% reduction in API calls | Medium |
| Optimize database queries | 30-70% reduction in query time | Medium |
| Archive historical data | 40-80% reduction in primary storage | Medium |

### Step-by-Step Approach

**Step 1: Collect current utilization data**

Get a snapshot of all resource usage:

```text
{{platform_config(action="get_status", scope="resources", metrics=["disk_usage", "memory_usage", "workflow_throughput", "api_call_rate", "active_sessions", "database_size"])}}
```

**Step 2: Analyze growth trends**

Review historical usage to determine growth rates:

```text
{{platform_config(action="get_trends", metrics=["database_size", "disk_usage", "workflow_count", "api_call_volume"], timeframe="90d", granularity="weekly")}}
```

**Step 3: Project future usage**

Calculate when each resource will hit its capacity threshold:

```text
{{platform_config(action="project_capacity", resources=[{"name": "database_storage", "current_gb": 2.1, "growth_rate_gb_month": 0.3, "capacity_gb": 10, "threshold_pct": 80}, {"name": "backup_storage", "current_gb": 5.4, "growth_rate_gb_month": 0.8, "capacity_gb": 20, "threshold_pct": 80}, {"name": "workflow_throughput", "current_per_hour": 85, "growth_rate_per_month": 10, "capacity_per_hour": 200, "threshold_pct": 80}, {"name": "api_rate_limit", "current_per_hour": 450, "growth_rate_per_month": 50, "capacity_per_hour": 1000, "threshold_pct": 80}])}}
```

**Step 4: Identify optimization opportunities**

Before scaling up, look for ways to reduce consumption:

```text
{{platform_config(action="analyze_optimization", targets=["database_cleanup", "log_rotation", "backup_compression", "cache_effectiveness", "query_performance"])}}
```

**Step 5: Build the capacity plan**

Combine projections and optimizations into an actionable plan:

```text
{{platform_config(action="create_capacity_plan", name="Q2-2026 Capacity Plan", items=[{"resource": "database_storage", "current_utilization": "21%", "projected_threshold_date": "2027-12-01", "action": "No immediate action; schedule review at 50% utilization", "priority": "low"}, {"resource": "backup_storage", "current_utilization": "27%", "projected_threshold_date": "2026-12-01", "action": "Enable compression (expected 50% reduction); implement retention cleanup", "priority": "medium"}, {"resource": "api_rate_limit", "current_utilization": "45%", "projected_threshold_date": "2027-03-01", "action": "Implement request caching for repeated queries; negotiate higher tier if growth continues", "priority": "medium"}, {"resource": "workflow_throughput", "current_utilization": "43%", "projected_threshold_date": "2027-06-01", "action": "Optimize slow workflow steps; evaluate parallel execution", "priority": "low"}])}}
```

**Step 6: Set up capacity monitoring**

Configure alerts to notify you when utilization approaches thresholds:

```text
{{platform_config(action="configure_alerts", rules=[{"name": "storage_80pct", "condition": "disk_usage > 80%", "severity": "warning", "channel": "admin_dashboard"}, {"name": "storage_90pct", "condition": "disk_usage > 90%", "severity": "critical", "channel": "admin_dashboard"}, {"name": "api_rate_70pct", "condition": "api_call_rate > 70% of limit", "severity": "warning", "channel": "admin_dashboard"}, {"name": "workflow_backlog", "condition": "workflow_queue_depth > 100", "severity": "warning", "channel": "admin_dashboard"}])}}
```

### Practice Exercise

**Scenario:** Your platform has been running for 4 months. The business is growing and plans to double its workflow volume in the next 6 months. Your manager asks: "Do we need to upgrade anything? What will it cost?"

**Task:** Build a capacity plan that answers the question.

1. Collect current resource utilization:

```text
{{platform_config(action="get_status", scope="resources")}}
```

1. Get the 90-day growth trend:

```text
{{platform_config(action="get_trends", metrics=["database_size", "workflow_count", "api_call_volume"], timeframe="90d")}}
```

1. Project forward 6 months with the planned doubling:

```text
{{platform_config(action="project_capacity", resources=[{"name": "workflow_throughput", "current_per_hour": 85, "growth_rate_per_month": 15, "capacity_per_hour": 200, "threshold_pct": 80}])}}
```

1. Identify what needs to change and estimate costs:

```text
{{platform_config(action="analyze_optimization", targets=["workflow_performance", "api_rate_limits", "storage_growth"])}}
```

**Self-check:** Your capacity plan should answer:

- Which resources will hit 80% utilization first, and when?
- What is the cost of doing nothing vs. the cost of scaling?
- Are there optimization opportunities that delay the need to scale?
- What is the timeline: when must decisions be made to avoid service impact?

If your plan does not have specific dates and numbers, it is not a plan. It is a guess.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Planning only for average load | Not accounting for peaks and spikes | Plan for peak load with 20% headroom above the highest expected spike |
| Ignoring compounding growth | Assuming linear growth when it is exponential | Plot growth curves; re-evaluate projections quarterly |
| Scaling before optimizing | Throwing resources at inefficiency | Always run optimization analysis before requesting additional resources |
| No cost analysis | Treating capacity as a technical problem only | Every capacity decision has a cost; present options with price tags |
| Planning once and never updating | Treating the plan as a one-time document | Review and update the capacity plan quarterly; growth rates change |
| Forgetting external dependencies | Planning for internal resources but not API rate limits | Include all constrained resources, internal and external, in projections |
