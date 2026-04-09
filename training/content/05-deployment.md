# Module 5: Deployment & Operations

> **Learning Path:** AI Solution Architect
> **Audience:** Non-technical business operators learning AI solution architecture
> **Prerequisites:** Completed Module 4: Implementation Excellence

---

## Lesson: CI/CD Pipeline Setup

### Why This Matters

Deploying AI solutions by hand -- copying files, running commands, crossing your fingers -- works exactly once. On the second deploy, you forget a step. On the third, you push broken code to production because you skipped the test. By the fifth, your client's system is down and you are debugging at midnight.

Continuous Integration and Continuous Deployment (CI/CD) is the practice of automating everything between "code is ready" and "code is running in production." It eliminates human error from the most error-prone phase of software delivery.

**What goes wrong without CI/CD:**

| Manual Step | What Goes Wrong | Business Impact |
|---|---|---|
| "I'll run the tests before deploying" | You forget once, ship a bug | Client-facing error, trust erosion |
| "I'll check the security scan later" | Later never comes | Vulnerability in production for weeks |
| "I'll deploy directly to production" | No staging validation | Breaking change hits real users |
| "I'll update the config by hand" | Wrong value in production | AI returns garbage, client notices first |

The goal is simple: make it impossible to deploy bad code. Every change must pass automated checks before it reaches any environment. No exceptions, no shortcuts.

**The cost of a production incident vs. the cost of CI/CD setup:**

```text
CI/CD Setup:           4-8 hours, one time
Production Incident:   2-8 hours to fix + client notification + trust damage
Break-even:            First prevented incident
```

### How to Think About It

**The Four Gates**

Every change to an AI project must pass through four automated gates before it reaches production. Think of these as security checkpoints -- each one catches a different category of problem.

```text
GATE MODEL

Code Change
    |
    v
GATE 1: LINT & FORMAT
    Does the code follow standards?
    Catches: syntax errors, style violations, import issues
    Speed: seconds
    |
    v
GATE 2: UNIT & INTEGRATION TESTS
    Does the code work correctly?
    Catches: broken logic, failed integrations, regression bugs
    Speed: 1-5 minutes
    |
    v
GATE 3: SECURITY SCAN
    Is the code safe to deploy?
    Catches: vulnerable dependencies, leaked secrets, unsafe patterns
    Speed: 1-3 minutes
    |
    v
GATE 4: AI QUALITY EVALUATION
    Do the AI outputs still meet quality bars?
    Catches: prompt regression, model behavior changes, quality drift
    Speed: 5-15 minutes
    |
    v
Ready to Deploy
```

**Gate Classification: Hard Block vs. Soft Block vs. Advisory**

Not every gate failure should stop a deploy. Use a tiered system:

```text
TIER 1 -- HARD BLOCK (deploy is stopped, no override)
  - Security scan finds critical vulnerability
  - Secrets detected in committed files
  - Unit tests fail
  - Integration tests fail

TIER 2 -- SOFT BLOCK (deploy paused, team lead can override)
  - AI quality evaluation drops below threshold
  - Performance test shows >20% latency increase
  - Non-critical dependency vulnerability

TIER 3 -- ADVISORY (deploy continues, warning logged)
  - Lint warnings (not errors)
  - AI quality evaluation within acceptable range but declining trend
  - Accessibility checks
```

**Environment Progression**

Code flows through environments in one direction. Never skip a stage.

```text
ENVIRONMENT FLOW

dev --> staging --> production

dev:
  Purpose: Build and test
  Data: Synthetic / sample data only
  Who sees it: Developers only
  Deploy trigger: Every commit to feature branch
  Validation: Gates 1-3

staging:
  Purpose: Validate before real users see it
  Data: Copy of production data (anonymized)
  Who sees it: Internal team, QA, client preview
  Deploy trigger: Merge to main branch
  Validation: Gates 1-4, plus manual review

production:
  Purpose: Real users, real data
  Data: Live production data
  Who sees it: Everyone
  Deploy trigger: Manual approval after staging validation
  Validation: All gates passed in staging, plus smoke test after deploy
```

**Deployment Strategies**

When code passes all gates and reaches production, how you roll it out matters:

```text
STRATEGY DECISION TREE

Q: How critical is zero-downtime?
  |
  |-- Not critical (internal tool, off-hours usage)
  |     --> Rolling deploy
  |     How: Replace instances one at a time
  |     Risk: Brief mixed-version period
  |     Rollback: Redeploy previous version
  |
  |-- Critical (customer-facing, 24/7)
  |     Q: Is the change high-risk?
  |       |
  |       |-- Low risk (config change, minor fix)
  |       |     --> Blue-green deploy
  |       |     How: Spin up new environment, switch traffic all at once
  |       |     Risk: Minimal (instant rollback by switching back)
  |       |     Rollback: Switch traffic back to old environment
  |       |
  |       |-- High risk (new model, major feature)
  |             --> Canary deploy
  |             How: Send 5% of traffic to new version, monitor, ramp up
  |             Risk: Only 5% of users affected if something breaks
  |             Rollback: Route 100% back to old version
```

### Step-by-Step Approach

**Step 1: Create the pipeline configuration**

```text
{{deployment_pipeline(
  action="create",
  project="acme-invoice-processor",
  pipeline_type="github_actions",
  environments=["dev", "staging", "production"],
  gates={
    "lint": {"tier": "hard_block", "stage": "all"},
    "unit_tests": {"tier": "hard_block", "stage": "all"},
    "integration_tests": {"tier": "hard_block", "stage": "all"},
    "security_scan": {"tier": "hard_block", "stage": "all"},
    "ai_quality_eval": {"tier": "soft_block", "stage": "staging"},
    "performance_test": {"tier": "soft_block", "stage": "staging"},
    "a11y_check": {"tier": "advisory", "stage": "staging"}
  }
)}}
```

This generates a GitHub Actions workflow YAML with all gates configured, environment progression rules, and approval requirements.

**Step 2: Configure the security scan**

```text
{{deployment_pipeline(
  action="configure_gate",
  project="acme-invoice-processor",
  gate="security_scan",
  config={
    "scan_dependencies": true,
    "scan_secrets": true,
    "scan_docker_image": true,
    "fail_on": "critical",
    "ignore_cves": [],
    "notify_on_warning": "team-lead@company.com"
  }
)}}
```

**Step 3: Configure the AI quality evaluation gate**

```text
{{deployment_pipeline(
  action="configure_gate",
  project="acme-invoice-processor",
  gate="ai_quality_eval",
  config={
    "eval_suite": "tests/eval/",
    "quality_threshold": 0.85,
    "regression_threshold": 0.05,
    "sample_size": 50,
    "timeout_minutes": 15,
    "compare_to": "last_passing_staging"
  }
)}}
```

**Step 4: Set up environment promotion rules**

```text
{{deployment_pipeline(
  action="configure_promotion",
  project="acme-invoice-processor",
  rules={
    "dev_to_staging": {
      "trigger": "merge_to_main",
      "required_gates": ["lint", "unit_tests", "integration_tests", "security_scan"],
      "auto_promote": true
    },
    "staging_to_production": {
      "trigger": "manual_approval",
      "required_gates": ["all_staging_gates_passed"],
      "approvers": ["team-lead"],
      "deploy_strategy": "blue_green",
      "post_deploy_smoke_test": true
    }
  }
)}}
```

**Step 5: Validate the pipeline**

```text
{{deployment_pipeline(
  action="validate",
  project="acme-invoice-processor",
  checks=["workflow_syntax", "gate_coverage", "environment_config", "approval_chain"]
)}}
```

### What Good Looks Like

**A properly configured CI/CD pipeline has these properties:**

- Every commit triggers at least lint and tests -- no code changes skip validation
- Security scan runs on every build, not just before production deploys
- AI quality evaluation uses a fixed test suite, not ad hoc spot checks
- Production deploys require explicit approval from a named person
- Rollback is a one-click operation, not a manual procedure
- The pipeline status is visible to the whole team (badge in repo, Slack notifications)

**Common mistakes to avoid:**

| Mistake | Risk | Fix |
|---|---|---|
| All gates as hard block | Team starts overriding everything | Use three tiers -- only truly critical issues hard-block |
| No AI quality gate | Prompt regression reaches production | Add eval suite that runs against fixed test cases |
| Skipping staging | "It worked in dev" is not validation | Always validate in a production-like environment first |
| Manual deploy steps | Steps get forgotten under pressure | Automate every step; if it cannot be automated, document it in the runbook |
| No rollback plan | Scramble to fix forward during an incident | Test rollback as part of your deploy process |
| Testing in production | Real users hit your bugs | Use staging with anonymized production data |

### Practice Exercise

Set up a CI/CD pipeline for one of your existing projects:

1. Run `{{deployment_pipeline(action="create", ...)}}` with three environments
2. Configure all four gates with appropriate tier levels
3. Set up environment promotion rules (auto for dev-to-staging, manual for staging-to-production)
4. Run `{{deployment_pipeline(action="validate", ...)}}` and fix any warnings
5. Make a small change and watch it flow through the pipeline
6. Deliberately introduce a failing test and confirm the pipeline blocks the deploy

**Success criteria:**

- Pipeline validation passes with zero errors
- A failing test prevents deployment to staging
- A security scan failure prevents deployment to any environment
- You can explain the difference between hard block, soft block, and advisory tiers
- You know how to roll back a production deploy in under 60 seconds

---

## Lesson: Docker Containerization

### Why This Matters

When you build an AI solution on your laptop, it works because your laptop has the right Python version, the right libraries, the right environment variables, and the right file paths. When you try to run it somewhere else -- a server, a colleague's machine, a cloud instance -- it breaks.

Docker solves this by packaging your application and everything it needs into a container: a self-contained unit that runs identically everywhere. For AI solutions, this is not optional. AI workloads have complex dependencies (model libraries, data processing tools, specific Python versions) that are nearly impossible to manage without containerization.

**What goes wrong without Docker:**

| Scenario | Symptom | Root Cause |
|---|---|---|
| "It works on my machine" | Fails in production | Different Python version, missing library |
| "The deploy took 20 minutes" | Slow iteration cycle | Installing all dependencies from scratch every time |
| "The server ran out of memory" | AI model crashes under load | No resource limits, model consumes everything |
| "Someone found our API key" | Security incident | Secrets baked into the container image |

Docker for AI solutions is about three things: **consistency** (same behavior everywhere), **security** (isolated, minimal attack surface), and **scalability** (run 1 or 100 copies of the same container).

### How to Think About It

**Multi-Stage Builds: Why They Matter**

A Docker build has two phases: building the application and running the application. Multi-stage builds keep these separate so your production image only contains what it needs to run.

```text
MULTI-STAGE BUILD MODEL

Stage 1: BUILD
  Base image: Full development image (Python + build tools)
  Actions: Install dependencies, compile code, run tests
  Size: 1.5 GB (includes compilers, dev tools, test frameworks)
  Kept? NO -- discarded after build

Stage 2: PRODUCTION
  Base image: Minimal runtime image (Python slim)
  Actions: Copy only built artifacts from Stage 1
  Size: 200 MB (runtime only, no build tools)
  Kept? YES -- this is what gets deployed

WHY THIS MATTERS:
  - Smaller image = faster deploys (200 MB vs 1.5 GB)
  - Fewer packages = smaller attack surface
  - No build tools in production = fewer vulnerabilities
```

**Security Practices Decision Checklist**

```text
DOCKER SECURITY CHECKLIST

[ ] Non-root user
    Why: If container is compromised, attacker has limited permissions
    How: Add USER directive in Dockerfile
    Skip if: Never (always use non-root)

[ ] Minimal base image
    Why: Fewer packages = fewer vulnerabilities
    How: Use python:3.11-slim instead of python:3.11
    Skip if: You need specific system libraries (then document why)

[ ] No secrets in image layers
    Why: Anyone with image access can extract secrets from any layer
    How: Pass secrets via environment variables at runtime
    Skip if: Never (this is a hard security rule)

[ ] Pinned dependency versions
    Why: Unpinned versions can change between builds, introducing bugs
    How: Use requirements.txt with exact versions (package==1.2.3)
    Skip if: Never (always pin versions)

[ ] Health check defined
    Why: Orchestrator needs to know if container is healthy
    How: HEALTHCHECK directive that hits your health endpoint
    Skip if: Standalone containers (not orchestrated)
```

**Resource Limits for AI Workloads**

AI workloads are resource-hungry. Without limits, a single container can consume all available CPU and memory, starving other services.

```text
RESOURCE SIZING GUIDE

Workload Type           CPU        Memory     Why
-------------------     -------    --------   --------------------------------
API Gateway             0.25 CPU   256 MB     Routes requests, minimal compute
Prompt Processing       0.5 CPU    512 MB     Text processing, API calls
Document Processing     1 CPU      1 GB       PDF parsing, image handling
Model Inference (API)   0.5 CPU    512 MB     Calling external model APIs
Model Inference (local) 2-4 CPU    4-8 GB     Running models locally
Queue Worker            0.5 CPU    512 MB     Background job processing
Database                1 CPU      2 GB       Data storage and retrieval

NOTE: These are starting points. Monitor actual usage and adjust.
      Always set limits -- an unlimited container is a crash waiting to happen.
```

**Compose Patterns for Multi-Service AI Solutions**

Most AI solutions are not a single container. They are multiple services working together.

```text
TYPICAL AI SOLUTION ARCHITECTURE

+------------------+     +------------------+     +------------------+
|   App Server     |---->|   Model Server   |---->|   Queue          |
|   (Flask/FastAPI)|     |   (AI API calls) |     |   (Redis/RabbitMQ)|
+------------------+     +------------------+     +------------------+
        |                                                  |
        v                                                  v
+------------------+                              +------------------+
|   Database       |                              |   Worker         |
|   (PostgreSQL)   |                              |   (Background)   |
+------------------+                              +------------------+

Services communicate over an internal Docker network.
Only the App Server is exposed to the outside world.
```

### Step-by-Step Approach

**Step 1: Generate the Dockerfile**

```text
{{docker_config(
  action="create",
  project="acme-invoice-processor",
  build_type="multi_stage",
  base_image="python:3.11-slim",
  config={
    "non_root_user": true,
    "health_check": "/health",
    "health_interval": "30s",
    "exposed_port": 8000,
    "entry_point": "gunicorn app:create_app() -b 0.0.0.0:8000"
  }
)}}
```

This generates a Dockerfile with a build stage and a production stage, non-root user, health check, and proper layering for cache efficiency.

**Step 2: Create the Docker Compose configuration**

```text
{{docker_config(
  action="create_compose",
  project="acme-invoice-processor",
  services=[
    {
      "name": "app",
      "build": "./",
      "ports": ["8000:8000"],
      "cpu_limit": "0.5",
      "memory_limit": "512m",
      "depends_on": ["db", "redis"],
      "env_file": ".env",
      "restart": "unless-stopped"
    },
    {
      "name": "worker",
      "build": "./",
      "command": "celery -A tasks worker --loglevel=info",
      "cpu_limit": "1.0",
      "memory_limit": "1g",
      "depends_on": ["redis"],
      "env_file": ".env",
      "restart": "unless-stopped"
    },
    {
      "name": "redis",
      "image": "redis:7-alpine",
      "cpu_limit": "0.25",
      "memory_limit": "256m",
      "restart": "unless-stopped"
    },
    {
      "name": "db",
      "image": "postgres:16-alpine",
      "cpu_limit": "0.5",
      "memory_limit": "512m",
      "volumes": ["pgdata:/var/lib/postgresql/data"],
      "env_file": ".env",
      "restart": "unless-stopped"
    }
  ]
)}}
```

**Step 3: Build and test locally**

```text
{{docker_config(
  action="build",
  project="acme-invoice-processor",
  target="production",
  tag="acme-invoice:latest",
  checks=["no_secrets_in_layers", "non_root_user", "health_check_defined"]
)}}
```

**Step 4: Run the security audit on the image**

```text
{{docker_config(
  action="audit",
  project="acme-invoice-processor",
  image="acme-invoice:latest",
  checks=["vulnerability_scan", "secret_scan", "user_check", "layer_size"]
)}}
```

**Step 5: Validate graceful shutdown**

```text
{{docker_config(
  action="test_shutdown",
  project="acme-invoice-processor",
  timeout_seconds=30,
  verify=["in_flight_requests_complete", "db_connections_closed", "no_data_loss"]
)}}
```

### What Good Looks Like

**A properly containerized AI solution has these properties:**

- Production image is under 500 MB (multi-stage build, slim base)
- Container runs as a non-root user
- No secrets exist in any image layer (use `docker history` to verify)
- All dependencies are pinned to exact versions
- Health check endpoint responds within 5 seconds
- Graceful shutdown completes in-flight requests before stopping
- Resource limits are set for every service in the compose file
- Services restart automatically after crashes (`restart: unless-stopped`)

**Common mistakes to avoid:**

| Mistake | Risk | Fix |
|---|---|---|
| Using full base image (python:3.11) | 900 MB image, slow deploys, more vulnerabilities | Use python:3.11-slim, install only what you need |
| Secrets in Dockerfile or image layers | Anyone with image access can extract them | Pass secrets as runtime environment variables only |
| No resource limits | One container starves others, cascading failure | Set CPU and memory limits for every service |
| Running as root | Container compromise = host compromise | Add USER directive, test that non-root works |
| No health check | Orchestrator cannot detect unhealthy containers | Add HEALTHCHECK that hits your /health endpoint |
| Copying entire project into image | Large image, dev files in production | Use .dockerignore to exclude tests, docs, .env, .git |

### Practice Exercise

Containerize an existing Agent Mahoo project:

1. Run `{{docker_config(action="create", ...)}}` with multi-stage build enabled
2. Generate a compose file with at least app + worker + database services
3. Build the image and verify it is under 500 MB
4. Run `{{docker_config(action="audit", ...)}}` and resolve any security findings
5. Start the compose stack and verify the health check passes
6. Test graceful shutdown: send a request, then stop the container, confirm the request completes

**Success criteria:**

- Image size is under 500 MB
- Security audit returns zero critical findings
- Container runs as non-root
- Health check passes within 5 seconds of startup
- Graceful shutdown completes without dropping in-flight requests
- You can start the entire multi-service stack with one command

---

## Lesson: Cloud Deployment

### Why This Matters

A containerized AI solution running on your laptop is a demo. A containerized AI solution running in the cloud, monitored, auto-scaling, and cost-optimized -- that is a product. The gap between the two is where most AI projects stall.

Cloud deployment for AI solutions is uniquely challenging because AI workloads have characteristics that traditional web apps do not:

- **Unpredictable latency** -- model API calls take 2-30 seconds, depending on prompt complexity and provider load
- **Bursty traffic** -- usage spikes at predictable times (Monday mornings, end of month) and unpredictable times (client demos)
- **High cost per request** -- each AI API call costs money, making cost-per-request a first-class metric alongside response time
- **Cold start sensitivity** -- containers that take 60 seconds to warm up cannot handle sudden traffic spikes

**What goes wrong without proper cloud deployment:**

| Shortcut | What Happens | Business Cost |
|---|---|---|
| No monitoring | Client reports errors before you know about them | Reactive firefighting, trust erosion |
| No auto-scaling | System falls over during traffic spikes | Downtime during client's busiest hours |
| No cost controls | Surprise cloud bill at end of month | Margin evaporates, project becomes unprofitable |
| Dev/prod mismatch | "Worked in dev" breaks in production | Hours of debugging environment differences |

### How to Think About It

**Environment Management: The Parity Principle**

Your development, staging, and production environments must be as similar as possible. Every difference is a place where bugs can hide.

```text
ENVIRONMENT PARITY MATRIX

Dimension          dev              staging           production
-----------        -----------      -----------       -----------
Infrastructure     Docker local     Cloud (small)     Cloud (full)
AI Provider        Same             Same              Same
API Keys           Dev keys         Staging keys      Production keys
Data               Synthetic        Anonymized copy   Real data
Domain             localhost        staging.app.com   app.client.com
Scaling            Single instance  Min 1, max 2      Min 2, max 10
Monitoring         Logs to console  Full monitoring    Full + alerting
Cost controls      None needed      Budget caps       Budget caps + alerts

RULE: If it differs between staging and production, document it and test it.
```

**Secrets Management Hierarchy**

```text
SECRETS MANAGEMENT DECISION TREE

Q: Where are your secrets stored?
  |
  |-- In .env files on the server
  |     --> RISKY: files can be read, copied, leaked
  |     Fix: Migrate to a secrets manager
  |
  |-- In environment variables on the host
  |     --> ACCEPTABLE for small deployments
  |     Risk: Visible in process listings, passed to child processes
  |
  |-- In a secrets manager (AWS SSM, GCP Secret Manager, Vault)
  |     --> BEST: encrypted at rest, audit logged, access controlled
  |     Use when: production environments, client data, team access
  |
  |-- In the container image or Dockerfile
  |     --> CRITICAL RISK: secrets are extractable from image layers
  |     Fix: Remove immediately, rotate all affected credentials
```

**Monitoring: The Four Pillars for AI Solutions**

Traditional monitoring watches CPU and memory. AI solutions need four additional pillars:

```text
PILLAR 1: RESPONSE TIME
  What to measure: End-to-end latency (request in to response out)
  Breakdown: Network + app processing + AI API call + post-processing
  Healthy: p50 < 3s, p95 < 10s, p99 < 30s
  Alert when: p95 exceeds 15s for 5 minutes

PILLAR 2: ERROR RATE
  What to measure: Percentage of requests returning errors
  Breakdown: Client errors (4xx) vs server errors (5xx) vs AI failures
  Healthy: < 1% error rate
  Alert when: > 2% for 5 minutes, or any spike > 10%

PILLAR 3: AI-SPECIFIC METRICS
  What to measure: Model latency, token usage, quality scores
  Breakdown: Per-model, per-prompt-template, per-use-case
  Healthy: Costs within budget, quality scores stable
  Alert when: Cost per request > 2x baseline, quality score drops > 10%

PILLAR 4: BUSINESS METRICS
  What to measure: Requests per user, feature usage, task completion rate
  Breakdown: By customer, by use case, by time of day
  Healthy: Steady or growing usage
  Alert when: Usage drops > 30% (possible quality issue or churn signal)
```

**Scaling Strategies for AI Workloads**

```text
SCALING STRATEGY SELECTION

Workload Pattern         Strategy              Why
--------------------     -----------------     ----------------------------
Steady, predictable      Fixed instance count   Simple, predictable cost
Bursty, predictable      Scheduled scaling      Scale up before known peaks
Bursty, unpredictable    Auto-scale on CPU/req  React to actual demand
Queue-based processing   Queue-depth scaling    Scale workers based on backlog
Cost-sensitive           Spot/preemptible       60-80% cheaper, can be interrupted

COLD START MITIGATION:
  Problem: New containers take 30-60s to warm up
  Solutions:
    - Keep minimum 2 instances running (never scale to zero in production)
    - Pre-warm containers with a health check request on startup
    - Use smaller base images for faster container start
    - Keep model connections alive with connection pooling
```

**Cost Optimization Framework**

```text
COST OPTIMIZATION DECISION TREE

Step 1: Measure current cost per request
  {{cloud_deploy(action="cost_report", project="...", period="last_30_days")}}

Step 2: Identify top cost drivers
  Usually: AI API calls (60-80%), compute (10-20%), storage (5-10%)

Step 3: Optimize by category

  AI API Costs:
    - Cache identical requests (save 20-40%)
    - Use cheaper models for simple tasks (save 50-70% on those tasks)
    - Reduce token usage with shorter prompts (save 10-30%)
    - Batch requests where possible (reduce overhead)

  Compute Costs:
    - Right-size instances (most are over-provisioned by 2-3x)
    - Use reserved instances for steady base load (save 30-50%)
    - Use spot instances for background workers (save 60-80%)
    - Scale down during off-hours (save 30-50%)

  Storage Costs:
    - Archive old logs after 30 days (move to cold storage)
    - Clean up unused container images
    - Compress data at rest
```

### Step-by-Step Approach

**Step 1: Configure the cloud deployment**

```text
{{cloud_deploy(
  action="create",
  project="acme-invoice-processor",
  provider="aws",
  environments={
    "staging": {
      "instance_type": "t3.medium",
      "min_instances": 1,
      "max_instances": 2,
      "region": "us-east-1"
    },
    "production": {
      "instance_type": "t3.large",
      "min_instances": 2,
      "max_instances": 10,
      "region": "us-east-1"
    }
  }
)}}
```

**Step 2: Configure secrets management**

```text
{{cloud_deploy(
  action="configure_secrets",
  project="acme-invoice-processor",
  environment="production",
  secrets_manager="aws_ssm",  # pragma: allowlist secret
  secrets=[
    {"name": "ANTHROPIC_API_KEY", "source": "ssm_parameter", "path": "/prod/acme/anthropic_key"},
    {"name": "DATABASE_URL", "source": "ssm_parameter", "path": "/prod/acme/database_url"},
    {"name": "CLIENT_API_KEY", "source": "ssm_parameter", "path": "/prod/acme/client_api_key"}
  ]
)}}
```

**Step 3: Set up monitoring and alerting**

```text
{{cloud_deploy(
  action="configure_monitoring",
  project="acme-invoice-processor",
  environment="production",
  dashboards=["performance", "errors", "ai_metrics", "cost"],
  alerts=[
    {"metric": "p95_latency", "threshold": "15s", "duration": "5m", "notify": "ops-team"},
    {"metric": "error_rate", "threshold": "2%", "duration": "5m", "notify": "ops-team"},
    {"metric": "ai_cost_per_request", "threshold": "0.15", "duration": "1h", "notify": "team-lead"},
    {"metric": "daily_spend", "threshold": "50.00", "duration": "1d", "notify": "team-lead"}
  ]
)}}
```

**Step 4: Configure auto-scaling**

```text
{{cloud_deploy(
  action="configure_scaling",
  project="acme-invoice-processor",
  environment="production",
  scaling_rules={
    "scale_up": {
      "metric": "cpu_utilization",
      "threshold": "70%",
      "duration": "3m",
      "action": "add_1_instance",
      "cooldown": "5m"
    },
    "scale_down": {
      "metric": "cpu_utilization",
      "threshold": "30%",
      "duration": "10m",
      "action": "remove_1_instance",
      "cooldown": "10m",
      "min_instances": 2
    },
    "schedule": [
      {"cron": "0 8 * * MON", "min_instances": 4, "note": "Monday morning spike"},
      {"cron": "0 20 * * *", "min_instances": 2, "note": "Evening scale-down"}
    ]
  }
)}}
```

**Step 5: Deploy and validate**

```text
{{cloud_deploy(
  action="deploy",
  project="acme-invoice-processor",
  environment="staging",
  strategy="blue_green",
  post_deploy_checks=["health_check", "smoke_test", "monitoring_active"]
)}}
```

**Step 6: Run a cost optimization review**

```text
{{cloud_deploy(
  action="cost_report",
  project="acme-invoice-processor",
  period="last_30_days",
  breakdown=["ai_api", "compute", "storage", "network"],
  recommendations=true
)}}
```

### What Good Looks Like

**A properly deployed cloud AI solution has these properties:**

- All environments use the same Docker image, differing only in configuration and scale
- Secrets are managed through a secrets manager, not environment files on disk
- Monitoring dashboards show all four pillars (response time, error rate, AI metrics, business metrics)
- Alerts fire before clients notice problems (proactive, not reactive)
- Auto-scaling handles traffic spikes without manual intervention
- Minimum two instances in production (one can fail without downtime)
- Cost per request is tracked and stays within budget
- Monthly cost review identifies optimization opportunities

**Common mistakes to avoid:**

| Mistake | Risk | Fix |
|---|---|---|
| No monitoring until something breaks | Reactive firefighting, client reports issues first | Set up monitoring before the first production deploy |
| Scaling to zero in production | Cold start when first request comes in, user waits 60s | Always keep minimum 2 instances running |
| Same API keys for all environments | Dev testing burns production rate limits | Separate keys per environment |
| No cost alerts | Surprise $2,000 bill | Set daily and monthly spend alerts |
| Over-provisioning "just in case" | Paying 3x what you need | Start small, monitor, right-size after 2 weeks of data |
| No scaling cooldown | Thrashing: scale up, down, up, down | Set cooldown periods of 5-10 minutes |

### Practice Exercise

Deploy one of your containerized projects to the cloud:

1. Run `{{cloud_deploy(action="create", ...)}}` with staging and production environments
2. Configure secrets management (move at least 3 secrets to the secrets manager)
3. Set up monitoring with dashboards for all four pillars
4. Configure at least 3 alert rules (latency, error rate, cost)
5. Configure auto-scaling with both reactive (CPU-based) and scheduled rules
6. Deploy to staging, verify monitoring is active, then promote to production
7. Run `{{cloud_deploy(action="cost_report", ...)}}` and identify one optimization

**Success criteria:**

- Staging and production are running with separate secrets and scaling configs
- All four monitoring pillars have dashboards and alerts
- Auto-scaling responds to load changes within 5 minutes
- Cost per request is known and tracked
- You can answer: "What is the monthly run cost of this solution?" without checking the cloud console
- Rollback from production takes under 2 minutes
