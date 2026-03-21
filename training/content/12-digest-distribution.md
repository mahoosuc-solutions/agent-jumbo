# Module 12: Digest & Distribution

> **Learning Path:** Knowledge & Content Strategist
> **Audience:** Content managers, knowledge workers, and information architects
> **Prerequisites:** Module 11 — Knowledge System Foundations

---

## Lesson: Digest Builder Fundamentals

### Why This Matters

A digest is the bridge between your knowledge system and the humans who need that knowledge. You can have the best-organized knowledge base in the world, but if people have to go looking for updates, most of them will not. Digests bring the right information to the right people at the right time without requiring them to ask.

Without well-designed digests:

- **Information overload** — people get a firehose of raw updates and learn to ignore everything
- **Information starvation** — people miss critical updates because nothing was pushed to them
- **Notification fatigue** — too many low-value pings train people to mute the channel
- **Context collapse** — a digest that mixes urgent alerts with trivia loses both

The difference between a digest people read and one they archive unread is design. Not the information itself, but how it is structured, prioritized, and timed.

**What is at stake:**

| Digest Quality | Open Rate | Action Rate | Trust Level |
|---|---|---|---|
| Excellent (curated, prioritized, actionable) | 90%+ | 60%+ act on at least one item | "I rely on this every day" |
| Adequate (complete but unfocused) | 50-70% | 20-30% act on something | "I skim it when I have time" |
| Poor (noisy, unprioritized, too long) | Below 30% | Below 10% | "I muted that channel" |

### How to Think About It

**Anatomy of a Good Digest**

Every effective digest has five components:

```text
┌─────────────────────────────────┐
│  HEADER                        │
│  Icon + Title + Date/Period    │
├─────────────────────────────────┤
│  PRIORITY SECTION              │
│  P0 items: must act today      │
│  (0-3 items max)               │
├─────────────────────────────────┤
│  BODY SECTIONS                 │
│  Grouped by topic/domain       │
│  P1 items with context         │
│  (3-8 items per section)       │
├─────────────────────────────────┤
│  METRICS / NUMBERS             │
│  Key stats, counts, trends     │
│  (dashboard-style summary)     │
├─────────────────────────────────┤
│  FOOTER                        │
│  Next actions / upcoming       │
│  Link to full dashboard        │
└─────────────────────────────────┘
```

**The Information Density Rule**

A good digest maximizes signal per line. Every line must earn its place.

- Bad: "There are some items that may need your attention in the operations area."
- Good: "3 maintenance tickets overdue (oldest: 4 days, Unit 7B water heater)"

The bad version uses 13 words to say nothing specific. The good version uses 11 words to communicate count, severity, and the specific worst case.

**Density targets:**

| Element | Bad Density | Good Density |
|---|---|---|
| Line item | Vague statement, no numbers | Specific fact with count or metric |
| Section header | "Updates" | "Guest Operations — 3 check-ins, 1 issue" |
| Priority call-out | "Something urgent came up" | "P0: Unit 12A AC failed, guest arriving 3:00 PM ET" |

**Audience Targeting**

Not everyone needs the same digest. Design for your audience:

| Audience | What They Need | Digest Style |
|---|---|---|
| Executive/Owner | Big picture, exceptions, decisions needed | 5-10 lines, metrics-heavy, P0 only |
| Operations Manager | Detailed task status, blockers, resource needs | 15-25 lines, grouped by function |
| Front-line Staff | Their tasks today, relevant updates | 5-8 lines, action-oriented, their scope only |
| External Client | Progress, milestones, next steps | 8-12 lines, professional tone, no internal jargon |

### Step-by-Step Approach

**Step 1: Define your digest purpose and audience**

Before building anything, answer three questions:

- Who reads this digest?
- What decisions does it support?
- What is the one thing the reader must not miss?

**Step 2: Create a digest template**

```text
{{digest_builder(action="create", template="daily-ops", config={"title": "Daily Operations Brief", "schedule": "daily 07:00", "audience": "operations-manager", "sections": [{"name": "priority_alerts", "source": "knowledge_base", "filter": {"priority": "P0"}, "max_items": 3}, {"name": "guest_operations", "source": "knowledge_base", "filter": {"domain": "guest-services"}, "max_items": 8}, {"name": "maintenance", "source": "knowledge_base", "filter": {"domain": "maintenance", "status": "open"}, "max_items": 5}, {"name": "metrics", "source": "analytics", "metrics": ["occupancy_rate", "revenue_today", "open_tickets"]}, {"name": "upcoming", "source": "calendar", "lookahead_hours": 24}]})}}
```

**Step 3: Configure information density rules**

```text
{{digest_builder(action="configure", template="daily-ops", setting="density_rules", value={"max_total_lines": 25, "require_counts": true, "require_specifics": true, "collapse_if_empty": true, "skip_section_if_no_items": true})}}
```

**Step 4: Preview and refine**

```text
{{digest_builder(action="preview", template="daily-ops", sample_date="2026-03-20")}}
```

Review the preview critically. Is there a single line that could be cut without losing value? Cut it.

### Practice Exercise

**Scenario:** You need to design three digests for a property management company:

1. An executive summary for the owner (checks phone once in the morning)
2. An operations brief for the property manager (lives in Telegram all day)
3. A task list for the cleaning crew lead (needs simple, actionable list)

**Task:** Create the executive summary digest:

```text
{{digest_builder(action="create", template="executive-daily", config={"title": "Daily Executive Summary", "schedule": "daily 07:30", "audience": "executive", "sections": [{"name": "attention_required", "source": "knowledge_base", "filter": {"priority": ["P0", "P1"], "needs_decision": true}, "max_items": 3}, {"name": "key_metrics", "source": "analytics", "metrics": ["total_revenue_yesterday", "occupancy_rate", "guest_satisfaction_score", "open_issues_count"]}, {"name": "notable", "source": "knowledge_base", "filter": {"notable": true}, "max_items": 3}], "density_rules": {"max_total_lines": 12, "collapse_if_empty": true}})}}
```

**Self-check:** Show your executive digest to someone unfamiliar with the business. Can they understand every line in under 30 seconds? If any line requires explanation, it is too jargon-heavy or not specific enough.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Sending the same digest to everyone | Easier to maintain one template | Build audience-specific templates; reuse data sources |
| Including items with no action | "They might want to know" | Every line must inform a decision or trigger an action |
| No priority differentiation | All items feel important | Use P0/P1/P2 ranking; lead with P0 always |
| Too many items per digest | Fear of missing something | Cap at 25 lines; link to dashboard for full details |
| Sending digests when nothing happened | Scheduled = must send | Use skip-silently pattern for non-anchor digests |

---

## Lesson: Telegram Digest Delivery

### Why This Matters

Telegram is where your digests reach operators in real time. It is the delivery channel that lives in their pocket. But Telegram has constraints that email and dashboards do not: small screen, quick scroll, notification badge. A digest that works beautifully in a web dashboard can be unreadable as a Telegram message.

Mastering Telegram delivery means understanding its format rules, its limitations, and how operators actually consume messages on mobile. Get this right and your digest becomes the first thing they check every morning. Get it wrong and your bot gets muted on day three.

**Channel characteristics:**

| Channel | Read Context | Screen Size | Attention Window | Best For |
|---|---|---|---|---|
| Email | Desktop, scheduled | Large | 2-5 minutes | Detailed reports, attachments |
| Dashboard | Desktop, on-demand | Large | Self-paced | Exploration, drill-down |
| Telegram | Mobile, immediate | Small | 10-30 seconds | Alerts, summaries, quick status |
| Slack | Desktop/mobile, async | Medium | 30-60 seconds | Team discussion, threaded context |

### How to Think About It

**Telegram Formatting Standards**

Follow the standard digest format from daily operations:

```text
[icon] TITLE — date

Section 1:
- Item with key detail
- Item with key detail

Section 2:
- Item with key detail
```

**Icons by category:**

| Category | Icon | When to Use |
|---|---|---|
| Property ops | house | Property-related updates |
| Calendar | calendar | Schedule, check-ins, check-outs |
| Finance | chart | Revenue, expenses, financial metrics |
| Client/project | clipboard | Client updates, project status |
| Alert/urgent | warning | P0 items, failures, urgent issues |
| Success/complete | checkmark | Completed tasks, resolved issues |
| BizDev/pipeline | handshake | Sales, partnerships, leads |

**Formatting Rules (non-negotiable):**

1. Lead with the most actionable item
2. Use bullet points, never paragraphs
3. Include counts: "3 check-ins, 2 check-outs" not "several check-ins"
4. Timestamps in 12h format with timezone: "2:30 PM ET"
5. Currency always with dollar sign and two decimals: "$1,234.56"
6. Keep total message under 30 lines — operator scans on mobile

**Priority Ranking for Telegram:**

| Urgency | Impact | Priority | Telegram Action |
|---|---|---|---|
| Today | Revenue | P0 | Always send immediately |
| Today | Operations | P0 | Always send immediately |
| This week | Revenue | P1 | Send in scheduled digest |
| Today | Informational | P1 | Send in scheduled digest |
| This week | Operations | P2 | Send only if anomaly detected |
| Future | Informational | P2 | Weekly rollup only |

**The Skip-Silently Pattern**

Not every scheduled check should produce a message. Notification fatigue kills engagement faster than missing information.

When to skip silently (send nothing):

- No new bookings in the check window
- No upcoming deadlines
- No overdue issues
- All metrics within normal range

When to always send (never skip):

- Morning briefing (daily rhythm anchor)
- End-of-day status (closure signal)
- Weekly reports (periodic rhythm)
- Any error or health check failure

**Digest Deduplication**

When multiple tasks run at similar times, avoid reporting the same fact twice:

- Morning briefing owns the overview — later task-specific messages add detail, do not repeat it
- EOD status covers changes since morning, does not re-report morning items
- Weekly reports supersede daily reports for the same data range

### Step-by-Step Approach

**Step 1: Design your Telegram message**

Draft the message first as plain text. Every line must survive the 10-second mobile scan test.

```text
{{digest_builder(action="create", template="morning-telegram", config={"title": "Morning Ops Brief", "channel": "telegram", "schedule": "daily 07:00", "format": "telegram_standard", "sections": [{"name": "priority", "icon": "warning", "filter": {"priority": "P0"}}, {"name": "today_ops", "icon": "calendar", "filter": {"date": "today", "domain": "operations"}}, {"name": "revenue", "icon": "chart", "filter": {"domain": "finance", "period": "yesterday"}}, {"name": "upcoming", "icon": "clipboard", "filter": {"date_range": "next_24h"}}], "rules": {"max_lines": 25, "skip_empty_sections": true, "dedup_against": ["eod-telegram"]}})}}
```

**Step 2: Send a test message**

```text
{{telegram_send(action="send", chat_id="ops-channel", message="calendar TODAY — Fri Mar 20\n\nGuest Ops:\n- 3 check-ins (earliest: 2:00 PM ET)\n- 1 check-out (11:00 AM ET, Unit 4B)\n- Mid-stay check: Unit 7A (day 3 of 5)\n\nMaintenance:\n- warning Unit 12A AC repair scheduled 10:00 AM\n- Pool filter replacement complete checkmark\n\nRevenue:\n- chart Yesterday: $2,847.00 (vs $2,600.00 avg)\n- Occupancy: 85% (10/12 units)")}}
```

**Step 3: Configure skip-silently rules**

```text
{{digest_builder(action="configure", template="midday-triage", setting="skip_rules", value={"skip_if": ["no_p0_items", "no_new_issues_since_morning", "all_metrics_in_range"], "never_skip": false, "log_skips": true})}}
```

**Step 4: Set up the daily rhythm**

```text
{{digest_builder(action="schedule", config={"timezone": "America/New_York", "schedule": [{"template": "morning-telegram", "time": "07:00", "never_skip": true}, {"template": "midday-triage", "time": "12:00", "skip_silently": true}, {"template": "eod-telegram", "time": "17:30", "never_skip": true}, {"template": "tomorrow-prep", "time": "20:00", "skip_silently": true}]})}}
```

### Practice Exercise

**Scenario:** Design the end-of-day Telegram digest for a property manager. The message must:

- Cover only what changed since the morning brief
- Include revenue for the day and comparison to average
- Flag any unresolved maintenance issues
- Preview tomorrow's schedule

**Task:**

```text
{{digest_builder(action="create", template="eod-telegram", config={"title": "EOD Status", "channel": "telegram", "schedule": "daily 17:30", "format": "telegram_standard", "sections": [{"name": "changes", "icon": "clipboard", "source": "delta_since", "reference": "morning-telegram"}, {"name": "revenue", "icon": "chart", "metrics": ["revenue_today", "revenue_vs_average", "payments_pending"]}, {"name": "open_issues", "icon": "warning", "filter": {"status": "open", "domain": "maintenance"}}, {"name": "tomorrow", "icon": "calendar", "filter": {"date": "tomorrow", "domain": "operations"}}], "rules": {"max_lines": 20, "never_skip": true, "dedup_against": ["morning-telegram"]}})}}
```

Test the output:

```text
{{telegram_send(action="send", chat_id="test-channel", message="clipboard EOD STATUS — Fri Mar 20\n\nSince this morning:\n- Unit 4B check-out completed on time checkmark\n- 2 of 3 check-ins completed (Unit 9A pending, ETA 8:00 PM)\n- New maintenance request: Unit 2C dishwasher leak\n\nRevenue:\n- chart Today: $3,120.00 (+$520 vs avg)\n- 1 payment pending: Unit 6A ($890.00)\n\nOpen Issues:\n- warning Unit 12A AC — parts ordered, ETA Monday\n- warning Unit 2C dishwasher — plumber scheduled tomorrow 9 AM\n\nTomorrow:\n- 2 check-outs, 4 check-ins\n- Plumber 9:00 AM (Unit 2C)\n- Pool maintenance 2:00 PM")}}
```

**Self-check:** Count the lines. Is it under 30? Does every line contain a specific fact (number, time, unit, name)? Is the most urgent item near the top? Could you act on this message without opening any other tool?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Writing paragraphs in Telegram | Writing like email | Bullet points only; one fact per line |
| No icons or visual anchors | Seems decorative | Icons enable instant scanning; use them consistently |
| Sending at random times | Triggered by events, not rhythm | Establish a daily schedule; operators rely on predictability |
| Repeating morning info in EOD | Completeness instinct | EOD covers delta only; reference morning for baseline |
| Not testing on mobile | Developing on desktop | Always preview on a phone screen before deploying |

---

## Lesson: Research Agent Workflows

### Why This Matters

A research agent is an automated intelligence gatherer. Instead of you manually reading 15 articles, checking 8 websites, and synthesizing findings into a summary, a research agent does the collection and first-pass synthesis, leaving you to do the high-value work: judgment, strategy, and decision-making.

Without research agents:

- **You miss things** — no human can monitor all relevant sources consistently
- **You are slow** — manual research takes hours; agents take minutes
- **You are inconsistent** — some days you research thoroughly, other days you skim
- **You cannot scale** — one person can deeply research one topic per day; agents can handle dozens

The goal is not to replace human judgment. The goal is to ensure human judgment is applied to a complete, current, well-organized information set rather than whatever you happened to stumble across.

**Research agent vs. manual research:**

| Dimension | Manual Research | Research Agent |
|---|---|---|
| Coverage | Limited by time and attention | Covers all configured sources |
| Consistency | Varies by day and energy | Same thoroughness every run |
| Speed | 2-4 hours for deep research | 5-15 minutes for equivalent scope |
| Judgment | Excellent (human strength) | Poor (needs human review) |
| Pattern detection | Limited by working memory | Can flag statistical anomalies |

### How to Think About It

**Research Agent Components**

Every research agent has four configurable layers:

```text
SOURCES ──→ COLLECTION ──→ PROCESSING ──→ OUTPUT
  |              |              |             |
What to      How to get     What to do     Where to
monitor      the data       with it        deliver it
```

**Layer 1: Sources — What to monitor**

| Source Type | Example | Update Frequency | Best For |
|---|---|---|---|
| RSS feeds | Industry news sites | Hourly | Breaking news, trends |
| Web pages | Competitor websites, pricing pages | Daily | Competitive intelligence |
| APIs | Market data, social media metrics | Real-time to hourly | Quantitative tracking |
| Documents | Uploaded reports, whitepapers | On ingestion | Deep analysis |
| Databases | Internal CRM, analytics | Scheduled | Performance tracking |

**Layer 2: Collection — How to gather**

- **Full scrape:** Pull entire page/document content
- **Diff scrape:** Only capture what changed since last run
- **Keyword monitor:** Only capture content matching specific terms
- **Structured extraction:** Pull specific data points (prices, dates, names)

**Layer 3: Processing — What to do with raw data**

- **Summarization:** Compress long articles into key points
- **Classification:** Tag by relevance, topic, sentiment
- **Deduplication:** Remove repeated information across sources
- **Scoring:** Rank by relevance to your specific interests
- **Comparison:** Highlight changes from previous runs

**Layer 4: Output — Where results go**

- Knowledge base (for long-term storage and retrieval)
- Digest (for daily/weekly summaries)
- Alert (for urgent findings)
- Dashboard (for trends and metrics)

### Step-by-Step Approach

**Step 1: Define your research objective**

Be specific. "Monitor the industry" is not an objective. "Track competitor pricing changes for vacation rentals in our market within 24 hours" is.

**Step 2: Configure your research agent**

```text
{{research_agent(action="create", name="competitor-pricing-monitor", config={"objective": "Track competitor pricing changes for vacation rentals in Charleston SC market", "sources": [{"type": "web", "urls": ["https://example-competitor-1.com/listings", "https://example-competitor-2.com/charleston"], "scrape_mode": "diff", "frequency": "daily"}, {"type": "rss", "feeds": ["https://example-vacation-news.com/rss"], "keyword_filter": ["charleston", "vacation rental", "pricing"]}, {"type": "api", "endpoint": "market_data_api", "params": {"market": "charleston_sc", "property_type": "vacation_rental"}}], "processing": {"summarize": true, "classify_by": ["pricing_change", "new_listing", "market_trend"], "dedup": true, "relevance_threshold": 0.7}, "output": {"knowledge_base": "market-intelligence-kb", "digest": "weekly-market-brief", "alert_on": {"pricing_change_pct": 10}}})}}
```

**Step 3: Run the agent and review results**

```text
{{research_agent(action="run", name="competitor-pricing-monitor")}}
```

**Step 4: Review and tune quality**

After the first few runs, evaluate:

```text
{{research_agent(action="evaluate", name="competitor-pricing-monitor", metrics=["relevance_accuracy", "source_coverage", "false_positive_rate"])}}
```

Adjust the relevance threshold up if you get too much noise, down if you are missing important items.

**Step 5: Schedule for ongoing operation**

```text
{{research_agent(action="schedule", name="competitor-pricing-monitor", schedule="daily 06:00", timezone="America/New_York")}}
```

### Practice Exercise

**Scenario:** You manage knowledge for a boutique consulting firm. The partners want a weekly intelligence brief covering:

- Industry trends in their three focus sectors (healthcare, fintech, logistics)
- Competitor activity (new hires, new services, published thought leadership)
- Regulatory changes that affect their clients

**Task:**

1. Design three research agents (one per information need)
2. Configure source selection and processing
3. Set up output routing

```text
{{research_agent(action="create", name="industry-trends", config={"objective": "Track weekly trends in healthcare, fintech, and logistics sectors", "sources": [{"type": "rss", "feeds": ["https://example-healthtech-news.com/rss", "https://example-fintech-weekly.com/feed", "https://example-logistics-today.com/rss"], "keyword_filter": ["AI", "automation", "digital transformation", "regulation"]}, {"type": "web", "urls": ["https://example-mckinsey.com/industries", "https://example-hbr.com/topics"], "scrape_mode": "diff", "frequency": "weekly"}], "processing": {"summarize": true, "max_items_per_sector": 5, "relevance_threshold": 0.75}, "output": {"digest": "weekly-intelligence-brief", "knowledge_base": "research-kb"}})}}
```

```text
{{research_agent(action="run", topic="competitor activity and new service announcements in management consulting")}}
```

**Self-check:** After the first run, check: Are the summaries specific enough to act on? If a summary says "Healthcare sector continues to evolve," that is useless. It should say "CMS proposed new telehealth reimbursement rules affecting 3 of our clients — comment period closes April 15." Tune your relevance threshold and source selection until summaries are actionable.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Too many sources, no filtering | More sources feels more thorough | Start with 3-5 high-quality sources; add more only if gaps exist |
| No relevance threshold | Default accepts everything | Set threshold at 0.7, tune based on noise ratio |
| Running without reviewing output | Set and forget mentality | Review first 3 runs manually; adjust before automating |
| Generic objectives | Vague goals feel inclusive | Write objectives as specific questions you need answered |
| Not routing to knowledge base | Using only for digest | Store research findings for long-term retrieval and trend analysis |

---

## Lesson: Content Pipeline Automation

### Why This Matters

Individual tools — ingestion, research agents, digest builders, delivery channels — are useful on their own. But the real power comes when they are connected into an automated pipeline. A content pipeline takes raw sources and, without human intervention, transforms them into curated, prioritized, delivered knowledge.

Without pipeline automation:

- **Manual bottlenecks** — someone has to remember to run the research agent, copy the results, format the digest, and send it
- **Inconsistency** — the pipeline runs perfectly when that person is available and breaks when they are not
- **Latency** — hours or days pass between source update and delivery to the person who needs it
- **Error accumulation** — each manual step introduces potential for mistakes, missed items, or formatting errors

A well-built pipeline runs reliably whether you are awake, on vacation, or sick. It is the difference between a knowledge system that depends on a person and one that depends on a process.

**Pipeline maturity levels:**

| Level | Description | Reliability | Human Effort |
|---|---|---|---|
| Manual | Person runs each step manually | Depends on person | 2-4 hours/day |
| Semi-automated | Some steps automated, manual triggers | Better, but gaps | 30-60 min/day |
| Fully automated | End-to-end, scheduled, self-monitoring | High, with alerts on failure | 10 min/day (review only) |
| Self-healing | Auto-detects and recovers from failures | Very high | 5 min/day (exception review) |

### How to Think About It

**The Content Pipeline Architecture**

Every content pipeline follows the same flow:

```text
SOURCE ──→ INGEST ──→ PROCESS ──→ STORE ──→ CURATE ──→ DELIVER
  |           |           |          |          |           |
External   Parse &    Summarize   Knowledge   Prioritize  Telegram
feeds,     chunk,     classify,   base with   filter,     email,
docs,      extract    deduplicate metadata    format      dashboard
APIs       metadata
```

**Pipeline stages in detail:**

| Stage | Input | Transformation | Output |
|---|---|---|---|
| Source | External URLs, files, APIs | Fetch/download | Raw content |
| Ingest | Raw content | Parse, chunk, extract metadata | Structured chunks |
| Process | Structured chunks | Summarize, classify, score, dedup | Processed knowledge items |
| Store | Processed items | Embed, index, tag | Knowledge base entries |
| Curate | KB entries + context | Priority rank, audience filter, format | Digest-ready content |
| Deliver | Digest-ready content | Channel-specific formatting | Telegram/email/dashboard |

**Error Handling at Each Stage**

Pipelines fail. The question is whether they fail silently (worst case) or fail loudly with recovery options (best case).

| Stage | Common Failure | Detection | Recovery |
|---|---|---|---|
| Source | URL returns 404, API rate limited | HTTP status check | Retry with backoff; alert after 3 failures |
| Ingest | Corrupt PDF, encoding error | Parse error catch | Log and skip item; flag for manual review |
| Process | Summarization produces garbage | Quality score check | Re-process with different parameters; flag if score still low |
| Store | Duplicate detection misses | Periodic dedup audit | Scheduled dedup sweep |
| Curate | No items pass priority filter | Empty digest check | Skip-silently if appropriate; alert if unexpected |
| Deliver | Telegram API error, rate limit | Delivery confirmation | Queue and retry; fallback to email |

### Step-by-Step Approach

**Step 1: Map your pipeline end-to-end**

Before automating, document every step:

```text
{{knowledge_base(action="ingest", source="pipeline-design-doc.md", format="markdown", metadata={"domain": "internal", "doc_type": "sop", "audience": "knowledge-team"})}}
```

**Step 2: Build the pipeline**

```text
{{digest_builder(action="create_pipeline", name="daily-intelligence", config={"stages": [{"name": "collect", "type": "research_agent", "agents": ["industry-trends", "competitor-monitor", "regulatory-tracker"], "schedule": "daily 05:00"}, {"name": "ingest", "type": "knowledge_ingest", "source": "collect.output", "chunking": "heading_based", "metadata_auto": true}, {"name": "process", "type": "summarize_and_classify", "input": "ingest.output", "summarize": true, "classify_by": ["sector", "urgency", "relevance"], "dedup": true}, {"name": "store", "type": "knowledge_store", "input": "process.output", "target_kb": "intelligence-kb"}, {"name": "curate", "type": "digest_curate", "input": "store.output", "template": "daily-intel-brief", "priority_filter": "P0,P1", "max_items": 15}, {"name": "deliver", "type": "telegram_send", "input": "curate.output", "chat_id": "intel-channel", "format": "telegram_standard"}], "error_handling": {"retry_count": 3, "retry_delay_seconds": 60, "alert_on_failure": true, "alert_channel": "ops-channel"}, "schedule": "daily 06:30", "timezone": "America/New_York"})}}
```

**Step 3: Test each stage independently**

Run each stage alone and verify its output before connecting them:

```text
{{research_agent(action="run", name="industry-trends")}}
```

Verify the output quality. Then:

```text
{{knowledge_base(action="ingest", source="research_output/industry-trends-2026-03-20.json", format="json", metadata={"domain": "research", "doc_type": "report", "source_agent": "industry-trends"})}}
```

Verify the ingestion. Continue stage by stage.

**Step 4: Connect and run end-to-end**

```text
{{digest_builder(action="run_pipeline", name="daily-intelligence", mode="test")}}
```

Review the test output. If any stage produced unexpected results, fix it before enabling the schedule.

**Step 5: Enable monitoring**

```text
{{digest_builder(action="configure", pipeline="daily-intelligence", setting="monitoring", value={"log_level": "info", "metrics": ["run_duration", "items_per_stage", "error_count", "delivery_confirmation"], "alert_rules": [{"condition": "error_count > 0", "action": "send_alert"}, {"condition": "items_collected < 3", "action": "log_warning"}, {"condition": "run_duration > 600", "action": "send_alert"}]})}}
```

### Practice Exercise

**Scenario:** Build an end-to-end content pipeline for a hospitality company that needs:

- Morning brief at 7:00 AM with today's guest operations
- Market intelligence digest every Monday at 8:00 AM
- Instant alerts for any negative guest review (any time)

**Task:**

1. Design the three pipelines
2. Configure error handling for each
3. Set up monitoring

Build the instant alert pipeline (most complex because it is event-driven):

```text
{{digest_builder(action="create_pipeline", name="review-alert", config={"stages": [{"name": "monitor", "type": "source_monitor", "sources": [{"type": "api", "endpoint": "review_platforms", "poll_interval_minutes": 15}], "trigger": "new_review"}, {"name": "analyze", "type": "sentiment_classify", "input": "monitor.output", "threshold": {"negative_below": 0.3}}, {"name": "alert", "type": "conditional_send", "condition": "analyze.sentiment < 0.3", "channel": "telegram", "chat_id": "ops-channel", "format": "alert", "icon": "warning", "template": "warning NEGATIVE REVIEW ALERT\n\nPlatform: {{source}}\nRating: {{rating}}/5\nProperty: {{property}}\nExcerpt: \"{{excerpt}}\"\n\nAction: Respond within 2 hours"}], "error_handling": {"retry_count": 2, "alert_on_failure": true}, "schedule": "continuous"})}}
```

**Self-check:** Test your pipeline with both a positive review (should not trigger alert) and a negative review (should trigger within 15 minutes). If the alert fires for a 4-star review with minor criticism, your sentiment threshold is too sensitive. If it misses a 2-star review, it is too lenient. Tune the threshold based on real examples.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Building the whole pipeline before testing any stage | Want to see it work end-to-end | Test each stage independently first; connect only after each works |
| No error handling | Happy path seems sufficient | Every stage needs: retry logic, error logging, failure alerts |
| No monitoring after deployment | "It works, ship it" | Monitor run duration, item counts, and error rates daily for the first week |
| Over-complex pipelines | Feature creep | Start with 3-4 stages; add complexity only when simple version proves insufficient |
| Not accounting for source outages | Assumes sources are always available | Build graceful degradation: skip unavailable sources, deliver partial digest with note |
