# Module 4: Implementation Excellence

> **Learning Path:** AI Solution Architect
> **Audience:** Non-technical business operators learning AI solution architecture
> **Prerequisites:** Completed Module 3: Sales & ROI

---

## Lesson: Project Setup

### Why This Matters

The first 30 minutes of building an AI project determine whether the next 30 days are organized or chaotic. A poorly set up project leads to:

- **Lost configuration** — API keys hardcoded in files, accidentally shared, or overwritten during updates
- **Inconsistent structure** — Every project organized differently, making it impossible to onboard help or revisit old work
- **Environment confusion** — Code that works in testing breaks in production because configuration differs and nobody documented which is which
- **Rework from scratch** — A project without scaffolding accumulates technical debt so fast that it is often cheaper to start over than to fix it

The difference between amateur and professional AI delivery is not the AI itself. It is the project structure around the AI. Templates and scaffolding exist so you spend your time on the hard problems (prompt quality, workflow design, integration) instead of reinventing folder structures.

**The cost of skipping proper setup:**

| Shortcut Taken | Consequence at Week 2 | Consequence at Week 8 |
|---|---|---|
| No template used | "Where does this file go?" | "Nobody can find anything" |
| Secrets in config files | Works fine locally | API key leaked in a screen share |
| No environment separation | Testing on live data | Accidentally emailed 500 real customers from a test |
| No .gitignore / .env pattern | Credentials committed to repo | Security incident, key rotation, client notified |

### How to Think About It

**Template Selection Framework**

Agent Jumbo provides scaffold templates for common project types. Choosing the right one saves days of setup.

```text
TEMPLATE SELECTION DECISION TREE

Q1: What is the primary function of this AI solution?
  |
  |-- Autonomous agent (makes decisions, takes actions)
  |     --> template: "ai_agent"
  |     Use when: Automated workflows, multi-step processes,
  |               tool-using agents, scheduled tasks
  |     Examples: Invoice processor, email triager, report generator
  |
  |-- Conversational interface (talks to humans)
  |     --> template: "chatbot"
  |     Use when: Customer-facing chat, internal Q&A,
  |               guided workflows, support bots
  |     Examples: Customer service bot, onboarding assistant
  |
  |-- Data pipeline (processes information)
  |     --> template: "data_pipeline"
  |     Use when: ETL processes, data transformation,
  |               document processing, batch operations
  |     Examples: Document ingestion, data migration, analytics prep
  |
  |-- API service (receives requests, returns responses)
  |     --> template: "api_service"
  |     Use when: Other systems call your AI,
  |               webhook receivers, integrations
  |     Examples: AI-powered API endpoint, Slack bot backend
  |
  |-- Hybrid (multiple of the above)
  |     --> template: "ai_agent" (most flexible)
  |     Then add components from other templates as needed
```

**Standard Directory Structure for AI Projects**

Regardless of template, every AI project follows this structure:

```text
project-name/
  |-- config/
  |     |-- settings.yaml        # Non-secret configuration
  |     |-- prompts/             # All prompt templates (versioned)
  |     |     |-- v1/
  |     |     |-- v2/
  |     |-- .env.example         # Template for environment variables
  |
  |-- workflows/
  |     |-- main_workflow.yaml   # Primary automation workflow
  |     |-- fallback.yaml        # Degradation / error handling workflow
  |
  |-- integrations/
  |     |-- crm.yaml             # CRM connection config
  |     |-- email.yaml           # Email service config
  |
  |-- data/
  |     |-- templates/           # Document templates, output formats
  |     |-- sample/              # Test data for development
  |
  |-- tests/
  |     |-- unit/                # Deterministic logic tests
  |     |-- eval/                # AI output quality evaluations
  |
  |-- docs/
  |     |-- runbook.md           # How to operate the system
  |     |-- decision-log.md      # Why decisions were made
  |
  |-- .env                       # NEVER committed -- secrets live here
  |-- .gitignore                 # Excludes .env, data/, local configs
```

**Configuration Management: The Three Layers**

```text
LAYER 1: SECRETS (API keys, passwords, tokens)
  Where: .env file (never committed to version control)
  Managed by: Environment variables
  Rule: If it would be a security incident when leaked, it is a secret
  Examples: ANTHROPIC_API_KEY, DATABASE_PASSWORD, CLIENT_API_TOKEN

LAYER 2: ENVIRONMENT-SPECIFIC SETTINGS (URLs, feature flags, thresholds)
  Where: config/settings.yaml with environment overrides
  Managed by: Configuration files, different per environment
  Rule: If it changes between dev/staging/production, it is a setting
  Examples: API_BASE_URL, MAX_RETRIES, BATCH_SIZE, FEATURE_FLAG_NEW_UI

LAYER 3: APPLICATION LOGIC (prompt templates, workflow definitions)
  Where: config/prompts/, workflows/
  Managed by: Version control (committed, tracked, reviewed)
  Rule: If it defines what the AI does, it is logic
  Examples: Prompt templates, workflow YAML, routing rules
```

### Step-by-Step Approach

**Step 1: Create the project scaffold**

```text
{{project_scaffold(
  action="create",
  template="ai_agent",
  name="acme-invoice-processor",
  customer_id="acme-corp",
  description="Automated invoice processing with human review for exceptions"
)}}
```

This generates the full directory structure, starter configuration files, and a `.env.example` with all required variables listed.

**Step 2: Configure environment variables**

```text
{{project_scaffold(
  action="configure_env",
  project="acme-invoice-processor",
  variables=[
    {"name": "ANTHROPIC_API_KEY", "source": "vault", "required": true},
    {"name": "ACME_CRM_API_KEY", "source": "client_provided", "required": true},
    {"name": "ACME_CRM_BASE_URL", "source": "config", "value": "https://api.acmecrm.com/v2"},
    {"name": "ENVIRONMENT", "source": "config", "value": "development"},
    {"name": "LOG_LEVEL", "source": "config", "value": "info"}
  ]
)}}
```

**Step 3: Set up prompt versioning**

```text
{{project_scaffold(
  action="init_prompts",
  project="acme-invoice-processor",
  prompts=[
    {
      "name": "invoice_extractor",
      "version": "v1",
      "description": "Extracts line items, totals, and vendor info from invoice images"
    },
    {
      "name": "exception_classifier",
      "version": "v1",
      "description": "Classifies invoices as auto-approve, review, or reject"
    }
  ]
)}}
```

**Step 4: Configure the integration connections**

```text
{{project_scaffold(
  action="add_integration",
  project="acme-invoice-processor",
  integrations=[
    {
      "name": "acme_crm",
      "type": "rest_api",
      "auth": "api_key",
      "config_file": "integrations/crm.yaml"
    },
    {
      "name": "email_notifications",
      "type": "smtp",
      "auth": "credentials",
      "config_file": "integrations/email.yaml"
    }
  ]
)}}
```

**Step 5: Verify the setup**

```text
{{project_scaffold(
  action="validate",
  project="acme-invoice-processor",
  checks=["structure", "env_vars", "integrations", "gitignore"]
)}}
```

This runs a validation that confirms: all required directories exist, all environment variables are defined (even if not yet populated), no secrets are committed, and `.gitignore` covers sensitive files.

### What Good Looks Like

**A properly set up project has these properties:**

- Running `validate` returns zero warnings
- A new team member can read `.env.example` and know exactly what credentials to obtain
- Secrets are never in configuration files, YAML, or version control
- Prompts are in their own versioned directory (not hardcoded in workflow definitions)
- There is a clear separation between dev, staging, and production configuration
- The `docs/runbook.md` file explains how to start, stop, and troubleshoot the system
- Test data exists in `data/sample/` so development never touches live client data

**Common mistakes to avoid:**

| Mistake | Risk | Fix |
|---|---|---|
| Skipping the template, building from scratch | Inconsistent structure, missing files | Always start with `project_scaffold` even for simple projects |
| Putting API keys in settings.yaml | Keys committed to version control | Secrets in `.env` only, referenced via environment variables |
| One prompt file for everything | Cannot version or test prompts independently | One file per prompt, organized in version directories |
| No .env.example file | New team members do not know what credentials are needed | Template auto-generates this; keep it updated |
| Testing against production data | Accidental customer-facing errors | Use `data/sample/` for all development; flag prod access as explicit |
| No runbook | You are the only person who can operate the system | Write the runbook during setup, not after launch |

### Practice Exercise

Set up a complete project from scratch:

1. Choose a template that matches your most recent solution design
2. Run `{{project_scaffold(action="create", ...)}}` with a descriptive name
3. Configure at least 3 environment variables (1 secret, 2 settings)
4. Create version 1 of at least 2 prompt templates
5. Add one integration connection
6. Run `{{project_scaffold(action="validate", ...)}}` and resolve any warnings
7. Verify: is there a `.env.example` that lists all required variables? Is `.env` in the `.gitignore`?

**Success criteria:**

- Validation passes with zero warnings
- You can explain what every directory is for
- No secrets exist in any committed file
- A colleague could set up their own environment using only `.env.example` and the runbook

---

## Lesson: AI Model Integration

### Why This Matters

Choosing and integrating the right AI model is not a technical decision. It is a business decision with direct impact on cost, quality, reliability, and client satisfaction. Get it wrong and you face:

- **Cost blowouts** — Using a premium model for simple tasks can 10x your API costs with no quality improvement
- **Quality failures** — Using a cheap model for complex reasoning produces outputs that damage client trust
- **Single point of failure** — One provider goes down and your entire client solution stops working
- **Privacy violations** — Sending sensitive client data to a cloud model when the contract requires on-premises processing

**The model integration decision is really four decisions:**

| Decision | Wrong Choice | Consequence |
|---|---|---|
| Which provider | Reasoning task on a breadth model | Shallow, unreliable outputs |
| Which tier | GPT-4 class for simple classification | 10x cost, same result as a smaller model |
| What fallback | No fallback strategy | Complete outage when provider has issues |
| What controls | No token budgets or caching | Surprise $2,000 API bill in month 1 |

### How to Think About It

**Provider Selection Framework**

Different AI providers excel at different types of tasks. This is not about brand preference -- it is about matching capability to requirement.

```text
PROVIDER SELECTION MATRIX

Task Type              Best Fit           Why                     Alternative
--------------------   ----------------   --------------------    ----------------
Complex reasoning      Claude             Deep analysis,          GPT-4 class
                                          nuanced judgment
Broad general tasks    GPT-4 class        Wide training data,     Claude
                                          good at everything
Simple classification  Smaller models     Fast, cheap, good       GPT-3.5 class
                       (Haiku, GPT-3.5)   enough for simple
                                          tasks
Privacy-sensitive      Local models       Data never leaves       On-prem deployment
                       (Llama, Mistral)   the client's network    of any open model
Creative content       Claude / GPT-4     Strong writing          Depends on style
                                          quality
Code generation        Claude / GPT-4     Accurate, tested        Specialized code
                                          code output             models
High-volume, low-      Smallest viable    Cost scales with        Batch API pricing
complexity             model              volume
```

**The Model Routing Strategy**

Do not use one model for everything. Route tasks to the appropriate model based on complexity and cost sensitivity.

```text
MODEL ROUTING DECISION TREE

START: What is the task complexity?
  |
  |-- HIGH (reasoning, analysis, multi-step logic)
  |     --> Primary: Claude Sonnet / Opus class
  |     --> Cost: $3-15 per 1M tokens
  |     --> Use for: Solution design, complex extraction, judgment calls
  |
  |-- MEDIUM (structured output, summarization, drafting)
  |     --> Primary: Claude Haiku / GPT-4 Mini class
  |     --> Cost: $0.25-1 per 1M tokens
  |     --> Use for: Report generation, email drafting, data formatting
  |
  |-- LOW (classification, routing, simple extraction)
  |     --> Primary: Smallest viable model
  |     --> Cost: $0.05-0.25 per 1M tokens
  |     --> Use for: Intent detection, category assignment, yes/no decisions

COST IMPACT EXAMPLE (10,000 tasks/month):

All tasks on premium model:    $45,000/year
Routed by complexity:          $8,200/year
Savings:                       $36,800/year (82% reduction)
```

**Prompt Management Lifecycle**

Prompts are code. They must be versioned, tested, and deployed with the same discipline as any other business logic.

```text
PROMPT LIFECYCLE

1. DRAFT    --> Write the prompt, test manually with 5 examples
2. TEST     --> Run against 50+ examples, measure quality metrics
3. BASELINE --> Record quality scores as the benchmark
4. DEPLOY   --> Push to production with version tag (v1.0)
5. MONITOR  --> Track quality metrics in production
6. ITERATE  --> When quality drifts or requirements change:
                 - Create new version (v1.1)
                 - Test against same evaluation set
                 - Compare to baseline
                 - Deploy only if metrics improve or hold
                 - Keep previous version available for rollback

VERSION NAMING:
  v1.0 --> Initial production version
  v1.1 --> Minor refinement (same structure, better instructions)
  v2.0 --> Major rewrite (different approach or structure)
```

**Fallback Strategy: The Degradation Ladder**

Every AI integration must have a plan for when things go wrong. The ladder has four rungs:

```text
DEGRADATION LADDER

Level 1: PRIMARY MODEL
  Status: Working normally
  Action: Use the configured primary model
  User experience: Full quality, normal speed

Level 2: SECONDARY MODEL (different provider)
  Trigger: Primary model returns errors or latency > threshold
  Action: Route to backup provider
  User experience: Slightly different output style, still functional
  Setup: Pre-configure a secondary provider with equivalent prompts

Level 3: CACHED RESPONSE
  Trigger: Both primary and secondary fail
  Action: Return a cached/templated response for common queries
  User experience: Generic but correct response
  Setup: Pre-build response templates for top 20 request types

Level 4: GRACEFUL DEGRADATION
  Trigger: All automated options exhausted
  Action: Queue for human processing, notify the operator
  User experience: "We have received your request and a team
                    member will respond within [SLA]"
  Setup: Configure notification channel and human queue
```

### Step-by-Step Approach

**Step 1: Configure the primary model**

```text
{{model_config(
  action="set_primary",
  project="acme-invoice-processor",
  provider="anthropic",
  model="claude-sonnet",
  use_case="invoice_extraction",
  max_tokens=2000,
  temperature=0.1
)}}
```

**Step 2: Set up model routing rules**

```text
{{model_config(
  action="set_routing",
  project="acme-invoice-processor",
  rules=[
    {
      "task": "invoice_extraction",
      "complexity": "high",
      "model": "claude-sonnet",
      "reason": "Complex document understanding with variable formats"
    },
    {
      "task": "exception_classification",
      "complexity": "low",
      "model": "claude-haiku",
      "reason": "Binary classification, high volume, low complexity"
    },
    {
      "task": "notification_drafting",
      "complexity": "medium",
      "model": "claude-haiku",
      "reason": "Templated content generation, moderate quality bar"
    }
  ]
)}}
```

**Step 3: Configure fallback chain**

```text
{{model_config(
  action="set_fallback",
  project="acme-invoice-processor",
  chain=[
    {"level": 1, "provider": "anthropic", "model": "claude-sonnet"},
    {"level": 2, "provider": "openai", "model": "gpt-4o"},
    {"level": 3, "action": "use_cache", "cache_ttl_hours": 24},
    {"level": 4, "action": "queue_human", "notify": "ops-channel", "sla_minutes": 60}
  ]
)}}
```

**Step 4: Set cost controls**

```text
{{model_config(
  action="set_budget",
  project="acme-invoice-processor",
  monthly_budget_usd=500,
  alert_threshold_percent=80,
  hard_limit=true,
  per_request_max_tokens=4000,
  cache_identical_requests=true,
  cache_ttl_minutes=30
)}}
```

**Step 5: Deploy and version the prompt**

```text
{{prompt_manager(
  action="deploy",
  project="acme-invoice-processor",
  prompt="invoice_extractor",
  version="v1",
  target="production",
  rollback_version="none"
)}}
```

### What Good Looks Like

**A well-integrated AI model setup has these properties:**

- Tasks are routed to the cheapest model that meets quality requirements (not the most expensive by default)
- Every model call has a fallback chain of at least 3 levels
- Token budgets are set with hard limits and alerts at 80%
- Prompts are versioned and can be rolled back in under 5 minutes
- Caching is enabled for identical or near-identical requests
- Privacy-sensitive tasks are routed to appropriate models (local if required by contract)
- Cost projections are documented and reviewed monthly

**Common mistakes to avoid:**

| Mistake | Consequence | Fix |
|---|---|---|
| One model for all tasks | 5-10x cost overrun | Route by complexity; use cheap models for simple tasks |
| No fallback provider | Total outage during provider incidents | Always configure at least a secondary provider |
| Prompts hardcoded in workflows | Cannot version, test, or rollback | Store prompts in `config/prompts/` with version directories |
| No token budget | Surprise API bill from a loop or unexpected volume | Set monthly hard limits before going live |
| Ignoring caching | Paying full price for repeated identical requests | Cache responses for at least 15-30 minutes |
| Using cloud models for sensitive data | Privacy/compliance violation | Audit data sensitivity per task; use local models where required |

### Practice Exercise

Set up a complete model integration for a test project:

1. Choose 3 tasks from your solution design with different complexity levels
2. Assign each task to an appropriate model using the routing framework
3. Configure a 4-level fallback chain
4. Set a monthly budget with an 80% alert threshold
5. Deploy version 1 of a prompt and verify it is tagged and rollback-ready
6. Calculate: what would your monthly cost be at full volume? What would it be if you used the premium model for everything?

**Success criteria:**

- Each task uses the cheapest model that meets its quality bar
- Fallback chain covers all 4 levels (primary, secondary, cache, human)
- Monthly budget is set and alerting is configured
- Cost estimate for routed model selection is at least 50% lower than using one premium model for everything

---

## Lesson: Testing AI Solutions

### Why This Matters

AI solutions are uniquely difficult to test because they are not deterministic. Ask the same question twice and you may get two different answers -- both correct, or one correct and one subtly wrong. Traditional testing ("did the function return 42?") is necessary but not sufficient.

What goes wrong without AI-specific testing:

- **Silent quality degradation** — The system works fine for weeks, then a model update changes output quality. Nobody notices until a client complains.
- **False confidence from passing tests** — Unit tests pass, but the AI outputs are mediocre. The logic is correct; the intelligence is not.
- **No regression detection** — You improve one prompt and unknowingly break another. Without evaluation baselines, you cannot detect this.
- **Untested edge cases at scale** — The AI handles the common 90% well. The uncommon 10% produces embarrassing results that find their way to screenshots on social media.

**Testing traditional software vs. testing AI solutions:**

| Aspect | Traditional Software | AI Solution |
|---|---|---|
| Expected output | Exactly one correct answer | Range of acceptable answers |
| Repeatability | Same input, same output, every time | Same input, different output possible |
| Pass/fail criteria | Binary (correct or wrong) | Gradient (quality score 1-5) |
| Regression cause | Code change | Code change, model update, prompt drift, data shift |
| Test volume needed | Dozens of test cases | Hundreds of evaluation cases |

### How to Think About It

**The AI Testing Pyramid**

Like the traditional testing pyramid, AI testing has layers. Each layer catches different types of problems. You need all of them.

```text
AI TESTING PYRAMID

                    /\
                   /  \
                  / HR \        HUMAN REVIEW (top)
                 /------\       Frequency: Monthly or on major changes
                /  EVAL  \      What: Humans rate AI output quality
               /----------\     Catches: Subtle quality issues, tone,
              / INTEGRATION \   appropriateness, brand alignment
             /--------------\
            /     UNIT       \  EVALUATION FRAMEWORK (middle-upper)
           /------------------\ Frequency: Every prompt change
                                What: Automated quality scoring against
                                labeled examples
                                Catches: Quality regressions, prompt
                                degradation, model update impact

                                INTEGRATION TESTS (middle-lower)
                                Frequency: Every deployment
                                What: End-to-end workflow execution
                                with test data
                                Catches: Broken connections, format
                                changes, timeout issues

                                UNIT TESTS (base)
                                Frequency: Every code change
                                What: Deterministic logic tests
                                (parsing, routing, formatting)
                                Catches: Code bugs, logic errors,
                                edge cases in non-AI components
```

**What to Test at Each Layer**

```text
UNIT TESTS (deterministic -- same input, same output)
  Test:
  - Input parsing and validation
  - Output formatting and transformation
  - Routing logic (which model, which prompt)
  - Error handling (what happens with bad input)
  - Configuration loading
  Do NOT test:
  - AI output content (that is for eval)
  - Prompt quality (that is for eval)

INTEGRATION TESTS (end-to-end flow with test data)
  Test:
  - Full workflow execution start to finish
  - API connections return expected format
  - Data flows correctly between steps
  - Timeout handling works
  - Retry logic activates on transient failures
  Do NOT test:
  - Whether the AI's answer is "good" (that is for eval)

EVALUATION FRAMEWORK (AI output quality scoring)
  Test:
  - Accuracy: Does the output contain correct information?
  - Relevance: Does the output address the actual question?
  - Completeness: Are all required elements present?
  - Safety: Does the output avoid harmful content?
  - Consistency: Do similar inputs produce similar quality outputs?
  - Format compliance: Does the output match the required structure?

  Method:
    1. Create a labeled evaluation set (50-200 examples)
    2. Each example has: input, expected output traits, quality rubric
    3. Run all examples through the current prompt
    4. Score each output against the rubric (automated + sampled human)
    5. Record aggregate scores as the baseline
    6. Re-run after any change; compare to baseline

HUMAN REVIEW (judgment and brand alignment)
  Test:
  - Would you be comfortable if the client saw this output?
  - Does the tone match the brand?
  - Are edge cases handled gracefully?
  - Would a domain expert find errors?
  Method:
    1. Sample 20-30 production outputs monthly
    2. Rate each on a 1-5 scale for quality, tone, accuracy
    3. Flag any output scoring below 3 for prompt review
    4. Track trends over time
```

**Evaluation Metrics Framework**

Define these metrics for every AI task in your solution:

| Metric | How to Measure | Acceptable Range | Action if Below |
|---|---|---|---|
| Accuracy | % of outputs with correct core information | > 95% for facts, > 85% for judgment | Review prompt, add examples |
| Relevance | % of outputs that address the actual request | > 90% | Improve prompt specificity |
| Safety | % of outputs free from harmful or inappropriate content | 100% (zero tolerance) | Immediate prompt revision |
| Consistency | Standard deviation of quality scores | < 0.8 on 5-point scale | Add constraints to prompt |
| Format compliance | % of outputs matching required structure | > 98% | Add format examples to prompt |
| Latency | Time from request to response | < SLA threshold | Optimize prompt length, consider faster model |

**Regression Detection**

```text
REGRESSION DETECTION PROCESS

1. ESTABLISH BASELINE
   Run evaluation set against current production prompt
   Record: accuracy, relevance, safety, consistency, format scores
   This is your quality floor

2. SET ALERT THRESHOLDS
   Warning: any metric drops > 5% from baseline
   Critical: any metric drops > 10% from baseline
   Emergency: safety score drops below 100%

3. TRIGGER EVALUATION ON
   - Any prompt change (before deployment)
   - Model version updates (when provider releases new version)
   - Monthly scheduled evaluation (catch gradual drift)
   - Client complaint or quality report

4. COMPARE AND DECIDE
   New scores >= baseline  --> Deploy / continue
   New scores within 5%   --> Investigate, likely acceptable
   New scores > 5% below  --> Do not deploy, revise prompt
   Safety below 100%      --> Immediate rollback, investigate
```

### Step-by-Step Approach

**Step 1: Create the evaluation set**

```text
{{test_framework(
  action="create_eval_set",
  project="acme-invoice-processor",
  task="invoice_extraction",
  examples=[
    {
      "input": "sample_invoice_standard.pdf",
      "expected_traits": ["vendor_name_correct", "total_correct", "line_items_complete"],
      "rubric": {"accuracy": 5, "format": 5, "completeness": 5}
    },
    {
      "input": "sample_invoice_handwritten.pdf",
      "expected_traits": ["vendor_name_correct", "total_correct", "flags_low_confidence"],
      "rubric": {"accuracy": 4, "format": 5, "completeness": 4}
    }
  ],
  target_count=50
)}}
```

Build at least 50 examples covering: common cases (60%), edge cases (25%), and adversarial cases (15%).

**Step 2: Run the baseline evaluation**

```text
{{test_framework(
  action="run_eval",
  project="acme-invoice-processor",
  task="invoice_extraction",
  prompt_version="v1",
  eval_set="invoice_extraction_eval_v1",
  save_as_baseline=true
)}}
```

**Step 3: Set up regression alerts**

```text
{{test_framework(
  action="set_alerts",
  project="acme-invoice-processor",
  baseline="invoice_extraction_baseline_v1",
  thresholds={
    "warning_drop_percent": 5,
    "critical_drop_percent": 10,
    "safety_minimum": 1.0,
    "notify": "ops-channel"
  }
)}}
```

**Step 4: Create unit tests for deterministic components**

```text
{{test_framework(
  action="create_unit_tests",
  project="acme-invoice-processor",
  tests=[
    {
      "name": "test_invoice_parser_extracts_total",
      "component": "invoice_parser",
      "input": {"raw_text": "Total: $1,234.56"},
      "expected": {"total": 1234.56}
    },
    {
      "name": "test_routing_sends_complex_to_sonnet",
      "component": "model_router",
      "input": {"task": "invoice_extraction", "complexity": "high"},
      "expected": {"model": "claude-sonnet"}
    },
    {
      "name": "test_fallback_activates_on_timeout",
      "component": "fallback_handler",
      "input": {"primary_status": "timeout", "elapsed_ms": 30000},
      "expected": {"action": "use_secondary"}
    }
  ]
)}}
```

**Step 5: Schedule recurring evaluations**

```text
{{test_framework(
  action="schedule_eval",
  project="acme-invoice-processor",
  task="invoice_extraction",
  frequency="monthly",
  eval_set="invoice_extraction_eval_v1",
  compare_to="baseline",
  notify_on="warning,critical"
)}}
```

**Step 6: Set up human review sampling**

```text
{{test_framework(
  action="configure_human_review",
  project="acme-invoice-processor",
  sample_rate=0.05,
  sample_method="stratified",
  review_rubric=["accuracy", "tone", "completeness", "safety"],
  reviewer_queue="quality-review-channel",
  minimum_monthly_reviews=30
)}}
```

### What Good Looks Like

**A well-tested AI solution has these properties:**

- Unit tests cover all deterministic logic (parsing, routing, formatting, error handling)
- An evaluation set of 50+ labeled examples exists for every AI task
- Baseline quality scores are recorded and compared against on every change
- Regression alerts are configured with warning and critical thresholds
- Safety is tested with zero tolerance -- any safety failure triggers immediate action
- Human review samples at least 30 production outputs per month
- Quality trends are tracked over time (not just point-in-time snapshots)
- The evaluation set includes adversarial examples (bad input, edge cases, tricky formats)

**Common mistakes to avoid:**

| Mistake | Consequence | Fix |
|---|---|---|
| Only unit tests, no eval framework | Logic works but AI quality is unknown | Build eval set before deploying any AI task |
| Evaluation set too small (< 20 examples) | False confidence; does not catch edge cases | Minimum 50 examples per AI task |
| No adversarial examples | System handles the easy 90%, fails on the hard 10% | 15% of eval set should be intentionally difficult inputs |
| Testing only after problems | Quality issues reach clients before you catch them | Schedule monthly evaluations, evaluate on every prompt change |
| No baseline recorded | Cannot tell if quality got better or worse | Always save the first evaluation as the baseline |
| Ignoring format compliance | AI output breaks downstream systems | Include format checks in both unit tests and eval framework |
| Human review without a rubric | Reviewers rate inconsistently | Provide a specific 1-5 rubric for each quality dimension |

### Practice Exercise

Build a complete test suite for one AI task in your project:

1. Pick one AI task (e.g., invoice extraction, email classification)
2. Create 10 evaluation examples covering: 6 common cases, 3 edge cases, 1 adversarial case
3. Run the evaluation against your current prompt and save it as the baseline
4. Write 3 unit tests for the deterministic components around that task
5. Set up regression alerts with 5% warning and 10% critical thresholds
6. Make a small prompt change, re-run the evaluation, and compare to baseline

**Validation questions:**

- Does your evaluation set include at least one example the AI is likely to get wrong?
- Are your unit tests truly deterministic (same input always produces same output)?
- If someone updated the prompt tomorrow, would the regression alert catch a quality drop?
- Is your safety threshold set to zero tolerance?
- Can you explain to the client how you know the system is working correctly?
