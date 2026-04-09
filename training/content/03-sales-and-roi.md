# Module 3: Sales & ROI

> **Learning Path:** AI Solution Architect
> **Audience:** Non-technical business operators learning AI solution architecture
> **Prerequisites:** Completed Module 2: Solution Design Mastery

---

## Lesson: ROI Calculation Methods

### Why This Matters

The number one reason AI projects get cancelled before they start is not technical failure. It is the inability to prove value in a language stakeholders trust: money. If you cannot quantify the return on investment for an AI solution, you are asking a business to gamble. Most will not.

What goes wrong without this skill:

- **Vague promises lose deals** — "It will save you time" is not a business case. "It will save 42 hours per week at $35/hour, paying for itself in 4.2 months" is.
- **Wrong stakeholder, wrong metric** — A CFO who wants payback period gets a slide about "innovation." The deal stalls.
- **Scope creep from unclear value** — Without a tied-to-dollars scope, the client keeps adding features because nothing feels "done."
- **Post-launch disappointment** — If you never defined what "good" looks like in financial terms, the client invents their own expectations.

**The cost of getting ROI wrong:**

| ROI Mistake | What Happens | Business Consequence |
|---|---|---|
| No ROI calculation at all | Client cannot justify the budget internally | Deal dies in procurement |
| Overstated ROI | Client expects 10x, gets 2x | Perceived failure despite real value |
| Single-scenario projection | One optimistic number with no range | Client feels misled when reality varies |
| Ignoring adoption curve | Full ROI assumed from day one | Year 1 looks like a failure |
| Wrong value category | You measure speed, they care about errors | Misaligned success criteria |

### How to Think About It

**The Three Value Levers**

Every AI solution creates measurable value through exactly three mechanisms. Your ROI model must identify which levers apply and quantify each one independently.

```text
VALUE LEVER 1: LABOR SAVINGS
Formula: Hours Saved = (manual_time - automated_time) x frequency x staff_count
Dollar Value = Hours Saved x blended_hourly_rate

Example:
  Manual invoice processing: 12 min per invoice
  AI-assisted processing: 2 min per invoice
  Volume: 400 invoices/month
  Staff hourly rate: $28/hr
  Monthly savings: (10 min x 400) / 60 x $28 = $1,867/month

VALUE LEVER 2: ERROR REDUCTION
Formula: Error Cost Avoided = error_rate x cost_per_error x volume
Dollar Value = (old_error_rate - new_error_rate) x cost_per_error x volume

Example:
  Current data entry error rate: 8%
  AI-assisted error rate: 1.5%
  Cost per error (rework + downstream impact): $45
  Volume: 2,000 entries/month
  Monthly savings: (0.08 - 0.015) x $45 x 2,000 = $5,850/month

VALUE LEVER 3: SPEED / OPPORTUNITY GAINS
Formula: Opportunity Value = time_saved_per_cycle x opportunity_cost_per_unit_time
Dollar Value = cycles_per_period x time_saved x revenue_per_unit_time

Example:
  Proposal turnaround: reduced from 5 days to 1 day
  Win rate increase from faster response: 12%
  Average deal value: $8,500
  Proposals per month: 15
  Monthly gain: 15 x 0.12 x $8,500 = $15,300/month
```

**Adoption Curve Reality Check**

New systems never hit 100% usage on day one. Your ROI projections must account for the adoption curve or you will over-promise Year 1 returns and destroy credibility.

```text
ADOPTION CURVE MODEL

Year 1:  40% adoption  -->  ROI x 0.40
Year 3:  80% adoption  -->  ROI x 0.80
Year 5:  95% adoption  -->  ROI x 0.95

Applied to a $5,000/month base ROI:

Year 1:  $5,000 x 0.40 = $2,000/month = $24,000/year
Year 3:  $5,000 x 0.80 = $4,000/month = $48,000/year
Year 5:  $5,000 x 0.95 = $4,750/month = $57,000/year

5-Year Cumulative ROI (with adoption curve): $228,000
5-Year Cumulative ROI (without curve):       $300,000
Difference: $72,000 -- this is the credibility gap you avoid
```

**Sensitivity Analysis: Three Scenarios**

Never present a single number. Always present three scenarios. This builds trust and shows you have thought through variability.

```text
SCENARIO FRAMEWORK

               WORST CASE     BASE CASE      BEST CASE
Adoption       30%            40%            55%
Time savings   -20% of est    as estimated   +15% of est
Error reduction -25% of est   as estimated   +20% of est
Volume growth  flat           +10%/year      +20%/year

                 Year 1        Year 3         Year 5
Worst case       $18,000       $38,000        $48,000
Base case        $24,000       $48,000        $57,000
Best case        $33,000       $62,000        $74,000
```

**Stakeholder-Specific ROI Framing**

The same ROI data must be presented differently depending on who you are talking to.

| Stakeholder | Primary Metric | Secondary Metric | What They Fear |
|---|---|---|---|
| CFO | Payback period (months to break even) | IRR, NPV | Sunk cost, hidden expenses |
| CEO | Strategic value, competitive advantage | Revenue impact, market position | Falling behind competitors |
| Ops Manager | Hours saved per week, error reduction | Ease of transition, staff impact | Disruption, staff pushback |
| IT Director | Integration cost, maintenance burden | Security, data governance | Technical debt, vendor lock-in |

```text
FRAMING GUIDE

For the CFO:
  "The solution costs $36,000 to implement. At base-case adoption,
   it saves $2,000/month in Year 1. Payback period: 18 months.
   By Year 3, cumulative savings exceed $100,000."

For the CEO:
  "Your competitors are responding to proposals in 1 day.
   You are responding in 5. This solution closes that gap
   and captures an estimated $15,300/month in deals you
   are currently losing to faster competitors."

For the Ops Manager:
  "Your team spends 67 hours per week on invoice processing.
   This solution cuts that to 13 hours. Your staff can redirect
   54 hours per week to customer-facing work. Rollout is phased
   so there is no big-bang disruption."
```

### Step-by-Step Approach

**Step 1: Gather the raw numbers from discovery**

Pull the process data you captured during discovery using Agent Mahoo tools:

```text
{{process_analyzer(action="get_metrics", customer_id="acme-corp")}}
```

This returns the task inventory with time estimates, frequencies, error rates, and staff counts you recorded during the discovery phase.

**Step 2: Calculate each value lever**

For each automatable task identified in your solution design, calculate all applicable value levers:

```text
{{roi_calculator(
  action="calculate",
  customer_id="acme-corp",
  tasks=[
    {
      "name": "Invoice Processing",
      "lever": "labor_savings",
      "manual_minutes": 12,
      "automated_minutes": 2,
      "frequency_per_month": 400,
      "hourly_rate": 28
    },
    {
      "name": "Data Entry QA",
      "lever": "error_reduction",
      "current_error_rate": 0.08,
      "projected_error_rate": 0.015,
      "cost_per_error": 45,
      "volume_per_month": 2000
    }
  ]
)}}
```

**Step 3: Apply the adoption curve**

```text
{{roi_calculator(
  action="project",
  customer_id="acme-corp",
  projection_years=5,
  adoption_curve={
    "year_1": 0.40,
    "year_3": 0.80,
    "year_5": 0.95
  },
  include_sensitivity=true
)}}
```

**Step 4: Generate stakeholder-specific summaries**

```text
{{roi_calculator(
  action="format",
  customer_id="acme-corp",
  audience="cfo",
  format="executive_summary"
)}}
```

Repeat with `audience="ceo"` and `audience="ops_manager"` to generate each version.

**Step 5: Store the ROI model for the proposal**

```text
{{customer_record(
  action="update",
  customer_id="acme-corp",
  section="roi_model",
  data={
    "total_monthly_value": 7717,
    "payback_months": 18,
    "year_1_roi": 24000,
    "year_3_cumulative": 120000,
    "year_5_cumulative": 228000,
    "confidence": "base_case"
  }
)}}
```

### What Good Looks Like

**A strong ROI model has these properties:**

- Every number traces back to a discovery finding (no invented data)
- Three scenarios presented (worst / base / best) -- never a single number
- Adoption curve applied -- Year 1 is realistic, not theoretical max
- Implementation costs included (your fee, client staff time for training, transition productivity dip)
- Payback period is under 24 months for base case (if it is longer, the deal is hard to close)
- Ongoing costs are explicit (monthly platform fees, maintenance, prompt tuning)

**Common mistakes to avoid:**

| Mistake | Why It Happens | How to Fix |
|---|---|---|
| Using theoretical max as the estimate | Wanting to impress the client | Always lead with base case, show best case as upside |
| Forgetting implementation costs | Focused on savings, not spend | Add a "Total Cost of Ownership" section: implementation + Year 1 run cost |
| Counting the same value twice | Labor savings AND speed gains on the same task | Each task maps to its primary lever; secondary levers are additive only if truly independent |
| Ignoring the transition dip | Assumes instant productivity | Model a 15-20% productivity dip in month 1-2 of each phase |
| No sensitivity analysis | Seems like extra work | It is the single most credibility-building element of your proposal |

### Practice Exercise

Run this exercise using your own Agent Mahoo instance:

1. Pick any existing customer record (or create a test one)
2. Identify 3 tasks from their process map
3. For each task, calculate at least one value lever using `{{roi_calculator}}`
4. Generate a 5-year projection with adoption curve
5. Create two stakeholder summaries: one for a CFO, one for an Ops Manager
6. Compare: does the CFO version lead with payback period? Does the Ops version lead with hours saved?

**Success criteria for the exercise:**

- Your worst-case scenario still shows positive ROI within 24 months
- Your base case and worst case differ by at least 20% (if they are closer, your model is not accounting for real variability)
- You can explain every number by pointing to a specific discovery finding

---

## Lesson: Using Sales Generator

### Why This Matters

A good ROI model that sits in a spreadsheet does not close deals. The ROI needs to live inside a proposal that tells a story: here is your pain, here is the fix, here is what it costs, here is what happens if you do nothing.

What goes wrong without a structured sales process:

- **Generic proposals lose to specific ones** — A competitor who tailors their proposal to the client's exact pain points will win even with an inferior solution
- **Missing risk framing** — If you only talk about gains, the client thinks "nice to have." If you also show the cost of inaction, it becomes "need to have."
- **Pricing disconnected from value** — Cost-plus pricing ("it takes us 80 hours at $150/hour") invites negotiation. Value-based pricing ("this saves you $7,700/month for $2,500/month") frames the conversation around ROI.
- **No urgency** — Without a timeline and milestones, proposals sit in email for weeks

**The proposal that loses vs. the proposal that wins:**

| Losing Proposal | Winning Proposal |
|---|---|
| Starts with "About Our Company" | Starts with "Your Current Situation" |
| Lists features | Maps features to the client's specific pain points |
| One price, take it or leave it | Tiered pricing aligned to phases |
| "AI will improve your business" | "You will save 54 hours/week in invoice processing" |
| No timeline | Phase 1 delivers first value in 4 weeks |
| No risk framing | "Every month without this costs you $7,700 in avoidable waste" |

### How to Think About It

**The Winning Proposal Structure**

Every proposal follows this 7-section arc. Each section has a specific job:

```text
PROPOSAL STRUCTURE

1. EXECUTIVE SUMMARY (1 page)
   Job: Give the busy decision-maker the full story in 60 seconds
   Contains: Problem, solution, ROI, timeline, investment
   Rule: Write this LAST, after everything else is solid

2. PROBLEM STATEMENT (1-2 pages)
   Job: Prove you understand their pain better than they do
   Contains: Current state metrics, cost of current process,
             specific friction points (use their words from discovery)
   Rule: Use direct quotes from discovery interviews

3. SOLUTION OVERVIEW (2-3 pages)
   Job: Show what you will build and how it maps to their problems
   Contains: Architecture overview (non-technical), workflow diagrams,
             task-by-task mapping (problem --> solution)
   Rule: Every feature must trace to a stated problem

4. ROI ANALYSIS (1-2 pages)
   Job: Prove the investment makes financial sense
   Contains: Value lever calculations, 3-scenario projection,
             payback period, stakeholder-specific framing
   Rule: Link to the ROI model from the previous lesson

5. IMPLEMENTATION ROADMAP (1-2 pages)
   Job: Show the path from signature to value
   Contains: Phased timeline, milestones, what the client
             needs to provide, when they see first results
   Rule: Phase 1 must deliver visible value within 4 weeks

6. PRICING (1 page)
   Job: Present investment in context of value
   Contains: Phased pricing, what each phase includes,
             ongoing costs, what is NOT included
   Rule: Price always appears AFTER ROI analysis

7. TERMS AND NEXT STEPS (1 page)
   Job: Make it easy to say yes
   Contains: Validity period, acceptance process,
             what happens immediately after signing
   Rule: Include a clear call to action with a date
```

**Pricing Strategy Decision Tree**

```text
START: What is the client's buying style?
  |
  Q1: Is the client price-sensitive or value-sensitive?
  |     |
  |     PRICE-SENSITIVE --> Q2: Is there competitive pressure?
  |     |                     |
  |     |                     YES --> COMPETITIVE PRICING
  |     |                     |       (match or beat competitors,
  |     |                     |        differentiate on scope/quality)
  |     |                     |
  |     |                     NO --> COST-PLUS PRICING
  |     |                            (your cost + margin, transparent)
  |     |                            Best for: commodity services,
  |     |                            established relationships
  |     |
  |     VALUE-SENSITIVE --> VALUE-BASED PRICING
  |                         (price as % of value delivered)
  |                         Best for: unique solutions, strong ROI,
  |                         strategic engagements
  |
  PRICING MODEL GUIDE:
  |
  |  Strategy        Formula                    When to Use
  |  --------------- -------------------------- ---------------------------
  |  Value-based     10-30% of Year 1 ROI       Strong, provable ROI
  |  Cost-plus       Hours x Rate + 20-40%      Commodity work, T&M clients
  |  Competitive     Market rate +/- 10%        Crowded market, RFP process
  |  Tiered          3 options (good/better/     Client wants to choose
  |                  best)                       scope and budget
```

**Risk Framing: The Cost of Inaction**

This is the most under-used sales technique in AI consulting. You must not only show what they gain, but what they lose by waiting.

```text
RISK FRAMING FORMULA

Monthly Cost of Inaction = sum of all value levers / month

"Every month you delay this decision costs your business
 $7,717 in avoidable labor costs, preventable errors,
 and lost opportunities."

"In the 3 months since our first conversation, the cost
 of inaction has been approximately $23,150."

"Your competitor [if known] implemented a similar solution
 6 months ago. That is a $46,300 head start."
```

### Step-by-Step Approach

**Step 1: Generate the proposal draft**

Use the sales generator with your customer record and ROI model:

```text
{{sales_generator(
  action="create_proposal",
  customer_id="acme-corp",
  template="ai_solution",
  sections=[
    "executive_summary",
    "problem_statement",
    "solution_overview",
    "roi_analysis",
    "implementation_roadmap",
    "pricing",
    "terms"
  ],
  pricing_strategy="value_based",
  include_risk_framing=true
)}}
```

This pulls from the customer record, discovery notes, solution design, and ROI model to populate every section.

**Step 2: Customize the problem statement with discovery quotes**

```text
{{sales_generator(
  action="customize_section",
  customer_id="acme-corp",
  section="problem_statement",
  source="discovery_notes",
  include_quotes=true,
  include_metrics=true
)}}
```

**Step 3: Set pricing tiers**

```text
{{sales_generator(
  action="set_pricing",
  customer_id="acme-corp",
  tiers=[
    {
      "name": "Foundation",
      "phases": [1],
      "monthly": 1500,
      "setup": 8000,
      "description": "Core automation: invoice processing + data entry QA"
    },
    {
      "name": "Professional",
      "phases": [1, 2],
      "monthly": 2500,
      "setup": 18000,
      "description": "Foundation + proposal generation + reporting dashboard"
    },
    {
      "name": "Enterprise",
      "phases": [1, 2, 3],
      "monthly": 3500,
      "setup": 28000,
      "description": "Professional + predictive analytics + custom integrations"
    }
  ]
)}}
```

**Step 4: Add the cost-of-inaction section**

```text
{{sales_generator(
  action="add_risk_framing",
  customer_id="acme-corp",
  monthly_cost_of_inaction=7717,
  competitor_context="Industry peers are automating similar workflows",
  urgency_date="2026-Q2"
)}}
```

**Step 5: Export the proposal**

```text
{{sales_generator(
  action="export",
  customer_id="acme-corp",
  format="pdf",
  include_cover_page=true,
  include_appendix=true
)}}
```

### What Good Looks Like

**A strong proposal exhibits these qualities:**

- The executive summary can stand alone -- a decision-maker who reads nothing else still understands the opportunity
- The problem statement uses the client's own language (direct quotes from discovery)
- Every proposed feature traces directly to a stated pain point
- Pricing appears after the ROI analysis, so the investment is framed by the return
- The implementation roadmap shows first value within 4 weeks
- The cost of inaction is quantified in dollars per month
- There are exactly 3 pricing tiers (fewer feels like no choice, more causes decision paralysis)
- Terms include a validity period (proposals expire in 14-21 days to maintain urgency)

**Common mistakes to avoid:**

| Mistake | Why It Hurts | Fix |
|---|---|---|
| Leading with your company bio | Client does not care about you yet; they care about their problem | Move credentials to an appendix |
| Features without problem mapping | Feels like a generic pitch | Every feature gets a "This solves: [specific pain point]" line |
| Single price point | Client can only say yes or no | Three tiers give them a sense of control |
| Pricing before ROI | Investment feels expensive without context | Always present value first, price second |
| No expiration date | Proposal sits for months, context goes stale | 14-21 day validity with a specific follow-up date |
| Forgetting ongoing costs | Client is surprised by month 2 invoice | Separate setup cost from monthly run cost explicitly |

### Practice Exercise

Using Agent Mahoo, complete this end-to-end proposal workflow:

1. Select an existing customer with a completed ROI model
2. Run `{{sales_generator(action="create_proposal", ...)}}` with all 7 sections
3. Review the problem statement -- does it contain at least 2 direct quotes from discovery?
4. Create 3 pricing tiers where the middle tier is the one you want them to buy
5. Add risk framing with a specific dollar-per-month cost of inaction
6. Export to PDF and review: can someone who has never met the client understand the full story from the executive summary alone?

**Checklist for your finished proposal:**

- [ ] Executive summary fits on one page
- [ ] Problem statement uses client's own words
- [ ] Every feature maps to a specific pain point
- [ ] ROI shows three scenarios
- [ ] Price appears after ROI
- [ ] Three pricing tiers
- [ ] Implementation shows value in first 4 weeks
- [ ] Cost of inaction is quantified
- [ ] Proposal has an expiration date

---

## Lesson: Roadmap Planning

### Why This Matters

A signed proposal is a promise. The roadmap is how you keep it. Without a structured implementation plan, AI projects follow a depressingly predictable arc: excitement at kickoff, confusion by week 3, panic by week 8, and either a messy late delivery or quiet cancellation.

What goes wrong without structured roadmap planning:

- **Big-bang delivery** — Everything ships at once after months of development. Client has seen nothing working until launch day. Bugs, misaligned expectations, and change requests pile up simultaneously.
- **No visible progress** — Client asks "what have you done?" at week 6 and you say "we are building the foundation." They hear "nothing."
- **Dependency blindness** — You start Phase 2 before Phase 1 outputs are stable, and failures cascade through the entire project.
- **Activity-based milestones** — "Complete data integration" is an activity. "System processes 100 invoices with less than 2% error rate" is a milestone. Activities can be "done" while the solution is still broken.

**The phased delivery advantage:**

| Approach | Client Experience | Risk Profile |
|---|---|---|
| Big-bang (all at once) | Sees nothing for 12 weeks, then everything | Maximum risk: one failure blocks entire launch |
| Phased (incremental) | Sees working value at week 4, then every 4 weeks | Minimum risk: each phase is self-contained and useful |

### How to Think About It

**The Three-Phase Pattern for AI Projects**

Most AI solutions fit a three-phase pattern. Customize the specifics, but keep the structure.

```text
PHASE 1: QUICK WINS (Weeks 1-4)
Goal: Deliver visible, working value fast
What belongs here:
  - Simplest automation with clearest ROI
  - Tasks with highest volume and lowest complexity
  - Features the client mentioned most in discovery
  - Things that make staff say "finally, I don't have to do that anymore"
Why it matters:
  - Builds trust ("they actually delivered something")
  - Generates internal champions ("this saved me 3 hours last week")
  - Provides real-world data for tuning Phases 2 and 3
Success looks like: Client's team is using the tool daily

PHASE 2: CORE AUTOMATION (Weeks 5-12)
Goal: Deliver the main value proposition
What belongs here:
  - Primary automation workflows
  - Integrations with existing systems
  - Hybrid human/AI workflows with review steps
  - Dashboard and reporting
Why it matters:
  - This is where 60-70% of the ROI lives
  - Complex enough to need Phase 1 data and feedback
  - Long enough to iterate on prompt quality
Success looks like: ROI metrics are trackable and trending positive

PHASE 3: OPTIMIZATION (Weeks 13-20)
Goal: Maximize value and set up long-term success
What belongs here:
  - Advanced features (predictive analytics, complex routing)
  - Performance optimization (speed, cost, accuracy tuning)
  - Edge case handling
  - Staff training and documentation
  - Handover to client's ongoing operations
Why it matters:
  - Only possible with real usage data from Phases 1-2
  - This is where good becomes great
  - Transition from "project" to "ongoing capability"
Success looks like: Client can operate and maintain without you
```

**Dependency Management**

Before sequencing tasks, map what depends on what. A dependency is anything where Task B cannot start or succeed without Task A being complete.

```text
DEPENDENCY MAP TEMPLATE

Task                          Depends On               Phase
---------------------------   -----------------------  -----
API integration setup         Client provides creds    1
Invoice processing workflow   API integration          1
Error rate baseline           2 weeks of live data     1
Proposal generation           Template library built   2
Dashboard                     Data pipeline running    2
Accuracy tuning               Error rate baseline      2
Predictive model              3+ months of data        3
Staff self-service training   All workflows stable     3

DEPENDENCY CHAIN:
  Client creds --> API setup --> Invoice workflow --> Live data
       --> Error baseline --> Accuracy tuning

  Template library --> Proposal generation --|
  API setup --> Data pipeline --> Dashboard --|-- Phase 2
                                              |  complete
  Live data (3 months) --> Predictive model -- Phase 3
```

**Milestone Definition: Outcomes, Not Activities**

| Bad Milestone (Activity) | Good Milestone (Outcome) |
|---|---|
| "Complete API integration" | "System successfully processes live data from client's CRM" |
| "Build invoice workflow" | "50 invoices processed with less than 3% error rate" |
| "Create dashboard" | "Ops manager reviews daily metrics without requesting manual reports" |
| "Train staff" | "80% of staff complete a task independently without support" |
| "Optimize prompts" | "Average response quality score exceeds 4.2/5.0" |

### Step-by-Step Approach

**Step 1: Pull the task list from your solution design**

```text
{{process_analyzer(
  action="get_automatable_tasks",
  customer_id="acme-corp",
  sort_by="roi_impact"
)}}
```

**Step 2: Map dependencies**

```text
{{roadmap_planner(
  action="map_dependencies",
  customer_id="acme-corp",
  tasks=[
    {"id": "api-setup", "depends_on": ["client-creds"], "complexity": "low"},
    {"id": "invoice-workflow", "depends_on": ["api-setup"], "complexity": "medium"},
    {"id": "error-baseline", "depends_on": ["invoice-workflow", "2-weeks-live"], "complexity": "low"},
    {"id": "dashboard", "depends_on": ["data-pipeline"], "complexity": "medium"},
    {"id": "accuracy-tuning", "depends_on": ["error-baseline"], "complexity": "high"},
    {"id": "predictive-model", "depends_on": ["3-months-data"], "complexity": "high"}
  ]
)}}
```

**Step 3: Generate the phased roadmap**

```text
{{roadmap_planner(
  action="create",
  customer_id="acme-corp",
  phases=[
    {
      "name": "Quick Wins",
      "weeks": "1-4",
      "tasks": ["api-setup", "invoice-workflow"],
      "milestone": "50 invoices processed with <3% error rate"
    },
    {
      "name": "Core Automation",
      "weeks": "5-12",
      "tasks": ["error-baseline", "dashboard", "proposal-gen"],
      "milestone": "All primary workflows live, ROI tracking active"
    },
    {
      "name": "Optimization",
      "weeks": "13-20",
      "tasks": ["accuracy-tuning", "predictive-model", "training"],
      "milestone": "Client operates independently, all KPIs met"
    }
  ]
)}}
```

**Step 4: Define sprint-level detail for Phase 1**

```text
{{roadmap_planner(
  action="create_sprints",
  customer_id="acme-corp",
  phase=1,
  sprint_length_weeks=2,
  sprints=[
    {
      "sprint": 1,
      "goals": ["API credentials received", "Integration environment set up", "First test data flowing"],
      "deliverable": "Live data connection confirmed"
    },
    {
      "sprint": 2,
      "goals": ["Invoice workflow configured", "10 test invoices processed", "Error rate measured"],
      "deliverable": "Invoice processing live with 50+ documents"
    }
  ]
)}}
```

**Step 5: Attach the roadmap to the proposal**

```text
{{sales_generator(
  action="attach_roadmap",
  customer_id="acme-corp",
  roadmap_id="acme-corp-roadmap-v1",
  highlight_first_value_date="Week 4"
)}}
```

### What Good Looks Like

**A strong roadmap exhibits these qualities:**

- Phase 1 delivers something the client can see and use within 4 weeks
- Every milestone is an outcome ("X works at Y quality") not an activity ("complete X")
- Dependencies are explicit -- no phase starts before its inputs are ready
- Sprint goals are achievable within the sprint (if a goal takes more than 2 weeks, break it down)
- Client responsibilities are listed alongside your deliverables (they know what they need to provide and when)
- Each phase has a clear "done" definition that both sides agreed to in the proposal
- Buffer time is built in (add 20% to estimates -- if you think it takes 4 weeks, plan for 5)

**Common mistakes to avoid:**

| Mistake | Consequence | Fix |
|---|---|---|
| Phase 1 is "setup and configuration" | Client sees no value for a month | Put at least one user-facing feature in Phase 1 |
| No buffer between phases | Phase 1 delays cascade into Phase 2 | Build 1-week buffer between phases |
| Milestones that only you can evaluate | Client cannot tell if you are on track | Milestones must be observable by the client |
| Ignoring client dependencies | You wait 3 weeks for API credentials | List client tasks with deadlines in the roadmap |
| Over-detailing Phase 3 at proposal time | Plans change once real data exists | Phase 1: detailed sprints. Phase 2: high-level sprints. Phase 3: goals only. |

### Practice Exercise

Build a complete roadmap for a test customer:

1. Select a customer with a completed solution design
2. List all tasks and map their dependencies using `{{roadmap_planner(action="map_dependencies", ...)}}`
3. Assign tasks to three phases following the Quick Wins / Core / Optimization pattern
4. Define outcome-based milestones for each phase
5. Create sprint-level detail for Phase 1 only
6. Review: Does Phase 1 deliver something the client can see and touch within 4 weeks?

**Validation questions for your roadmap:**

- Can you explain to the client what they will see working at the end of each phase?
- Is every milestone measurable without your involvement (the client can verify it themselves)?
- Are all client dependencies listed with deadlines?
- Does the critical path have at least 20% buffer?
- If Phase 3 was cancelled, would Phases 1 and 2 still deliver standalone value?
