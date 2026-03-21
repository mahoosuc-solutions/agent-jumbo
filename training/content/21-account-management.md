# Module 21: Account Management

> **Learning Path:** Business Development Operator
> **Audience:** Sales operators, BizDev managers, account executives
> **Prerequisites:** customer_intake skill

---

## Lesson: Client Health Monitoring

### Why This Matters

Acquiring a new customer costs 5-7x more than retaining an existing one. Yet most sales organizations spend 90% of their energy on acquisition and 10% on retention. The result is a leaky bucket — you pour new customers in the top while existing customers drain out the bottom.

Client health monitoring fixes this by giving you an early warning system. Instead of finding out a client is unhappy when they send a cancellation notice, you detect the warning signs weeks or months earlier — when you can still act.

**The churn timeline you never see:**

```text
Month 1-3:  Client is happy, using the product, seeing results
Month 4-6:  Usage starts declining. Support tickets increase. They stop attending check-in calls.
Month 7-9:  Internal champion leaves. New manager questions the investment. They start evaluating alternatives.
Month 10:   They send the cancellation email. You are "blindsided."
```

You were not blindsided. The signals were there at month 4. You just were not watching.

**What unhealthy accounts cost:**

| Metric | Healthy Account | Unhealthy Account |
|---|---|---|
| Annual retention rate | 90-95% | 50-60% |
| Expansion revenue | 20-30% of base | 0% (contracting) |
| Support cost | Low, proactive requests | High, reactive complaints |
| Referral probability | 40-60% | 0% (may give negative referrals) |
| Lifetime value | 3-5 years | 12-18 months |

One unhealthy account that churns costs you the contract value PLUS the acquisition cost of finding a replacement PLUS the opportunity cost of the expansion revenue you will never see. For a $50k/year account, churn costs $150k-$250k in total economic impact.

### How to Think About It

**The Health Score Model**

A client health score is a composite metric that combines multiple signals into a single 0-100 score. Each signal is weighted by its predictive power for churn.

```text
Health Score (0-100)
  |
  +-- Usage Metrics (30% weight)
  |     - Feature adoption rate
  |     - Login frequency
  |     - Active users vs. licensed users
  |
  +-- Engagement Metrics (25% weight)
  |     - Check-in call attendance
  |     - Email response rate
  |     - Training participation
  |
  +-- Outcome Metrics (25% weight)
  |     - Are they achieving the KPIs from the proposal?
  |     - ROI realization rate
  |     - Process improvement measured
  |
  +-- Sentiment Metrics (20% weight)
        - NPS/satisfaction survey scores
        - Support ticket tone analysis
        - Stakeholder relationship strength
```

**Health Score Thresholds:**

| Score Range | Status | Action Required |
|---|---|---|
| 80-100 | Healthy | Standard check-in cadence. Look for expansion opportunities. |
| 60-79 | Watch | Increase check-in frequency. Identify and address emerging concerns. |
| 40-59 | At Risk | Escalate internally. Schedule executive check-in. Build remediation plan. |
| 0-39 | Critical | All-hands intervention. Executive-to-executive call. Offer concessions if needed. |

**Leading vs. Lagging Indicators**

Not all health signals are created equal. Some predict problems early (leading) and some confirm problems you already have (lagging):

| Indicator Type | Examples | Warning Window |
|---|---|---|
| Leading (act now) | Login frequency drops 30%, champion stops attending calls, support tickets increase 2x | 2-4 months before churn |
| Coincident (act fast) | NPS score drops, client requests "pause," reduces user count | 1-2 months before churn |
| Lagging (may be too late) | Formal cancellation request, non-payment, negative review posted | 0-30 days before churn |

Focus your monitoring on leading indicators. By the time you see lagging indicators, the relationship may be unrecoverable.

### Step-by-Step Approach

**Step 1: Set up health score tracking for each account**

```text
{{customer_lifecycle(action="get_health_score", customer="Northwind Distributors")}}
```

This pulls the current composite health score and its components. Review this weekly for every active account.

**Step 2: Configure automated health alerts**

```text
{{customer_lifecycle(action="update_customer", name="Northwind Distributors", data={"health_monitoring": {"alerts": [{"trigger": "usage_drop_30pct", "action": "notify_account_manager", "severity": "warning"}, {"trigger": "no_login_14_days", "action": "notify_account_manager_and_csm", "severity": "critical"}, {"trigger": "nps_below_7", "action": "escalate_to_director", "severity": "critical"}, {"trigger": "support_tickets_2x_increase", "action": "schedule_health_review", "severity": "warning"}, {"trigger": "champion_role_change", "action": "escalate_to_account_manager", "severity": "critical"}], "check_frequency": "daily"}})}}
```

**Step 3: Run a sentiment analysis on recent interactions**

```text
{{customer_lifecycle(action="get_health_score", customer="Northwind Distributors", data={"component": "sentiment", "sources": ["support_tickets", "email_correspondence", "call_notes"], "period": "last_30_days"})}}
```

Look for tonal shifts: a client who used to say "this is great" now says "it's fine" is sending a signal. A client who stops responding to emails is sending a louder one.

**Step 4: Document health review findings**

```text
{{customer_lifecycle(action="add_note", name="Northwind Distributors", data={"date": "2026-03-20", "type": "health_review", "health_score": 72, "components": {"usage": 85, "engagement": 65, "outcomes": 78, "sentiment": 58}, "concerns": ["Engagement score dropped 15 points — champion missed last 2 check-in calls", "Sentiment declining — last 3 support tickets had frustrated tone"], "actions": ["Reach out to champion directly to understand missed calls", "Review support tickets to identify recurring frustration source", "Prepare value recap showing ROI achieved so far"], "review_date_next": "2026-03-27"})}}
```

**Step 5: Intervene on at-risk accounts**

When a health score drops below 60, trigger an intervention:

```text
{{customer_lifecycle(action="update_customer", name="Northwind Distributors", data={"health_status": "watch", "intervention_plan": {"immediate": "Account manager calls champion within 24 hours", "week_1": "Schedule onsite visit to review outcomes and gather feedback", "week_2": "Present updated ROI analysis showing value delivered", "week_3": "Address any product or service gaps identified", "success_criteria": "Health score back above 75 within 30 days"}, "escalation_owner": "Account Manager - Sarah"})}}
```

### Practice Exercise

**Scenario:** You manage 5 active accounts. Here are their health signals from this week:

| Account | Usage Trend | Last Check-in | Support Tickets (30d) | Champion Status |
|---|---|---|---|---|
| Northwind Distributors | Stable | 5 days ago | 2 (normal) | Active, engaged |
| Summit Health Group | Down 25% | 3 weeks ago | 6 (up from 2) | Missed last 2 calls |
| Apex Financial | Up 10% | 2 days ago | 1 (normal) | Active, requesting new features |
| Cascade Retail | Down 40% | 6 weeks ago | 0 (concerning — stopped reporting issues) | Left the company |
| Wellington Legal | Stable | 1 week ago | 3 (normal) | Active |

**Task:**

1. Calculate approximate health scores for each account
2. Identify which accounts need immediate intervention
3. Create an intervention plan for the most critical account

```text
{{customer_lifecycle(action="get_health_score", customer="Cascade Retail")}}
```

```text
{{customer_lifecycle(action="update_customer", name="Cascade Retail", data={"health_status": "critical", "health_score": 28, "critical_signals": ["Usage down 40%", "No check-in for 6 weeks", "Zero support tickets (disengaged, not satisfied)", "Champion left company"], "intervention_plan": {"immediate": "Identify new stakeholder — call the executive sponsor today", "day_2": "Research who replaced the champion, request introduction", "week_1": "Schedule executive-to-executive call to reaffirm partnership", "week_2": "Present refreshed value analysis to new stakeholder", "week_3": "Propose re-onboarding with updated training for current team"}, "risk_level": "churn_imminent"})}}
```

**Self-check:** Cascade Retail is your most critical account. Every leading indicator is flashing red: usage collapse, no engagement, champion gone, and zero support tickets (which means they have stopped trying to make it work). Summit Health is your second priority — declining usage plus missed check-ins. Apex Financial is your healthiest account and a likely expansion candidate. If you prioritized your time on Apex because it felt productive, you would lose Cascade and Summit while Apex would have been fine without you.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Only checking health when renewal is approaching | Reactive mindset | Monitor health weekly. Problems caught early are cheap to fix. |
| Interpreting zero support tickets as satisfaction | Assumption that silence = happiness | Zero tickets from an active account often means they have given up. Investigate. |
| Focusing on healthy accounts because it feels good | Avoiding difficult conversations | Your at-risk accounts need you most. Healthy accounts can wait a week. |
| Not tracking champion changes | No process for monitoring key contacts | Set alerts for role changes. A new champion needs re-onboarding. |
| Using health scores without acting on them | Measurement without management | Every score below 60 needs a written intervention plan within 48 hours. |

---

## Lesson: Expansion and Upsell Identification

### Why This Matters

Expansion revenue — selling more to existing customers — is the most efficient revenue you can generate. The customer already trusts you, already uses your product, and already has budget allocated. Closing an expansion deal costs 60-70% less than acquiring a new customer and happens 2-3x faster.

Yet most account managers leave expansion revenue on the table because they do not systematically look for it. They wait for the customer to ask for more instead of proactively identifying opportunities.

**The expansion revenue equation:**

```text
Net Revenue Retention = (Starting Revenue + Expansion - Contraction - Churn) / Starting Revenue

Example:
  Starting revenue:  $500,000
  Expansion:         +$120,000 (24%)
  Contraction:       -$30,000 (6%)
  Churn:             -$40,000 (8%)
  Net retention:     $550,000 / $500,000 = 110%

110% NRR means you grow even without acquiring new customers.
100% NRR means you are replacing lost revenue with expansion (treading water).
Below 90% NRR means your bucket is leaking faster than you can fill it.
```

**Where expansion revenue hides:**

| Expansion Type | Signal | Example |
|---|---|---|
| More users | Team is growing, new departments interested | "Our marketing team saw what we did and wants to try it" |
| More features | Using core features heavily, asking about adjacent capabilities | "Can the system also handle purchase orders?" |
| More volume | Hitting usage limits, processing more than contracted | "We are doing 500 orders/day now instead of the 200 we scoped" |
| New use cases | Applying the tool to problems you did not originally scope | "We started using it for vendor management too" |
| New locations | Multi-site company expanding deployment | "Can we roll this out to our Chicago office?" |

### How to Think About It

**The Expansion Signal Detection Framework**

Expansion signals fall into three categories based on reliability:

```text
Strong Signals (80%+ expansion probability):
  - Customer explicitly asks about additional capabilities
  - Usage consistently exceeds contracted volume by 20%+
  - New department head requests a demo
  - Customer refers you to their peers

Moderate Signals (40-70% expansion probability):
  - Usage growing steadily month over month
  - Customer attending webinars and training beyond required
  - Positive NPS with written comments about additional needs
  - Customer's company announces growth (funding, hiring, new market)

Weak Signals (10-30% expansion probability):
  - Customer renews without negotiation (satisfied but may not be thinking about more)
  - Steady usage without growth (comfortable but not expanding)
  - Industry trend suggests adjacent needs
```

**The Timing Matrix**

When you propose expansion matters as much as what you propose:

| Customer Context | Timing Quality | Approach |
|---|---|---|
| Just achieved a major milestone with your product | Excellent | "You just hit [milestone]. Here is how companies like you typically expand next." |
| Approaching renewal (60-90 days out) | Good | Bundle expansion into renewal conversation for better pricing. |
| Recently resolved a major support issue | Poor | Wait 30 days. Asking for more money after a problem feels tone-deaf. |
| Champion just got promoted | Excellent | Their success with your product helped them. They want to replicate it. |
| Budget cycle beginning | Good | Position expansion in time for budget allocation. |
| Budget cycle ending with surplus | Excellent | "Use it or lose it" budget makes fast decisions possible. |

**The Cross-Sell Opportunity Map**

For each product or service you offer, map which others naturally pair with it:

```text
Core Product: AI Order Processing
  |
  +-- Natural Cross-Sell: AI Customer Communication (same data, different output)
  |
  +-- Natural Cross-Sell: Analytics Dashboard (uses data already being captured)
  |
  +-- Adjacent Cross-Sell: AI Vendor Management (similar process, different direction)
  |
  +-- Stretch Cross-Sell: Predictive Inventory (requires additional data sources)
```

### Step-by-Step Approach

**Step 1: Analyze usage patterns for expansion signals**

```text
{{customer_lifecycle(action="get_health_score", customer="Apex Financial", data={"component": "usage_trends", "period": "last_90_days", "include_growth_rate": true, "include_feature_adoption": true})}}
```

**Step 2: Identify specific expansion opportunities**

```text
{{customer_lifecycle(action="get_customer", name="Apex Financial")}}
```

Review their current scope against their usage. Are they bumping against limits? Using features you did not expect? Asking questions that suggest adjacent needs?

**Step 3: Build the expansion business case**

```text
{{business_xray_tool(action="analyze", company="Apex Financial", data={"analysis_type": "expansion_opportunity", "current_contract": {"value": 95000, "scope": "document processing automation", "users": 15, "volume": "2000 docs/month"}, "expansion_signals": [{"signal": "volume_at_180_pct_of_contracted", "detail": "Processing 3,600 docs/month vs. 2,000 contracted"}, {"signal": "feature_request", "detail": "Asked about automated compliance checking 3 times"}, {"signal": "new_department_interest", "detail": "Legal ops director requested demo last week"}], "opportunities": [{"type": "volume_upgrade", "estimated_value": 35000, "probability": "high"}, {"type": "new_feature", "estimated_value": 28000, "probability": "medium"}, {"type": "new_department", "estimated_value": 45000, "probability": "medium"}]})}}
```

**Step 4: Prepare the expansion proposal**

```text
{{sales_generator(action="create_proposal", customer="Apex Financial", data={"type": "expansion", "current_contract_value": 95000, "expansion_options": [{"name": "Volume Upgrade", "additional_value": 35000, "new_total": 130000, "justification": "Current usage at 180% of contract. Upgrade aligns contract with reality and removes overage risk."}, {"name": "Volume + Compliance Module", "additional_value": 63000, "new_total": 158000, "justification": "Volume upgrade plus automated compliance checking addresses the need you raised in our last 3 conversations."}, {"name": "Full Department Expansion", "additional_value": 108000, "new_total": 203000, "justification": "Extends the proven success from finance to legal ops. Same platform, shared administration, volume discounts applied."}], "recommended": "Volume + Compliance Module", "discount_for_commitment": "8% discount on new total for 2-year commitment"})}}
```

**Step 5: Log the expansion pipeline**

```text
{{customer_lifecycle(action="update_customer", name="Apex Financial", data={"expansion_pipeline": {"opportunities": [{"type": "volume_upgrade", "value": 35000, "stage": "proposal", "probability": 0.85}, {"type": "compliance_module", "value": 28000, "stage": "discovery", "probability": 0.55}, {"type": "legal_ops_expansion", "value": 45000, "stage": "qualified", "probability": 0.40}], "total_expansion_pipeline": 108000, "weighted_expansion_value": 59250, "target_close_date": "2026-05-15"}, "next_action": "Present expansion options in next check-in call", "next_action_date": "2026-03-25"})}}
```

### Practice Exercise

**Scenario:** You manage Apex Financial, a client that has been live for 8 months. Here is what you know:

- Current contract: $95,000/year for document processing automation (15 users)
- Current usage: 3,600 docs/month (contracted for 2,000)
- Health score: 88
- They recently hired 5 new analysts
- The legal ops director saw a demo and said "this would change our world"
- Their compliance team manually reviews 200 documents/week for regulatory adherence
- Renewal is in 4 months

**Task:**

1. Identify all expansion signals and categorize by strength
2. Calculate the total expansion opportunity value
3. Decide on timing — do you propose now or wait for renewal?
4. Build an expansion proposal with 3 options

```text
{{customer_lifecycle(action="update_customer", name="Apex Financial", data={"expansion_signals": {"strong": ["Volume at 180% of contract", "Legal ops director explicitly interested", "5 new analysts hired (more users needed)"], "moderate": ["Compliance team has manual review process — natural cross-sell", "Health score 88 — satisfied and engaged"], "timing": "excellent — propose now, do not wait for renewal. Volume is already over contract and legal ops interest is fresh. Bundling into renewal in 4 months risks losing momentum."})}}
```

**Self-check:** You should propose now, not wait for renewal. Three reasons: (1) they are already over their contracted volume — this is a conversation they expect, (2) the legal ops interest is hot right now and will cool in 4 months, (3) proposing now with a renewal bundle gives you a strong "commit now, save on renewal" narrative. Total expansion opportunity: $35k (volume) + $28k (compliance) + $45k (legal ops) = $108k, potentially doubling the account value.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Waiting for the customer to ask for more | Passive account management | Proactively identify and propose expansion. It is your job, not theirs. |
| Proposing expansion when health score is low | Desperation to grow revenue | Fix the health issue first. Expanding an unhappy customer makes them angrier. |
| Not tracking usage against contracted limits | No monitoring in place | Set automated alerts when usage hits 80% of contract. That is an expansion signal. |
| Proposing expansion without a business case | Assuming they will see the value | Build the ROI case for expansion just like you did for the original deal. |
| Bundling too many expansions at once | Wanting to maximize the deal | Start with the strongest signal. Land that, then propose the next one. |

---

## Lesson: Renewal Automation

### Why This Matters

Renewal is not a transaction. It is a relationship checkpoint. Every renewal is a moment where the customer actively decides whether to continue investing in you — and if you have not demonstrated value throughout the contract period, the renewal conversation becomes a negotiation at best and a cancellation at worst.

The problem is that most organizations treat renewal as a calendar event. Ninety days before expiration, someone remembers to send a renewal notice. By then, the customer has already decided. They have either been satisfied (and renewal is a formality) or dissatisfied (and the notice triggers the cancellation they have been considering).

Renewal automation transforms this from a reactive calendar event into a proactive, year-round process. It ensures that value is continuously demonstrated, issues are resolved before they fester, and the renewal conversation is a celebration of results rather than a negotiation.

**The renewal math:**

| Metric | Impact |
|---|---|
| 5% improvement in retention rate | 25-95% increase in profit (depending on industry) |
| Cost to renew an existing customer | 10-20% of original acquisition cost |
| Revenue from a retained customer over 5 years | 3-7x the original contract value |
| Customers who churn without warning | 40-60% (could have been saved with earlier intervention) |

### How to Think About It

**The Renewal Timeline**

Renewal is not a point in time. It is a process that spans the entire contract period:

```text
Contract Start                                                    Renewal Date
     |                                                                  |
     |-- Month 1-3: Onboarding & Value Realization --|                 |
     |                                                |                 |
     |-- Month 4-6: Steady State & Optimization -----|                 |
     |                                                |                 |
     |-- Month 7-9: Expansion & Deepening -----------|                 |
     |                                                |                 |
     |-- Month 10: Renewal Prep (90 days out) -------|                 |
     |                                                |                 |
     |-- Month 11: Renewal Proposal (60 days out) ---|                 |
     |                                                |                 |
     |-- Month 12: Signature (30 days out) ----------|                 |
```

**The Three Renewal Outcomes**

Every renewal ends in one of three outcomes. Your process should maximize outcome 1 and prevent outcome 3:

| Outcome | Characteristics | Your Goal |
|---|---|---|
| Expansion renewal | Customer renews at higher value — more users, features, or scope | 30-40% of renewals |
| Flat renewal | Customer renews at same value — satisfied but not growing | 40-50% of renewals |
| Contraction or churn | Customer reduces scope or cancels — value not demonstrated | Under 15% of renewals |

**Churn Prevention Triggers**

Automated triggers that fire early warning signals before churn becomes inevitable:

```text
Trigger                              Warning Level    Time to Act
Usage drops below 50% of contract   Critical         Immediate — schedule call within 48 hours
Champion leaves company             Critical         Immediate — identify new stakeholder
NPS score drops below 6             High             Within 1 week — investigate root cause
No login for 21+ days               High             Within 3 days — outreach to primary contact
Support tickets increase 3x         Medium           Within 1 week — review ticket themes
Invoice payment delayed 30+ days    Medium           Coordinate with finance, check satisfaction
Customer stops attending check-ins  Medium           Within 1 week — try different contact or format
Competitor mentioned in support     Critical         Immediate — competitive response plan
```

**The Value Recap**

Before every renewal conversation, prepare a value recap that shows the customer exactly what they received for their investment:

```text
Value Recap Structure:
  1. Investment Summary — What they paid
  2. Outcomes Delivered — What they got (in their KPIs, not your features)
  3. ROI Calculation — Dollar value of improvements
  4. Comparison to Proposal — Did you deliver what you promised?
  5. Forward Look — What comes next if they renew
```

### Step-by-Step Approach

**Step 1: Set up renewal tracking for all accounts**

```text
{{customer_lifecycle(action="get_pipeline", stage="renewal", data={"filter": "renewal_within_90_days"})}}
```

This surfaces every account with a renewal in the next 90 days so you can begin preparation.

**Step 2: Configure automated renewal reminders**

```text
{{customer_lifecycle(action="update_customer", name="Northwind Distributors", data={"renewal_tracking": {"contract_end_date": "2026-07-15", "renewal_reminders": [{"days_before": 120, "action": "begin_value_recap_preparation", "owner": "account_manager"}, {"days_before": 90, "action": "schedule_renewal_planning_meeting_internal", "owner": "account_manager"}, {"days_before": 75, "action": "send_value_recap_to_customer", "owner": "account_manager"}, {"days_before": 60, "action": "present_renewal_proposal", "owner": "account_manager"}, {"days_before": 45, "action": "follow_up_on_proposal", "owner": "account_manager"}, {"days_before": 30, "action": "escalate_if_unsigned", "owner": "director"}, {"days_before": 14, "action": "final_signature_push", "owner": "account_manager"}], "auto_renewal_clause": false, "renewal_target": "expansion"}})}}
```

**Step 3: Generate the value recap**

```text
{{sales_generator(action="create_proposal", customer="Northwind Distributors", data={"type": "value_recap", "contract_period": "2025-07-15 to 2026-07-15", "investment": 180000, "outcomes": [{"metric": "Order processing time", "before": "50 min/order", "after": "12 min/order", "improvement": "76% reduction"}, {"metric": "Quote error rate", "before": "12%", "after": "2.1%", "improvement": "82.5% reduction"}, {"metric": "Orders processed daily", "before": 180, "after": 310, "improvement": "72% increase"}, {"metric": "Staff overtime hours", "before": "120 hrs/month", "after": "15 hrs/month", "improvement": "87.5% reduction"}], "roi_calculation": {"annual_savings": 487000, "investment": 180000, "roi_percentage": "271%", "payback_period": "4.4 months"}, "value_delivered_vs_proposed": "Exceeded proposal targets on all 4 KPIs"})}}
```

**Step 4: Build the renewal proposal with expansion options**

```text
{{sales_generator(action="create_proposal", customer="Northwind Distributors", data={"type": "renewal", "current_contract": 180000, "options": [{"name": "Standard Renewal", "value": 180000, "scope": "Same scope, continued service", "incentive": "5% loyalty discount for 2-year term"}, {"name": "Growth Renewal", "value": 225000, "scope": "Current scope + analytics dashboard + vendor management module", "incentive": "10% discount on new modules for renewal commitment"}, {"name": "Enterprise Renewal", "value": 310000, "scope": "Full suite expansion to all departments + priority support + quarterly business reviews", "incentive": "15% discount on total for 3-year commitment"}], "recommended": "Growth Renewal", "recommendation_reason": "Addresses analytics needs expressed in Q3 check-ins and aligns with their vendor management initiative launching in Q4"})}}
```

**Step 5: Track renewal progress**

```text
{{customer_lifecycle(action="update_customer", name="Northwind Distributors", data={"renewal_status": "proposal_presented", "renewal_proposal_value": 225000, "renewal_option_selected": "Growth Renewal", "renewal_discussion_notes": "CFO was impressed by value recap. Wants to discuss Growth Renewal with COO. Follow up scheduled for March 28.", "renewal_probability": 0.85, "renewal_risk_factors": ["COO may push for Standard to save budget"], "next_action": "Prepare COO-specific value analysis focusing on vendor management ROI", "next_action_date": "2026-03-27"})}}
```

**Step 6: Set up churn prevention for at-risk renewals**

```text
{{customer_lifecycle(action="update_customer", name="Summit Health Group", data={"renewal_status": "at_risk", "contract_end_date": "2026-06-01", "churn_risk_factors": ["Health score 52", "Usage down 25%", "Champion missed 2 check-ins", "Support ticket volume doubled"], "churn_prevention_plan": {"week_1": "Account manager meets champion in person — understand root cause of disengagement", "week_2": "Present tailored remediation plan addressing specific complaints", "week_3": "Offer 30-day complimentary premium support to demonstrate commitment", "week_4": "Re-assess health score. If improved, proceed with renewal. If not, escalate to executive.", "contingency": "If churn is likely, offer reduced-scope contract to maintain relationship"}, "escalation_trigger": "If health score does not improve to 65+ within 30 days"})}}
```

### Practice Exercise

**Scenario:** You have 4 accounts renewing in the next 90 days:

| Account | Renewal Date | Contract Value | Health Score | Usage vs. Contract | Expansion Signals |
|---|---|---|---|---|---|
| Northwind Distributors | July 15 | $180,000 | 72 | 110% | Analytics interest |
| Summit Health Group | June 1 | $95,000 | 52 | 75% | None |
| Apex Financial | August 1 | $95,000 | 88 | 180% | Strong — multiple |
| Wellington Legal | July 1 | $68,000 | 76 | 95% | Minor — template request |

**Task:**

1. Prioritize these renewals by risk and opportunity
2. Create a renewal strategy for each account (expand, maintain, or save)
3. Build a value recap for the highest-risk account
4. Calculate your expected renewal revenue

```text
{{customer_lifecycle(action="get_pipeline", stage="renewal", data={"accounts": [{"name": "Summit Health Group", "strategy": "save", "priority": 1, "action": "Immediate intervention — health score critical, churn likely without action"}, {"name": "Apex Financial", "strategy": "expand", "priority": 2, "action": "Present expansion proposal ASAP — usage at 180% is the strongest signal"}, {"name": "Northwind Distributors", "strategy": "expand_cautious", "priority": 3, "action": "Address health score dip first, then propose growth renewal"}, {"name": "Wellington Legal", "strategy": "maintain", "priority": 4, "action": "Standard renewal with minor scope addition for template feature"}]})}}
```

**Self-check:** Your expected renewal revenue calculation: Summit ($95k x 60% probability = $57k), Apex ($140k expanded x 90% = $126k), Northwind ($200k expanded x 75% = $150k), Wellington ($72k with template add-on x 90% = $64.8k). Total expected: $397,800 vs. current base of $438,000. Without the Apex expansion, you are contracting. Summit is the difference between hitting and missing your retention target — saving that one account is worth more than any prospecting you could do this quarter.

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Starting renewal conversations 30 days before expiration | No automated reminders, reactive approach | Begin the renewal process 120 days out. The conversation at 30 days should be about signing, not selling. |
| Not preparing a value recap | Assumes the customer remembers the value | Customers forget. Show them the numbers. A value recap is your strongest renewal tool. |
| Treating renewal as a formality | Assuming satisfied customers automatically renew | Every renewal is a decision. Make the case. Competitors are always reaching out to your customers. |
| Offering discounts at first sign of resistance | Panic about losing the account | Understand the objection first. Often it is not about price — it is about value or fit. Discounts given too easily train customers to negotiate hard every time. |
| Not having a churn prevention plan | No process for at-risk accounts | Every account under health score 60 with a renewal in 90 days needs a written save plan within 48 hours. |
