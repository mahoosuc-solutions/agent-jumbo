# Module 1: Discovery Fundamentals

> **Learning Path:** AI Solution Architect
> **Audience:** Non-technical business operators learning AI solution architecture
> **Prerequisites:** Basic familiarity with Agent Mahoo interface

---

## Lesson: Introduction to AI Solutioning

### Why This Matters

Every AI project that fails in production failed first in solutioning. The graveyard of AI initiatives is full of projects that:

- **Over-promised capabilities** — sold "magic AI" without scoping what the technology can actually do
- **Skipped discovery** — jumped straight to building without understanding the business problem
- **Had no success criteria** — launched without knowing what "working" looks like
- **Ignored the human side** — built a perfect system nobody wanted to use

The cost of these failures is not just money. It is credibility. A failed AI project poisons the well for every future initiative. Your client loses trust in AI, and you lose the client.

**What is at stake:**

| Failure Mode | Business Impact | Relationship Impact |
|---|---|---|
| Over-promising | Client expects magic, gets software | Trust destroyed, no repeat business |
| Skipping discovery | Solution solves wrong problem | Months wasted, scope creep, budget overrun |
| No success criteria | Nobody agrees if it "worked" | Endless revisions, unpaid invoices |
| No change management | Staff reject the tool | Low adoption, system shelved in 6 months |

AI solutioning is the discipline of turning a vague business need ("we want to use AI") into a concrete, buildable, measurable system that delivers value.

### How to Think About It

**The 6-Phase Model**

Every AI engagement follows this lifecycle. Skip a phase and you pay for it later.

```text
Discover --> Design --> Sell --> Build --> Deploy --> Optimize
   |           |         |        |         |          |
   |           |         |        |         |          |
 Learn the   Define    Price    Make     Put it     Make it
 business    the fix   the fix   it      in their   better
                                         hands
```

**Phase breakdown:**

1. **Discover** — Understand the business, its processes, its pain, and its readiness for AI. This is where 80% of project success is determined.
2. **Design** — Classify tasks, design workflows, choose architecture, write prompts. Turn understanding into a blueprint.
3. **Sell** — Package the solution with clear scope, pricing, timeline, and success criteria. Get commitment.
4. **Build** — Implement the solution using Agent Mahoo tools. Configure workflows, integrations, prompts.
5. **Deploy** — Roll out to users. Train staff. Monitor early usage. Handle the inevitable surprises.
6. **Optimize** — Measure against success criteria. Tune prompts. Expand scope. Build the case for next engagement.

**Where value actually comes from:**

AI solutions create value in exactly three ways. Every feature you build should map to one of these:

1. **Time savings** — Tasks that took 2 hours now take 5 minutes. Measure in hours saved per week.
2. **Error reduction** — Tasks that had a 15% error rate now have 2%. Measure in errors prevented.
3. **Scale** — Tasks that could only handle 50 per day can now handle 500. Measure in throughput increase.

If a proposed feature does not clearly deliver one of these three, question whether it belongs in the solution.

**The Discovery-to-Value Pipeline:**

```text
Business Pain --> Process Map --> AI Opportunity --> Solution Scope --> Value Estimate
     |                |                |                  |                  |
  "We're slow"    "Here's where"   "AI can help       "Here's what      "You'll save
                   the time goes"   with these 3"      we'll build"     $X/month"
```

### Step-by-Step Approach

When starting any new AI engagement, follow this sequence using Agent Mahoo tools:

**Step 1: Create the customer record**

```text
{{customer_lifecycle(action="add_customer", name="Acme Corp", data={"industry": "logistics", "size": "50-200 employees", "source": "referral", "stage": "discovery"})}}
```

**Step 2: Document initial pain points**

After your first conversation with the prospect, log what you heard:

```text
{{customer_lifecycle(action="update_customer", name="Acme Corp", data={"pain_points": ["manual invoice processing taking 20hrs/week", "data entry errors causing billing disputes", "cannot scale order processing beyond current volume"], "initial_contact_date": "2026-03-20"})}}
```

**Step 3: Run a preliminary business X-ray**

```text
{{business_xray_tool(action="quick_scan", company="Acme Corp", industry="logistics", known_pain_points=["invoice processing", "data entry", "order scaling"])}}
```

**Step 4: Assess which phase you are in**

Ask yourself these gating questions before moving to the next phase:

- Discovery: Do I understand their business well enough to explain it back to them? If no, stay here.
- Design: Can I describe the solution in specific enough terms to build it? If no, stay here.
- Sell: Has the client explicitly agreed to scope, timeline, and budget? If no, stay here.

### What Good Looks Like

**Signs you are doing discovery well:**

- You can explain the client's business to a stranger in 2 minutes
- You have identified at least 3 specific processes where AI could help
- You have quantified the current cost of those processes (time, errors, or scale limits)
- The client has said "yes, that's exactly right" when you played back their situation
- You have documented everything in the customer lifecycle tool

**Signs you are doing discovery poorly:**

- You are already talking about technical architecture in the first meeting
- You cannot name the client's top 3 pain points without checking your notes
- You have not asked about budget, timeline, or decision-making process
- You are assuming what the client needs based on their industry
- Your notes say things like "they want AI" without specifics

**Common mistakes to avoid:**

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Solutioning in the first call | Eagerness to impress | Listen for 80% of the call, talk for 20% |
| Accepting vague requirements | Fear of seeming difficult | Ask "what would that look like specifically?" |
| Ignoring non-technical stakeholders | Talking to IT only | Ask "who else would be affected by this?" |
| Skipping the value estimate | Assuming value is obvious | Always calculate hours saved or errors prevented |

### Practice Exercise

**Scenario:** You receive a lead from a small accounting firm (15 people). The owner says: "We spend too much time on data entry. We heard AI can help."

**Task:** Using Agent Mahoo tools, complete the following:

1. Create a customer record for "Summit Accounting" with appropriate initial data
2. List 5 questions you would ask in the discovery call
3. Log hypothetical answers to those questions in the customer record
4. Identify which phase of the 6-phase model you are in and what you need before moving forward

**Expected tool calls:**

```text
{{customer_lifecycle(action="add_customer", name="Summit Accounting", data={"industry": "accounting", "size": "15 employees", "source": "inbound_lead", "stage": "discovery", "initial_pain": "excessive data entry time"})}}
```

After your discovery call:

```text
{{customer_lifecycle(action="update_customer", name="Summit Accounting", data={"pain_points": ["manual entry of client tax documents - 30hrs/week across team", "copy-paste between client portals and accounting software", "year-end crunch requires overtime and temps"], "budget_signal": "willing to invest if ROI is clear within 3 months", "decision_maker": "owner - Sarah Chen", "timeline": "want something before next tax season"})}}
```

**Self-check:** Can you calculate a rough value estimate? If the team spends 30 hours/week on data entry at an average cost of $35/hour, that is $1,050/week or $54,600/year. If AI reduces that by 60%, the value is $32,760/year. That number frames your entire engagement.

---

## Lesson: Using Customer Lifecycle Tool

### Why This Matters

Your customer data is the foundation of every decision you make. Without structured customer tracking:

- You forget what was discussed in the last call and ask the same questions twice
- You lose track of where each prospect is in the pipeline and deals go cold
- You cannot spot patterns across clients that would improve your solutioning
- Handoffs between team members lose critical context
- You have no data to improve your own sales and delivery process

The customer lifecycle tool is not a CRM. It is your operational memory. Every interaction, every insight, every decision gets logged here. Six months from now, when the client asks "why did we decide to do it this way?", your answer is in this tool.

**The real cost of bad customer data:**

- Average deal that goes cold due to lost follow-up: $15,000-$50,000 in revenue
- Time spent reconstructing context for a client you haven't talked to in 3 weeks: 45 minutes per call
- Deals lost because you forgot a key stakeholder's concern: immeasurable

### How to Think About It

**Customer Lifecycle Stages**

Every customer moves through a predictable sequence. Your job is to know exactly where each customer is and what moves them forward.

```text
Lead --> Qualified --> Discovery --> Proposal --> Negotiation --> Won/Lost --> Active --> Renewal
```

**Stage definitions and exit criteria:**

| Stage | What You Know | Exit Criteria |
|---|---|---|
| Lead | Name, industry, initial interest | Confirmed they have budget and authority |
| Qualified | Budget range, decision maker, timeline | Scheduled discovery session |
| Discovery | Pain points, processes, readiness | Completed business X-ray |
| Proposal | Solution design, pricing, timeline | Proposal delivered and reviewed |
| Negotiation | Objections, competing options | Signed agreement |
| Won/Lost | Outcome and reasons | Project kickoff scheduled (or loss documented) |
| Active | Project status, milestones | Project delivered and accepted |
| Renewal | Usage data, satisfaction, expansion opportunities | Renewal decision made |

**Qualification Frameworks (Simplified)**

Use BANT as your baseline qualification checklist:

- **B**udget — Do they have money allocated? ("What have you budgeted for this initiative?")
- **A**uthority — Are you talking to the decision maker? ("Who else needs to approve this?")
- **N**eed — Is the pain real and urgent? ("What happens if you do nothing for 6 months?")
- **T**imeline — Is there a deadline driving action? ("When do you need this working by?")

**Green flags** (move forward with confidence):

- They have tried to solve this before and failed (proves the pain is real)
- They can name a specific dollar amount they are losing
- The decision maker is on the call
- They have a deadline driven by an external event (tax season, contract renewal, new regulation)

**Red flags** (slow down and investigate):

- "We're just exploring" with no timeline
- Cannot articulate what success looks like
- The person you are talking to needs to "check with their boss"
- They want a proposal before answering qualification questions
- Their budget expectation is 10x below what the solution would cost

### Step-by-Step Approach

**Adding a new customer:**

```text
{{customer_lifecycle(action="add_customer", name="Riverside Medical Group", data={"industry": "healthcare", "size": "35 employees", "source": "website_inquiry", "stage": "lead", "initial_contact": "2026-03-20", "initial_pain": "patient intake forms are manual and error-prone", "contact_name": "Dr. James Rivera", "contact_email": "jrivera@riversidemedical.example.com", "contact_role": "Practice Manager"})}}
```

**Updating after qualification call:**

```text
{{customer_lifecycle(action="update_customer", name="Riverside Medical Group", data={"stage": "qualified", "qualification": {"budget": "10000-25000 annual", "authority": "Dr. Rivera is decision maker, needs board approval over 20k", "need": "high - 3 staff spend 50% of time on intake paperwork", "timeline": "want pilot running by June 2026"}, "next_action": "schedule discovery session", "next_action_date": "2026-03-25"})}}
```

**Logging a meeting note:**

```text
{{customer_lifecycle(action="add_note", name="Riverside Medical Group", data={"date": "2026-03-22", "type": "discovery_call", "attendees": ["Dr. Rivera", "Office Manager Kim Park"], "summary": "Walked through intake process end-to-end. 4 forms per patient, 40 patients/day. Key pain: insurance verification is manual lookup taking 8 min per patient. Kim mentioned they tried a different software last year but staff found it too complex.", "action_items": ["run business x-ray on intake process", "research insurance verification API options", "prepare readiness assessment"]})}}
```

**Viewing customer status:**

```text
{{customer_lifecycle(action="get_customer", name="Riverside Medical Group")}}
```

**Listing all customers at a stage:**

```text
{{customer_lifecycle(action="list_customers", data={"filter_stage": "discovery"})}}
```

**Moving a customer to a new stage:**

```text
{{customer_lifecycle(action="update_customer", name="Riverside Medical Group", data={"stage": "proposal", "proposal_sent_date": "2026-04-01", "proposal_value": 18000, "proposal_summary": "AI-powered patient intake system with insurance verification"})}}
```

### What Good Looks Like

**A well-maintained customer record has:**

- Complete contact information for all stakeholders (not just your main contact)
- Dated notes from every interaction (calls, emails, meetings)
- Clear qualification data (BANT filled in, not guessed)
- Specific, quantified pain points ("30 hours/week on data entry" not "lots of manual work")
- Documented next actions with dates
- Stage transitions logged with reasons

**A poorly maintained customer record has:**

- Only a name and email
- Notes that say "good call, they're interested"
- No budget information after 3 meetings
- No record of who else is involved in the decision
- Last update was 3 weeks ago with no next action

**Quality check questions to ask yourself weekly:**

1. Can I tell the current status of every customer without opening their record? If not, your stages are not accurate.
2. Does every customer have a next action with a date? If not, deals are going cold.
3. Are my pain points specific and quantified? If not, my proposals will be vague.
4. Have I updated records within 24 hours of every interaction? If not, I am losing details.

### Practice Exercise

**Task:** Set up a complete customer pipeline with 3 fictional clients at different stages.

**Client 1 — New Lead:**

```text
{{customer_lifecycle(action="add_customer", name="Brightpath Tutoring", data={"industry": "education", "size": "8 employees", "source": "linkedin", "stage": "lead", "initial_pain": "scheduling tutors is a nightmare", "contact_name": "Maria Gonzalez", "contact_role": "Founder"})}}
```

**Client 2 — In Discovery:**

```text
{{customer_lifecycle(action="add_customer", name="Harbor Freight Logistics", data={"industry": "logistics", "size": "120 employees", "source": "referral", "stage": "discovery", "qualification": {"budget": "50000-100000", "authority": "COO approves, CTO influences", "need": "critical - losing contracts due to slow quoting", "timeline": "Q3 2026"}, "pain_points": ["manual freight quoting takes 45 min per quote, do 30/day", "error rate on quotes is 12%, causing margin loss", "cannot scale quoting team fast enough for growth"]})}}
```

**Client 3 — Proposal Stage:**

```text
{{customer_lifecycle(action="add_customer", name="Clearview Property Management", data={"industry": "real_estate", "size": "25 employees", "source": "conference", "stage": "proposal", "qualification": {"budget": "20000-35000", "authority": "CEO decides solo", "need": "moderate - want to reduce tenant response time", "timeline": "flexible, within 6 months"}, "proposal_value": 28000, "proposal_summary": "AI tenant communication system with maintenance triage"})}}
```

**Self-check:** Review your three records. For each one, answer:

1. What is the next action you would take?
2. What information is missing that you need?
3. What is the single biggest risk to this deal?

If you cannot answer these questions from the record alone, the record is incomplete.

---

## Lesson: Business X-Ray Analysis

### Why This Matters

A business X-ray is your systematic method for understanding how a company actually works, not how they say they work or how they wish they worked, but what really happens day to day.

Without a proper business X-ray:

- You design solutions for imaginary problems
- You miss the highest-value opportunities because they are buried in "that's just how we do it" processes
- You underestimate implementation complexity because you did not see the workarounds and exceptions
- Your proposals feel generic because they are not grounded in specific operational reality

**The insight gap:**

What the client tells you in the first meeting is almost never where the real value is. They say "we need AI for customer service." The X-ray reveals that their real bottleneck is a 3-person team manually copying data between two systems that do not integrate, costing 60 hours/week and causing the customer service delays they are complaining about.

The X-ray finds the real problem. The real problem is where the real value is.

### How to Think About It

**Process Mapping: Breaking a Business into Processes**

Every business is a collection of processes. Your job is to decompose the business into its component processes and evaluate each one.

```text
Business
  |
  +-- Core Processes (directly serve customers/generate revenue)
  |     +-- Sales & Marketing
  |     +-- Service Delivery
  |     +-- Customer Support
  |
  +-- Support Processes (keep the business running)
  |     +-- Finance & Accounting
  |     +-- HR & Hiring
  |     +-- IT & Infrastructure
  |
  +-- Management Processes (steer the business)
        +-- Planning & Strategy
        +-- Reporting & Analytics
        +-- Compliance & Risk
```

For each process, capture:

- **Who** does it (role, not person name)
- **What** they do (specific actions, not job descriptions)
- **How often** (daily, weekly, monthly, per-event)
- **How long** it takes (per instance and total per week)
- **What tools** they use (software, spreadsheets, paper, phone)
- **What goes wrong** (errors, delays, bottlenecks, workarounds)

**Pain Point Scoring: Frequency x Impact x Fixability**

Not all pain points are equal. Score each one on three dimensions:

| Dimension | Score 1 | Score 3 | Score 5 |
|---|---|---|---|
| **Frequency** | Happens monthly or less | Happens weekly | Happens daily or multiple times daily |
| **Impact** | Minor inconvenience | Moderate time/cost waste | Major cost, errors, or customer impact |
| **Fixability** | Hard to fix with AI (needs physical change, regulation, etc.) | Partially addressable with AI | Highly suitable for AI automation |

**Total score = Frequency x Impact x Fixability** (range: 1-125)

Scoring guide:

- **75-125:** High priority. This is your headline use case. Lead with this in your proposal.
- **30-74:** Medium priority. Good for Phase 2 or as supporting features.
- **1-29:** Low priority. Note it but do not build for it first.

**AI Opportunity Identification: Which Processes Are AI-Suitable?**

Use this decision tree for each process:

```text
Is the process primarily information-based (text, data, documents)?
  |
  YES --> Does it follow repeatable patterns?
  |         |
  |         YES --> Is the output predictable/structured?
  |         |         |
  |         |         YES --> STRONG AI CANDIDATE (automation)
  |         |         NO  --> MODERATE AI CANDIDATE (AI-assisted with human review)
  |         |
  |         NO  --> Does it require deep domain expertise?
  |                   |
  |                   YES --> MODERATE AI CANDIDATE (knowledge augmentation)
  |                   NO  --> WEAK AI CANDIDATE (may not be worth automating)
  |
  NO --> Does it involve physical actions?
          |
          YES --> NOT AN AI CANDIDATE (needs robotics/IoT, out of scope)
          NO  --> RE-EVALUATE (may have information components you missed)
```

### Step-by-Step Approach

**Step 1: Run the initial X-ray scan**

```text
{{business_xray_tool(action="quick_scan", company="Harbor Freight Logistics", industry="logistics", known_pain_points=["freight quoting speed", "quote accuracy", "scaling quoting team"])}}
```

**Step 2: Map specific processes**

For each process the quick scan surfaces, get detailed:

```text
{{business_xray_tool(action="map_process", company="Harbor Freight Logistics", process="freight_quoting", data={"steps": [{"step": 1, "action": "Receive quote request via email", "who": "Sales Rep", "time_minutes": 2, "tool": "Outlook"}, {"step": 2, "action": "Look up carrier rates in 3 different portals", "who": "Sales Rep", "time_minutes": 15, "tool": "carrier websites"}, {"step": 3, "action": "Calculate fuel surcharges and accessorials", "who": "Sales Rep", "time_minutes": 10, "tool": "Excel spreadsheet"}, {"step": 4, "action": "Build quote document", "who": "Sales Rep", "time_minutes": 8, "tool": "Word template"}, {"step": 5, "action": "Get manager approval for quotes over $5000", "who": "Sales Manager", "time_minutes": 10, "tool": "email"}, {"step": 6, "action": "Send quote to customer", "who": "Sales Rep", "time_minutes": 5, "tool": "Outlook"}], "total_time_minutes": 50, "frequency": "30 per day", "error_rate": "12%", "bottleneck": "carrier rate lookup across multiple portals"})}}
```

**Step 3: Score the pain points**

```text
{{business_xray_tool(action="score_pain_points", company="Harbor Freight Logistics", pain_points=[{"name": "Slow freight quoting", "frequency": 5, "impact": 5, "fixability": 5, "notes": "30 quotes/day at 50 min each = 25 hrs/day across team"}, {"name": "Quote accuracy errors", "frequency": 5, "impact": 4, "fixability": 4, "notes": "12% error rate causing margin loss and customer disputes"}, {"name": "Cannot scale quoting team", "frequency": 3, "impact": 5, "fixability": 4, "notes": "Hiring and training takes 3 months, losing contracts now"}])}}
```

**Step 4: Identify AI opportunities**

```text
{{business_xray_tool(action="identify_opportunities", company="Harbor Freight Logistics", data={"processes_analyzed": ["freight_quoting", "carrier_rate_lookup", "quote_document_generation"], "opportunities": [{"process": "carrier_rate_lookup", "ai_type": "automation", "description": "API integration with carrier rate systems, AI to select optimal carrier", "estimated_time_savings": "15 min per quote", "confidence": "high"}, {"process": "quote_document_generation", "ai_type": "automation", "description": "Auto-generate quote documents from structured data", "estimated_time_savings": "8 min per quote", "confidence": "high"}, {"process": "quote_approval", "ai_type": "hybrid", "description": "AI pre-approval for standard quotes, human review for exceptions", "estimated_time_savings": "8 min per flagged quote", "confidence": "medium"}]})}}
```

### What Good Looks Like

**A strong business X-ray delivers:**

- A complete process map with 5-15 key processes identified
- Time and frequency data for each process (not estimates, actual measurements)
- Pain point scores that clearly separate high-value from low-value opportunities
- At least 3 specific AI opportunities with estimated value
- A clear "start here" recommendation backed by the scoring

**A weak business X-ray looks like:**

- Vague process descriptions ("they do a lot of manual work")
- No quantified time or cost data
- Pain points listed without scoring or prioritization
- AI opportunities that sound impressive but have no supporting data
- Recommendations based on what is technically cool rather than what delivers value

**Red flags in your X-ray process:**

- You completed the X-ray without talking to the people who actually do the work (only management)
- Your process maps have fewer than 4 steps (you are not seeing the real complexity)
- Every process scored as "high priority" (you are not discriminating enough)
- You did not find any surprises (you are confirming assumptions, not discovering reality)

### Practice Exercise

**Scenario:** You are running a business X-ray for a 20-person marketing agency. From your discovery call, you know they struggle with:

- Creating client reports (takes 4 hours per client per month, 25 clients)
- Managing social media content calendars across clients
- Responding to client emails and Slack messages

**Task:**

1. Run a quick scan for the agency
2. Map the "client reporting" process in detail (invent realistic steps)
3. Score all three pain points
4. Identify which is the best AI opportunity and why

```text
{{business_xray_tool(action="quick_scan", company="Spark Marketing Agency", industry="marketing", known_pain_points=["client reporting", "content calendar management", "client communication management"])}}
```

**Self-check:** After scoring, your highest-priority item should be the one with the highest Frequency x Impact x Fixability score. Does your recommendation match that score? If you recommended something different, you need a strong reason why (for example, a lower-scoring item might be a better starting point because it builds trust for a larger engagement).

---

## Lesson: AI Readiness Assessment

### Why This Matters

Readiness assessment prevents the most expensive mistake in AI consulting: building a solution for a client who cannot use it.

You can design the perfect AI workflow, but if the client's data lives in handwritten notebooks, their team is terrified of technology, or their IT infrastructure is a single shared desktop computer, the project will fail. And it will be your fault, because you should have checked.

**What "not ready" actually looks like:**

- A dental practice that wants AI appointment scheduling but their schedule is a paper book
- A law firm that wants AI document review but their files are scanned images with no OCR
- A manufacturer that wants predictive maintenance but their machines have no sensors
- A real estate agency that wants AI lead scoring but their CRM has 200 contacts with no data fields filled in

These are not edge cases. These are the majority of small business AI prospects. Your readiness assessment separates the "ready now" from "ready after some prep work" from "not ready and here is what needs to change first."

### How to Think About It

**The 4 Dimensions of AI Readiness**

```text
                    DATA QUALITY
                         |
                    [1-2-3-4-5]
                         |
TEAM CAPABILITY ----[READINESS]---- INFRASTRUCTURE
    [1-2-3-4-5]          |          [1-2-3-4-5]
                         |
                  CHANGE MANAGEMENT
                    [1-2-3-4-5]
```

**Dimension 1: Data Quality (Score 1-5)**

| Score | Description | Example |
|---|---|---|
| 1 | No digital data exists | Paper records only, no databases |
| 2 | Data exists but is messy, inconsistent, siloed | Spreadsheets with different formats per person |
| 3 | Data is digital and mostly consistent but incomplete | CRM with 60% of fields filled, some duplicates |
| 4 | Data is clean, structured, and accessible | Well-maintained database with API access |
| 5 | Data is clean, labeled, versioned, and documented | Enterprise data warehouse with data dictionary |

**Dimension 2: Infrastructure (Score 1-5)**

| Score | Description | Example |
|---|---|---|
| 1 | No relevant infrastructure | Shared desktop, no cloud services |
| 2 | Basic infrastructure, no integration points | Email and basic office software only |
| 3 | Modern tools but not connected | Cloud CRM, email, accounting software, no integrations |
| 4 | Connected systems with some automation | CRM with email integration, some Zapier workflows |
| 5 | API-first architecture, automation-ready | Connected systems with documented APIs, webhook support |

**Dimension 3: Team Capability (Score 1-5)**

| Score | Description | Example |
|---|---|---|
| 1 | Team struggles with basic technology | Cannot navigate software without help |
| 2 | Team uses technology but resists change | Comfortable with current tools, nervous about new ones |
| 3 | Team is comfortable with technology | Uses multiple apps, can learn new tools with training |
| 4 | Team is tech-forward | Actively seeks better tools, some self-service automation |
| 5 | Team includes technical members | Has staff who can maintain integrations and troubleshoot |

**Dimension 4: Change Management Readiness (Score 1-5)**

| Score | Description | Example |
|---|---|---|
| 1 | Strong resistance to change, no leadership support | "We've always done it this way" culture |
| 2 | Leadership wants change but staff is resistant | Top-down push without buy-in |
| 3 | Mixed readiness, some champions | A few team members excited, others cautious |
| 4 | Organization is change-ready with a plan | Leadership committed, staff informed, timeline shared |
| 5 | Change-native organization | Regularly adopts new processes, has change management experience |

**Readiness Levels:**

Calculate the average score across all 4 dimensions:

- **Average 4.0-5.0: Ready** — Proceed with full solution design. This client can absorb AI today.
- **Average 2.5-3.9: Needs Work** — Proceed with a readiness plan. Identify specific gaps and include remediation in your proposal (data cleanup, tool migration, training). The project scope should include a "readiness sprint" before the AI build.
- **Average 1.0-2.4: Not Ready** — Do not propose an AI solution yet. Propose a readiness engagement instead: data digitization, infrastructure modernization, team training. The AI project becomes Phase 2.

**Common Gaps and How to Address Them:**

| Gap | Quick Fix (weeks) | Proper Fix (months) |
|---|---|---|
| Data is in spreadsheets | Import to a structured database | Implement proper data management |
| No API access to key systems | Use browser automation as bridge | Migrate to API-friendly tools |
| Team cannot use current tools well | Simplify AI interface to minimum clicks | Conduct training program |
| No executive sponsor | Find a champion, build quick win | Defer until leadership changes |
| Data has no labels or categories | Manual labeling sprint | Build labeling into daily workflow |

### Step-by-Step Approach

**Step 1: Gather readiness data during discovery**

Ask these specific questions during your discovery calls:

- Data: "Where does the data for this process live? Can you show me a sample?"
- Infrastructure: "What software do you use daily? Do any of them connect to each other?"
- Team: "How did the team react the last time you introduced a new tool?"
- Change: "Who will champion this project internally? What happens if they leave?"

**Step 2: Score each dimension**

```text
{{business_xray_tool(action="assess_readiness", company="Harbor Freight Logistics", data={"data_quality": {"score": 3, "notes": "Carrier rates are in structured databases but quote history is in spreadsheets with inconsistent formatting. Customer data is in CRM but incomplete.", "gaps": ["quote history needs cleanup and migration", "customer data fields 40% empty"]}, "infrastructure": {"score": 4, "notes": "Modern CRM, cloud email, carrier portals have APIs. No current integrations between systems.", "gaps": ["need to set up API connections to carrier portals"]}, "team_capability": {"score": 3, "notes": "Sales team is comfortable with CRM and email. Resistant to past tool changes. Office manager is tech-savvy and could be a champion.", "gaps": ["sales team will need hands-on training", "identify Kim Park as internal champion"]}, "change_management": {"score": 3, "notes": "COO is committed and vocal. Sales team is cautious but motivated by commission impact of faster quoting.", "gaps": ["need visible quick win in first 2 weeks", "sales team must see personal benefit"]}})}}
```

**Step 3: Calculate overall readiness and determine approach**

Average score: (3 + 4 + 3 + 3) / 4 = 3.25 — **Needs Work**

This means: proceed with project, but include a readiness sprint covering data cleanup and team training before the AI build begins.

**Step 4: Build the readiness plan into your proposal**

```text
{{customer_lifecycle(action="update_customer", name="Harbor Freight Logistics", data={"readiness_level": "needs_work", "readiness_score": 3.25, "readiness_plan": ["Week 1-2: Clean and migrate quote history data to structured format", "Week 1-2: Set up API connections to top 3 carrier portals", "Week 3: Train sales team on new quoting interface", "Week 3: Identify and empower Kim Park as internal champion", "Week 4+: Begin AI solution rollout"], "proposal_note": "Include 2-week readiness sprint before AI build"})}}
```

### What Good Looks Like

**A strong readiness assessment:**

- Has specific evidence for each score, not just a gut feeling
- Identifies concrete gaps with concrete remediation steps
- Adjusts the project plan based on readiness (does not ignore low scores)
- Includes the readiness work in the proposal timeline and budget
- Names a specific internal champion

**A weak readiness assessment:**

- Scores all dimensions the same (lazy scoring)
- Lists gaps but no remediation plan
- Ignores low scores and proposes a full AI build anyway
- Does not account for readiness work in the timeline
- Assumes the client will "figure it out"

**The most dangerous mistake:** Scoring a client as "Ready" because you want the deal. A client who is not ready will produce a failed project, a refund demand, and a bad reference. A client who is told "you need to do X first" respects your honesty, does the prep work, and becomes your best case study.

### Practice Exercise

**Scenario:** You are assessing readiness for a 30-person veterinary clinic chain (3 locations). They want AI to help with:

- Automated appointment reminders and rescheduling
- Post-visit follow-up communications
- Insurance claim pre-authorization

From your discovery, you learn:

- They use a cloud-based veterinary practice management system (has an API)
- Patient records are digital but notes are free-text (not structured)
- The front desk staff at one location is very tech-savvy; the other two locations prefer phone calls
- The practice owner is enthusiastic but the office managers are skeptical

**Task:**

1. Score each of the 4 readiness dimensions with supporting evidence
2. Calculate the overall readiness level
3. Write a readiness plan that addresses the gaps
4. Decide: Do you propose an AI project, a readiness engagement, or walk away?

```text
{{business_xray_tool(action="assess_readiness", company="Pawsitive Vet Care", data={"data_quality": {"score": 3, "notes": "Digital records exist in cloud PMS but clinical notes are unstructured free-text. Insurance data is structured. Appointment history is clean.", "gaps": ["clinical notes need NLP processing or structured templates", "may need to standardize note-taking across locations"]}, "infrastructure": {"score": 4, "notes": "Cloud PMS with API. Modern phone system. Email and SMS capabilities exist.", "gaps": ["need to verify PMS API covers appointment and communication endpoints"]}, "team_capability": {"score": 2, "notes": "Only 1 of 3 locations has tech-comfortable staff. Other locations prefer phone-based workflows. No one on staff has managed an automation before.", "gaps": ["2 locations need significant training", "need to start with the tech-savvy location as pilot"]}, "change_management": {"score": 2, "notes": "Owner is enthusiastic but office managers are skeptical. No change management plan exists. Previous software rollout at Location 2 went poorly.", "gaps": ["must get office manager buy-in before rollout", "need visible quick win at pilot location", "owner must actively sponsor, not just approve"]}})}}
```

**Self-check:** Average score is (3 + 4 + 2 + 2) / 4 = 2.75 — **Needs Work**, barely. The team and change management scores are the blockers. Your proposal should include a pilot at the tech-savvy location first, with office manager involvement in the design process, before rolling out to other locations. If you proposed a full 3-location rollout, you would be setting yourself up for failure at 2 of the 3 sites.
