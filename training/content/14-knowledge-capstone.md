# Module 14: Knowledge Capstone

> **Learning Path:** Knowledge & Content Strategist
> **Audience:** Content managers, knowledge workers, and information architects
> **Prerequisites:** Modules 11–13 — Knowledge System Foundations, Digest & Distribution, Advanced Knowledge Ops

---

## Lesson: Knowledge Base Build-Out

### Why This Matters

Everything you have learned so far — architecture, ingestion, taxonomy, retrieval optimization, voice standards, governance — converges here. This capstone lesson asks you to build a complete knowledge base from scratch for a realistic domain, making every design decision yourself.

This is where theory meets practice. In a real engagement, nobody hands you a checklist. You walk into an organization, assess what they have, decide what to build, and deliver a working system. The decisions you make in the first week shape the system for years.

**Why building from scratch is different from learning components:**

| Learning Components | Building From Scratch |
|---|---|
| Each skill practiced in isolation | Every decision affects every other decision |
| Clear right answers | Trade-offs with no single right answer |
| Mistakes are low-cost | Bad architecture is expensive to fix later |
| Instructor provides context | You must discover the context yourself |
| Focus on how | Focus on what, why, and when — not just how |

The gap between "I understand each piece" and "I can assemble the pieces into a working system" is the gap this lesson closes.

### How to Think About It

**The Build-Out Sequence**

Building a knowledge base is not linear. But there is an optimal sequence that minimizes rework:

```text
1. DISCOVER ──→ 2. DESIGN ──→ 3. BUILD ──→ 4. LOAD ──→ 5. TEST ──→ 6. GOVERN
     |               |             |            |            |            |
  Audit what      Architecture   Create KB,   Ingest       Test        Set up
  exists, who     taxonomy,      configure    content,     retrieval,  ownership,
  needs what      voice guide,   chunking,    tag, embed   tune RAG   freshness,
                  schema         set up                               audits
                                 retrieval
```

**Key decisions at each stage:**

| Stage | Decision | Wrong Answer Costs You |
|---|---|---|
| Discover | What knowledge domains matter? | Building for domains nobody uses |
| Design | Hierarchical or flat taxonomy? | Re-tagging hundreds of documents |
| Build | Chunk size and strategy? | Poor retrieval quality across the board |
| Load | What to ingest first? | Weeks spent on low-value content |
| Test | What test questions to use? | Blind spots in retrieval quality |
| Govern | Who owns what? | System decays within 6 months |

**The Domain: Boutique Hotel Operations**

For this capstone, you will build a knowledge base for a boutique hotel group with:

- 5 properties (2 hotels, 3 vacation rentals)
- 40 employees across all properties
- Current knowledge: scattered Google Docs, one outdated wiki, Slack messages, and "ask Maria"
- Goal: centralized operations knowledge that staff can query and that feeds automated daily digests

### Step-by-Step Approach

**Step 1: Discovery — Audit the current state**

Before building anything, understand what exists:

```text
{{knowledge_base(action="audit", scope="all", report_type="landscape")}}
```

Interview stakeholders. You need to know:

- What questions do staff ask most often? (These become your retrieval test set)
- What knowledge is most dangerous when wrong? (These become your priority ingestion items)
- Who knows things that are not written down? (These become your knowledge capture interviews)

**Step 2: Design — Define architecture and taxonomy**

```text
{{knowledge_base(action="configure", setting="taxonomy", value={"domains": [{"name": "property-ops", "description": "Property-specific SOPs, checklists, and procedures", "children": ["housekeeping", "maintenance", "inspections", "amenities"]}, {"name": "guest-services", "description": "Guest-facing processes and communication", "children": ["check-in", "check-out", "concierge", "complaints", "vip"]}, {"name": "hr-training", "description": "Staff policies, onboarding, and training materials", "children": ["policies", "onboarding", "role-guides", "safety"]}, {"name": "finance", "description": "Revenue management, billing, vendor payments", "children": ["pricing", "billing", "vendor-contracts", "reporting"]}, {"name": "compliance", "description": "Licenses, regulations, insurance, safety codes", "children": ["licenses", "fire-safety", "health-codes", "insurance"]}], "tag_schema": {"doc_type": {"values": ["sop", "checklist", "policy", "guide", "template", "faq", "report"], "required": true}, "audience": {"values": ["all-staff", "management", "housekeeping", "front-desk", "maintenance"], "required": true}, "property": {"values": ["hotel-downtown", "hotel-waterfront", "vr-oceanview", "vr-garden", "vr-cottage", "all-properties"], "required": true}, "priority": {"values": ["critical", "standard", "reference"], "required": false}}}})}}
```

**Step 3: Build — Create the knowledge base and configure retrieval**

```text
{{knowledge_base(action="create", name="hotel-ops-kb", domains=["property-ops", "guest-services", "hr-training", "finance", "compliance"], description="Central operations knowledge base for boutique hotel group", access_level="role-based")}}
```

Configure chunking per document type:

```text
{{knowledge_base(action="configure", setting="chunking", value={"default": {"strategy": "heading_based", "max_chunk_tokens": 500, "overlap_tokens": 75}, "overrides": [{"doc_type": "checklist", "strategy": "whole_document", "max_chunk_tokens": 1200}, {"doc_type": "faq", "strategy": "question_answer_pairs", "max_chunk_tokens": 300}, {"doc_type": "policy", "strategy": "heading_based", "max_chunk_tokens": 800, "overlap_tokens": 100}]})}}
```

**Step 4: Load — Ingest content in priority order**

Priority 1 (Week 1): Safety-critical and most-queried content

```text
{{knowledge_base(action="ingest", source="./priority-1/", format="auto", metadata={"priority": "critical", "audience": "all-staff"}, batch=true)}}
```

Priority 2 (Week 2): Property-specific SOPs and checklists

```text
{{knowledge_base(action="ingest", source="./property-sops/", format="auto", metadata={"domain": "property-ops", "doc_type": "sop"}, batch=true)}}
```

Priority 3 (Week 3): Training materials and reference guides

```text
{{knowledge_base(action="ingest", source="./training-guides/", format="auto", metadata={"domain": "hr-training", "doc_type": "guide"}, batch=true)}}
```

**Step 5: Test — Validate retrieval quality**

Create your test set from the questions staff actually ask:

```text
{{knowledge_base(action="create_test_set", name="staff-questions-v1", questions=[{"question": "What do I do if a guest reports a water leak?", "expected_source": "emergency-procedures.md", "expected_answer_contains": ["shut off valve", "notify maintenance", "relocate guest"]}, {"question": "What is the check-out cleaning sequence for hotel rooms?", "expected_source": "housekeeping-sop-hotel.md", "expected_answer_contains": ["strip linens", "bathroom", "inspect", "restock"]}, {"question": "How do I handle a noise complaint after 10 PM?", "expected_source": "guest-complaint-procedures.md", "expected_answer_contains": ["quiet hours", "first warning", "escalate to manager"]}, {"question": "What are the pool maintenance requirements?", "expected_source": "amenity-maintenance.md", "expected_answer_contains": ["chemical levels", "daily check", "log readings"]}, {"question": "How do I process a guest refund?", "expected_source": "billing-procedures.md", "expected_answer_contains": ["manager approval", "refund form", "within 48 hours"]}])}}
```

```text
{{knowledge_base(action="test_retrieval", test_set="staff-questions-v1", config={"top_k": 5, "return_debug": true})}}
```

Target: 80%+ Recall@5 and 70%+ answer accuracy before launch.

**Step 6: Govern — Establish ongoing maintenance**

```text
{{knowledge_base(action="assign_owners", assignments=[{"domain": "property-ops", "owner": "ops-director@hotel.com"}, {"domain": "guest-services", "owner": "guest-services-mgr@hotel.com"}, {"domain": "hr-training", "owner": "hr-lead@hotel.com"}, {"domain": "finance", "owner": "finance-mgr@hotel.com"}, {"domain": "compliance", "owner": "gm@hotel.com"}])}}
```

```text
{{knowledge_base(action="configure", setting="freshness_policies", value={"rules": [{"doc_type": "sop", "review_interval_days": 90}, {"doc_type": "checklist", "review_interval_days": 90}, {"doc_type": "policy", "review_interval_days": 180}, {"doc_type": "guide", "review_interval_days": 180}, {"doc_type": "faq", "review_interval_days": 60}]})}}
```

### Practice Exercise

**Scenario:** You are two weeks into the build-out. The knowledge base has 85 documents ingested. Staff have started using it, and you are getting feedback:

- "I asked about late check-out policy and got the cancellation policy instead"
- "The cleaning checklist it showed me was for the vacation rentals, not the hotel"
- "It gave me last year's pricing, not the current rates"

**Task:**

1. Diagnose each problem (retrieval, tagging, or freshness?)
2. Fix each issue
3. Verify the fix with test queries

Problem 1 diagnosis: Retrieval is confusing "check-out" in the guest policy context with "check-out" in the cancellation context. Fix: improve metadata filtering.

```text
{{knowledge_base(action="query", question="What is the late check-out policy?", filters={"domain": "guest-services", "doc_type": ["policy", "sop"]})}}
```

Problem 2 diagnosis: Property tag is missing or wrong. Fix: retag the document.

Problem 3 diagnosis: Outdated document is still active. Fix: archive old version, verify current version is ingested.

```text
{{knowledge_base(action="audit", scope="finance", report_type="freshness", thresholds={"stale_after_days": 90})}}
```

**Self-check:** After fixing all three issues, re-run the same queries. Do you get the correct answer every time? If yes, add these queries to your permanent test set so regressions are caught automatically.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Ingesting everything before testing anything | Completeness feels like progress | Ingest 20 docs, test, tune, then continue |
| Same chunk strategy for all doc types | One-size-fits-all default | Match chunking to document structure: checklists whole, policies by section |
| Skipping the discovery phase | Eager to build | Spend at least 3 days understanding what staff actually need before configuring anything |
| No governance from day one | "We'll add that later" | Governance set up during build, not after launch |
| Not testing with real user questions | Using synthetic test questions | Collect actual questions from staff during discovery; these are your best test set |

---

## Lesson: Automated Intelligence Brief

### Why This Matters

An automated intelligence brief is the crown jewel of a knowledge and content system. It combines everything you have learned — research agents, knowledge base retrieval, digest formatting, delivery channels, and pipeline automation — into a single daily output that makes decision-makers smarter every morning.

The brief does not just report what happened. It connects dots, highlights patterns, and surfaces the information leaders need to see but would not know to ask for. A good daily brief replaces 45 minutes of manual scanning across multiple sources with a 3-minute read that covers more ground.

**The intelligence brief value chain:**

```text
Without brief:                     With brief:
Leader checks 8 sources            Leader reads one brief
  → misses 3 of them               → covers all sources
  → spends 45 minutes              → spends 3 minutes
  → forgets to check one           → nothing slips through
  → no trend detection             → anomalies flagged automatically
  → acts on incomplete info        → acts on complete picture
```

**What makes a brief "intelligent" vs. just a summary:**

| Summary (basic) | Intelligence Brief (advanced) |
|---|---|
| Lists what happened | Explains why it matters |
| Reports raw numbers | Highlights anomalies and trends |
| Covers all items equally | Prioritizes by impact |
| Same format every day | Adapts to what is noteworthy today |
| No recommendations | Suggests actions or decisions |

### How to Think About It

**Brief Architecture**

An intelligence brief has three layers:

```text
Layer 1: COLLECTION (research agents gather from all sources)
    |
    ▼
Layer 2: SYNTHESIS (connect, compare, prioritize, detect anomalies)
    |
    ▼
Layer 3: DELIVERY (format for audience, deliver on schedule)
```

**Layer 1: Collection Sources**

| Source Category | What It Provides | Update Frequency |
|---|---|---|
| Internal operations data | Performance metrics, issues, completions | Real-time to daily |
| External market data | Competitor activity, market trends, pricing | Daily to weekly |
| Customer signals | Reviews, feedback, support tickets | Real-time |
| Financial data | Revenue, expenses, forecasts | Daily |
| Calendar and schedule | Upcoming events, deadlines, milestones | Real-time |
| Research feeds | Industry news, regulatory changes | Hourly to daily |

**Layer 2: Synthesis Techniques**

Raw data becomes intelligence through synthesis:

- **Trend detection:** "Revenue has been above average for 5 consecutive days"
- **Anomaly flagging:** "Guest complaint rate jumped 40% this week vs. trailing average"
- **Correlation:** "Occupancy dropped 12% the same week competitor launched a promotion"
- **Comparison:** "This month's maintenance costs are 25% above same month last year"
- **Countdown:** "Liquor license renewal due in 14 days — application not yet submitted"

**Layer 3: Delivery Format**

The brief should follow Telegram formatting standards for mobile consumption:

```text
clipboard DAILY INTELLIGENCE BRIEF — Mon Mar 20

P0 ACTIONS:
- warning License renewal due in 14 days — application not submitted
- warning Guest complaint rate +40% vs trailing avg (3 complaints in 2 days)

OPERATIONS:
- Occupancy: 88% (vs 82% avg) — 5th consecutive day above average
- 4 check-ins, 2 check-outs today
- Maintenance: 2 open tickets (both non-urgent)

REVENUE:
- chart Yesterday: $4,280.00 (+18% vs avg)
- chart MTD: $62,400.00 (tracking 12% above forecast)
- Competitor alert: Seaside Resort dropped rates 15% for April

MARKET:
- New short-term rental regulation proposed in city council — hearing April 3
- Tourism board reports 8% increase in spring bookings region-wide

UPCOMING:
- Wed: VIP guest arrival (returning guest, 4th stay)
- Fri: Monthly financial review with ownership
- Next Mon: Pool maintenance scheduled (closed 8 AM–12 PM)
```

### Step-by-Step Approach

**Step 1: Define your intelligence requirements**

What does the decision-maker need to know every morning? Interview them:

- "What is the first thing you check when you start your day?"
- "What information would change how you spend today?"
- "What have you been surprised by in the last month that you wish you had known earlier?"

**Step 2: Configure research agents for each source category**

```text
{{research_agent(action="create", name="ops-data-collector", config={"objective": "Collect daily operations metrics from internal systems", "sources": [{"type": "api", "endpoint": "pms_api", "data_points": ["occupancy", "check_ins", "check_outs", "revenue"]}, {"type": "api", "endpoint": "maintenance_system", "data_points": ["open_tickets", "completed_today", "overdue"]}], "processing": {"calculate_trends": true, "anomaly_detection": true, "comparison_periods": ["yesterday", "7_day_avg", "30_day_avg"]}, "schedule": "daily 05:30"})}}
```

```text
{{research_agent(action="create", name="market-intel-collector", config={"objective": "Monitor competitor pricing and local market conditions", "sources": [{"type": "web", "urls": ["https://example-competitor-a.com/rates", "https://example-competitor-b.com/availability"], "scrape_mode": "diff"}, {"type": "rss", "feeds": ["https://example-tourism-board.com/rss", "https://example-local-news.com/business/rss"], "keyword_filter": ["hotel", "tourism", "short-term rental", "regulation"]}], "processing": {"summarize": true, "relevance_threshold": 0.7}, "schedule": "daily 05:00"})}}
```

**Step 3: Build the synthesis pipeline**

```text
{{digest_builder(action="create_pipeline", name="daily-intelligence-brief", config={"stages": [{"name": "collect", "agents": ["ops-data-collector", "market-intel-collector", "review-monitor"], "schedule": "daily 05:00-06:00"}, {"name": "synthesize", "type": "intelligence_synthesis", "input": "collect.output", "operations": ["detect_trends", "flag_anomalies", "compare_to_benchmarks", "identify_correlations", "check_deadlines"]}, {"name": "prioritize", "type": "priority_rank", "input": "synthesize.output", "rules": {"P0": "requires_action_today OR deadline_within_14_days OR anomaly_severity_high", "P1": "notable_trend OR revenue_impact OR this_week_action", "P2": "informational OR future_planning"}}, {"name": "format", "type": "telegram_format", "input": "prioritize.output", "template": "intelligence-brief", "max_lines": 30, "voice_profile": "professional-concise"}, {"name": "deliver", "type": "telegram_send", "input": "format.output", "chat_id": "executive-channel", "schedule": "daily 06:30"}], "error_handling": {"retry_count": 3, "alert_on_failure": true}})}}
```

**Step 4: Test with historical data**

Before going live, run the pipeline against the last 7 days of historical data:

```text
{{digest_builder(action="run_pipeline", name="daily-intelligence-brief", mode="backtest", date_range="2026-03-13 to 2026-03-19")}}
```

Review each day's output. Would the brief have surfaced the right things? Did it miss anything important? Did it include noise?

**Step 5: Go live and iterate**

```text
{{digest_builder(action="activate_pipeline", name="daily-intelligence-brief")}}
```

After one week of live operation, collect feedback from the reader and tune.

### Practice Exercise

**Scenario:** The hotel group's general manager wants a daily brief that covers operations, revenue, guest satisfaction, competitive landscape, and upcoming deadlines. She reads it at 6:30 AM on her phone while having coffee.

**Task:**

1. Design the brief sections (what goes where)
2. Configure the research agents needed
3. Build the synthesis pipeline
4. Write a sample output for a typical Tuesday

Write the sample output:

```text
{{telegram_send(action="send", chat_id="gm-channel", message="clipboard DAILY INTELLIGENCE BRIEF — Tue Mar 21\n\nACTION REQUIRED:\n- warning Fire inspection scheduled Thu — ensure all exit signs tested by Wed EOD\n- warning 1 negative review posted overnight (Booking.com, 2/5) — response needed\n\nOPERATIONS:\n- Occupancy: 90% (9/10 hotel rooms, 3/3 vacation rentals)\n- 2 check-ins (Hotel Downtown: 3:00 PM, VR Oceanview: 4:00 PM)\n- 1 check-out (Hotel Waterfront: 11:00 AM)\n- Maintenance: 1 open ticket (VR Garden — slow drain, plumber Thu AM)\n\nREVENUE:\n- chart Yesterday: $5,120.00 (+22% vs Mon avg)\n- chart MTD: $67,520.00 (tracking 15% above forecast)\n- ADR: $285.00 (up $12 from last week)\n\nMARKET:\n- Competitor Seaside Resort: April rates dropped 15% — may indicate soft demand\n- Tourism board: Spring festival Apr 5-7 expected to drive 20% booking surge\n\nUPCOMING:\n- Wed: Exit sign testing (fire inspection prep)\n- Thu: Fire inspection 10:00 AM, Plumber at VR Garden 9:00 AM\n- Fri: Monthly P&L review with ownership group")}}
```

**Self-check:** Time yourself reading the sample brief. If it takes more than 3 minutes, it is too long. If you finish and feel like you are missing something important, it is incomplete. The sweet spot is 2-3 minutes to read, zero items that make you say "I need to go check something else."

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Including every data point available | More data feels more valuable | Include only what changes a decision or triggers an action |
| No anomaly detection | Reporting raw numbers seems sufficient | Always compare to baselines; flag deviations, not just values |
| Same brief every day regardless of content | Template rigidity | Brief should adapt: skip empty sections, expand when anomalies exist |
| Not testing with historical data | Eager to launch | Backtest against 7 days minimum; verify it would have caught real issues |
| No feedback loop with the reader | Assuming the brief is right | Ask the reader weekly: "What did you find most/least useful?" |

---

## Lesson: Knowledge System Audit

### Why This Matters

Building a knowledge system is the beginning, not the end. Over time, even well-governed systems develop problems: content drifts out of date, taxonomy categories become bloated, retrieval quality degrades as the corpus grows, and usage patterns shift away from what you originally designed for.

An audit is a systematic health check. It reveals problems before users lose trust and surfaces opportunities to improve the system's value. Organizations that audit quarterly maintain high-quality knowledge systems. Organizations that never audit watch their systems decay into expensive digital landfills.

**The audit payoff:**

| Audit Frequency | Knowledge Quality Over Time | User Trust |
|---|---|---|
| Quarterly | Stable or improving | High — "the system is reliable" |
| Annually | Gradual decline, periodic recovery | Medium — "it's usually right" |
| Never | Continuous decline | Low — "I don't trust it, I ask a person" |

**What an audit uncovers:**

- **Staleness:** 30% of your content has not been reviewed in 6 months
- **Gaps:** Users search for "refund process" 50 times/month but no document covers it
- **Redundancy:** Three versions of the same SOP exist, all slightly different
- **Quality:** 15% of documents score below 3/5 on clarity
- **Orphans:** 40 documents have no assigned owner
- **Dead weight:** 80 documents have never been retrieved by any user

### How to Think About It

**The Five Dimensions of a Knowledge Audit**

```text
             FRESHNESS
                |
        ┌───────┼───────┐
        |       |       |
   COVERAGE   AUDIT   QUALITY
        |       |       |
        └───────┼───────┘
                |
            USAGE
                |
           GOVERNANCE
```

**Dimension 1: Freshness — Is the content current?**

| Metric | How to Measure | Red Flag Threshold |
|---|---|---|
| % documents past review date | Count of expired / total | Above 20% |
| Average days since last review | Mean across all docs | Above 120 days |
| Oldest unreviewed document | Max days since review | Above 365 days |
| % documents with no freshness policy | Count without policy / total | Above 10% |

**Dimension 2: Coverage — Does the KB cover what users need?**

| Metric | How to Measure | Red Flag Threshold |
|---|---|---|
| Failed query rate | Queries with no relevant results / total queries | Above 15% |
| Top unfulfilled queries | Most frequent queries with poor results | Any query asked 10+ times with no good answer |
| Domain coverage score | Domains with content / total domains defined | Below 80% |
| Gap analysis | Topics mentioned in queries but absent from KB | Any high-frequency topic missing |

**Dimension 3: Quality — Is the content accurate and useful?**

| Metric | How to Measure | Red Flag Threshold |
|---|---|---|
| Average quality score | Mean of accuracy + completeness + clarity + actionability | Below 3.0/5.0 |
| User-reported issues | Tickets flagging wrong or confusing content | More than 5/month |
| Retrieval precision | % of top-3 results that are actually relevant | Below 70% |
| Contradictions | Documents that give conflicting answers | Any contradiction is a red flag |

**Dimension 4: Usage — Is the system being used effectively?**

| Metric | How to Measure | Red Flag Threshold |
|---|---|---|
| Daily active queries | Unique queries per day | Below expected (varies by org size) |
| Query-to-action rate | Queries that lead to a user action | Below 40% |
| Abandonment rate | Queries where user does not click any result | Above 30% |
| Never-retrieved documents | Docs with zero retrievals in 90 days | Above 25% of total |

**Dimension 5: Governance — Are the maintenance processes working?**

| Metric | How to Measure | Red Flag Threshold |
|---|---|---|
| % documents with assigned owner | Docs with owner / total | Below 90% |
| Review compliance rate | Reviews completed on time / reviews due | Below 75% |
| Average escalation response time | Time from escalation to resolution | Above 7 days |
| Archival compliance | Expired docs archived on schedule | Below 80% |

### Step-by-Step Approach

**Step 1: Run the automated audit**

```text
{{knowledge_base(action="audit", scope="all", report_type="comprehensive", dimensions=["freshness", "coverage", "quality", "usage", "governance"])}}
```

**Step 2: Analyze the freshness report**

```text
{{knowledge_base(action="audit", scope="all", report_type="freshness", thresholds={"stale_after_days": 90, "critical_after_days": 180, "ancient_after_days": 365})}}
```

Categorize results:

```text
Freshness Audit Results:
├── Current (reviewed within policy): ___%
├── Stale (past review date, <180 days): ___%
├── Critical (180-365 days overdue): ___%
└── Ancient (365+ days overdue): ___%
```

**Step 3: Analyze coverage gaps**

```text
{{knowledge_base(action="query_log", period="last_90_days", report="failed_queries", sort_by="frequency", limit=20)}}
```

These are the top 20 questions your knowledge base cannot answer. Each one is either:

- A content gap (the knowledge exists but is not in the system)
- A retrieval gap (the knowledge is in the system but is not being found)
- A scope gap (the knowledge is outside your system's intended scope)

**Step 4: Sample and score quality**

```text
{{knowledge_base(action="schedule_audit", config={"type": "quality_sample", "sample_size": 30, "scoring_dimensions": ["accuracy", "completeness", "clarity", "actionability"], "sample_method": "stratified_by_domain"})}}
```

Score each sampled document on the four quality dimensions (1-5 scale). Calculate averages by domain and by document type.

**Step 5: Review usage patterns**

```text
{{knowledge_base(action="audit", scope="all", report_type="usage", period="last_90_days", metrics=["daily_queries", "top_queries", "never_retrieved", "abandonment_rate"])}}
```

**Step 6: Check governance health**

```text
{{knowledge_base(action="audit", scope="all", report_type="governance", metrics=["owner_assignment_rate", "review_compliance", "escalation_response_time", "archival_compliance"])}}
```

**Step 7: Produce the audit report and action plan**

Synthesize findings into a prioritized action plan:

```text
{{digest_builder(action="create", template="audit-report", config={"title": "Knowledge System Audit — Q1 2026", "sections": [{"name": "executive_summary", "content": "Overall health score and top 3 findings"}, {"name": "freshness", "content": "Freshness metrics and critical documents needing review"}, {"name": "coverage", "content": "Top coverage gaps with recommended additions"}, {"name": "quality", "content": "Quality scores by domain with improvement targets"}, {"name": "usage", "content": "Usage trends and adoption metrics"}, {"name": "governance", "content": "Governance compliance and owner accountability"}, {"name": "action_plan", "content": "Prioritized list of fixes with owners and deadlines"}]})}}
```

Deliver the summary via Telegram:

```text
{{telegram_send(action="send", chat_id="knowledge-ops", message="clipboard KNOWLEDGE SYSTEM AUDIT — Q1 2026\n\nOverall Health: 72/100 (Needs Attention)\n\nTop Findings:\n1. warning 28% of documents past review date (target: <20%)\n2. warning 15 high-frequency queries with no good answer (coverage gaps)\n3. checkmark Governance compliance at 85% (above 75% threshold)\n\nCritical Actions:\n- 12 documents need immediate review (safety/compliance domain)\n- 3 SOPs have contradicting versions — resolve by Mar 28\n- Create content for top 5 unanswered queries by Apr 4\n\nFull report: [link to dashboard]")}}
```

### Practice Exercise

**Scenario:** You are conducting a quarterly audit of the hotel group's knowledge base (built in the previous capstone lesson). The system has been live for 3 months with 120 documents and approximately 50 queries per day.

**Task:**

1. Run a comprehensive audit across all five dimensions
2. Identify the top 3 issues
3. Create an action plan with owners and deadlines
4. Deliver the audit summary to stakeholders

```text
{{knowledge_base(action="audit", scope="all", report_type="comprehensive", dimensions=["freshness", "coverage", "quality", "usage", "governance"])}}
```

Based on the audit, fix the most critical issue immediately:

```text
{{knowledge_base(action="query_log", period="last_90_days", report="failed_queries", sort_by="frequency", limit=5)}}
```

If the top failed query is "How do I handle a guest medical emergency?" and that content does not exist:

```text
{{knowledge_base(action="ingest", source="emergency-medical-procedures.md", format="markdown", metadata={"domain": "compliance", "doc_type": "sop", "audience": "all-staff", "priority": "critical", "freshness_policy": "90 days", "owner": "gm@hotel.com"})}}
```

Verify the fix:

```text
{{knowledge_base(action="query", question="How do I handle a guest medical emergency?")}}
```

**Self-check:** After addressing the top 3 audit findings, re-run the audit. Did the overall health score improve? If not, you may have fixed symptoms rather than root causes. For example, reviewing 12 stale documents fixes the freshness metric today, but if you did not also fix the governance process that let them go stale, the same problem returns next quarter.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Auditing only freshness | It is the easiest to measure | Audit all five dimensions; coverage and quality issues are often more damaging |
| No action plan from audit findings | Audit feels complete when numbers are produced | Every finding needs an owner, a fix, and a deadline |
| Auditing too infrequently | "The system is working fine" | Quarterly minimum; monthly for the first year |
| Not tracking audit metrics over time | Each audit treated as standalone | Compare quarter-over-quarter to detect trends and measure improvement |
| Fixing content without fixing process | Treat symptoms, not causes | If documents go stale, fix the review process, not just the stale documents |
