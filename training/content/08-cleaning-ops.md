# Module 8: Cleaning & Operations

> **Learning Path:** Hospitality Operations Manager
> **Audience:** Property managers and vacation rental operators
> **Prerequisites:** Module 7 (Guest Communication Mastery), PMS integration active

---

## Lesson: PMS Data Interpretation

### Why This Matters

Your Property Management System (PMS) is the single source of truth for your entire operation. Every decision you make -- which properties need cleaning, which guests need messages, what your revenue looks like -- starts with PMS data. If you cannot read and interpret that data correctly, you are operating blind.

The most common mistakes in vacation rental management are not operational failures. They are data interpretation failures:

- Counting owner-blocked dates as vacant nights and panicking about low occupancy
- Missing a same-day turnover because you read the checkout date wrong
- Quoting revenue numbers that include cancelled bookings
- Not realizing a guest extended their stay because the PMS updated silently

**What bad data interpretation costs:**

| Interpretation Error | Operational Impact | Financial Impact |
|---|---|---|
| Confusing "blocked" with "vacant" | Inaccurate occupancy, wrong pricing decisions | Under-pricing or over-pricing by 10-20% |
| Missing a reservation status change | Guest arrives to unprepared property | Emergency cleaning cost + potential refund |
| Ignoring channel source in revenue calc | Inflated revenue projections | Budget shortfall when commissions are deducted |
| Not tracking cancellation patterns | No early warning system | Lost revenue from preventable cancellations |
| Counting pending bookings as confirmed | Over-committing resources | Wasted cleaning dispatch, lost opportunity cost |

Your PMS holds the answers. You just need to know how to ask the right questions.

**Why this lesson comes before cleaning and daily ops:**

You cannot dispatch cleaning correctly if you misread the PMS. You cannot build a morning briefing that reflects reality if your data interpretation is wrong. Every system downstream depends on accurate PMS reading. This is the foundation.

### How to Think About It

**Reservation Status Lifecycle**

Every booking moves through a status sequence. Know where each booking is at all times.

```text
Inquiry --> Pending --> Confirmed --> Checked-In --> Checked-Out --> Cancelled
                                                                    (can happen
                                                                     at any stage)
```

**Status definitions and what they mean operationally:**

| Status | What It Means | Operational Implication | Count in Occupancy? |
|---|---|---|---|
| Inquiry | Guest asked about availability, no commitment | Do not schedule cleaning or prep | No |
| Pending | Booking requested, awaiting payment/confirmation | Tentatively hold the date, do not over-commit | No |
| Confirmed | Payment received, booking is locked | Schedule cleaning, prepare welcome materials | Yes |
| Checked-In | Guest is currently at the property | Mid-stay messaging window, monitor for issues | Yes |
| Checked-Out | Guest has departed | Cleaning dispatch triggered, review solicitation queued | No (past) |
| Cancelled | Booking was cancelled at any stage | Release the dates, analyze cancellation reason | No |

**Blocked dates are NOT bookings:**

This is the single most important data interpretation rule. When an owner blocks dates for personal use or maintenance, those dates show as unavailable in the PMS. They must be excluded from:

- Occupancy rate calculations
- Revenue projections
- ADR (Average Daily Rate) calculations
- RevPAN calculations

They should be included in:

- Scheduling (the property is still occupied and may need prep)
- Calendar views (to avoid double-use conflicts)
- Cleaning dispatch (owner stays may need cleaning after)

**A concrete example of why this matters:**

Property has 30 days in a month. Owner blocks 10 days for personal use. 15 days are booked by guests.

- WRONG occupancy: 15 / 30 = 50% (panic mode, cut rates)
- RIGHT occupancy: 15 / 20 (available nights) = 75% (healthy, hold rates)

That error in interpretation could lead you to slash rates unnecessarily, costing hundreds or thousands of dollars.

**Key metrics and how to calculate them:**

```text
ADR (Average Daily Rate) = Total Revenue / Occupied Nights
    Exclude blocked dates from denominator
    Exclude cancelled bookings from numerator

RevPAN (Revenue Per Available Night) = Total Revenue / Available Nights
    Available = total nights - blocked nights

Occupancy Rate = Occupied Nights / Available Nights x 100
    Available = total nights - blocked nights

Channel Mix = Bookings by Source / Total Bookings x 100
    (direct, Airbnb, VRBO, Booking.com, etc.)

Net Revenue = Gross Revenue - Channel Commissions
    Each channel has different commission rates
```

**Why channel source matters:**

| Channel | Typical Commission | Net Revenue on $200/night | Effective Rate |
|---|---|---|---|
| Direct booking | 0% | $200.00 | $200.00 |
| Airbnb | 3% (host-only) | $194.00 | $194.00 |
| VRBO | 5% | $190.00 | $190.00 |
| Booking.com | 15% | $170.00 | $170.00 |

A property with 80% occupancy at $200/night through Booking.com generates less net revenue than one with 70% occupancy at $200/night through direct bookings. Channel mix is as important as rate.

**Reading guest profiles for operational context:**

PMS guest profiles contain data that directly affects operations:

| Data Point | Operational Use |
|---|---|
| Past stays | Returning guest? Adjust messaging tone |
| Booking channel | Which review link to use, commission impact |
| Party size | Cleaning scope, supply stocking |
| Special requests | Pet, accessibility needs, early check-in |
| Communication preferences | Email vs. text vs. app messaging |

### Step-by-Step Approach

**Step 1: Pull a daily booking snapshot**

```text
{{pms_data(action="get_bookings", date_range="today", data={"properties": "all", "include": ["status", "guest_name", "check_in", "check_out", "channel", "rate", "notes"]})}}
```

**Step 2: Identify today's operational events**

```text
{{pms_data(action="get_daily_events", date="2026-03-20", data={"event_types": ["check_in", "check_out", "turnover", "cancellation", "modification"], "properties": "all"})}}
```

**Step 3: Calculate current occupancy (correctly)**

```text
{{pms_data(action="calculate_metrics", date_range="2026-03-01:2026-03-31", data={"metrics": ["occupancy_rate", "adr", "revpan", "channel_mix"], "properties": "all", "exclude_blocked": true})}}
```

Note the `exclude_blocked: true` parameter. This is critical. Without it, your occupancy numbers are wrong.

**Step 4: Analyze guest profiles for personalization**

```text
{{pms_data(action="get_guest_profile", guest="Sarah Mitchell", data={"include": ["past_stays", "preferences", "notes", "channel", "total_revenue"]})}}
```

A returning guest who has stayed three times and always books direct is a high-value relationship. Treat them differently than a first-time OTA booking.

**Step 5: Check for data anomalies**

```text
{{pms_data(action="audit_data", date_range="today:+7days", data={"checks": ["overlapping_bookings", "missing_rates", "stale_status", "blocked_vs_vacant", "pending_over_48h"], "properties": "all"})}}
```

Run this audit daily. It catches problems before they become guest-facing incidents:

- **Overlapping bookings**: Two confirmed reservations for the same dates at the same property. This is an emergency.
- **Missing rates**: A confirmed booking with no rate attached. Revenue tracking is broken.
- **Stale status**: A booking that should be "checked-in" but is still "confirmed" 24 hours after check-in time.
- **Pending over 48h**: A pending booking that has not been confirmed or cancelled in 2 days. Follow up or release.

### Practice Exercise

**Scenario:** You pull the following data for March:

| Property | Total Nights | Nights Blocked | Nights Occupied | Revenue | Primary Channel |
|---|---|---|---|---|---|
| Lakeside Cottage | 31 | 5 | 20 | $4,000 | Airbnb (3%) |
| Mountain A-Frame | 31 | 0 | 15 | $3,750 | Direct (0%) |
| Downtown Loft | 31 | 10 | 18 | $2,700 | Booking.com (15%) |

**Task:** Calculate the following for each property:

1. Available nights (total - blocked)
2. Occupancy rate (occupied / available)
3. ADR (revenue / occupied nights)
4. RevPAN (revenue / available nights)
5. Net revenue after commission

**Expected calculations for Lakeside Cottage:**

- Available nights: 31 - 5 = 26
- Occupancy rate: 20 / 26 = 76.9%
- ADR: $4,000 / 20 = $200.00
- RevPAN: $4,000 / 26 = $153.85
- Net revenue: $4,000 - ($4,000 x 0.03) = $3,880.00

**Expected calculations for Mountain A-Frame:**

- Available nights: 31 - 0 = 31
- Occupancy rate: 15 / 31 = 48.4%
- ADR: $3,750 / 15 = $250.00
- RevPAN: $3,750 / 31 = $120.97
- Net revenue: $3,750 - ($3,750 x 0.00) = $3,750.00

**Expected calculations for Downtown Loft:**

- Available nights: 31 - 10 = 21
- Occupancy rate: 18 / 21 = 85.7%
- ADR: $2,700 / 18 = $150.00
- RevPAN: $2,700 / 21 = $128.57
- Net revenue: $2,700 - ($2,700 x 0.15) = $2,295.00

```text
{{pms_data(action="calculate_metrics", date_range="2026-03-01:2026-03-31", data={"metrics": ["occupancy_rate", "adr", "revpan", "net_revenue"], "properties": ["Lakeside Cottage", "Mountain View A-Frame", "Downtown Loft"], "exclude_blocked": true})}}
```

**Self-check questions:**

1. Which property has the highest gross revenue? (Lakeside Cottage: $4,000)
2. Which has the highest net revenue? (Lakeside Cottage: $3,880 -- but notice Mountain A-Frame is close at $3,750 with zero commission)
3. Which has the highest RevPAN? (Lakeside Cottage: $153.85)
4. Which property's occupancy looks deceptively bad without the blocked-date correction? (Downtown Loft: 58% raw vs 85.7% corrected)
5. Which property is losing the most to commissions? (Downtown Loft: $405 in commission on $2,700)

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Including blocked dates in occupancy rate | PMS shows them as "unavailable," same visual as booked | Always filter out blocked dates explicitly before calculating |
| Ignoring commission in revenue calculations | Commission is deducted later, not visible in PMS | Calculate net revenue by channel for accurate projections |
| Treating "pending" bookings as confirmed | Wanting to show higher occupancy | Only count confirmed and checked-in for operational planning |
| Not auditing PMS data weekly | Trusting the system blindly | Run a weekly data audit for overlaps, stale statuses, missing rates |
| Comparing properties without normalizing for blocked dates | Using raw numbers | Always use available nights as the denominator |
| Forgetting that rate changes mid-booking | Assuming one rate per stay | Check the nightly rate breakdown for long stays with rate adjustments |
| Not tracking cancellation reasons | Only counting cancellations, not understanding them | Log the reason for every cancellation to spot patterns |
| Using occupancy as the primary metric | It is the most visible number | Use RevPAN instead — it combines occupancy and rate into one actionable number |

---

## Lesson: Cleaning Dispatch Automation

### Why This Matters

Cleaning is the operational backbone of vacation rentals. A missed turnover means a guest arrives to a dirty property. That is not a recoverable situation. No message, no discount, no apology fully undoes the impression of walking into someone else's mess.

Manual cleaning coordination fails at scale because:

- You forget a same-day turnover when you are juggling five properties
- You text the wrong cleaner or give the wrong address
- You do not communicate the urgency -- the cleaner treats a same-day turnover like a routine clean
- You have no visibility into whether the clean was completed until the guest complains
- You cannot track performance across cleaners over time

Automated dispatch solves these problems by applying consistent priority logic, sending structured messages with all necessary details, and tracking completion.

**The priority tiers:**

| Priority | Condition | Action | Window |
|---|---|---|---|
| URGENT | Same-day turnover (checkout + checkin same day) | Clean first, alert operator | 3-5 hours |
| HIGH | Checkout today, checkin tomorrow | Clean by end of day | 8-12 hours |
| NORMAL | Checkout today, no checkin within 48h | Clean at convenience | 24-48 hours |
| LOW | Periodic deep clean, no guest turnover | Schedule for slow period | Flexible |

These tiers are non-negotiable. Every cleaning task gets classified before dispatch. The priority determines everything: which cleaner gets assigned, what time they arrive, whether the operator gets an alert, and how aggressively completion is tracked.

**Why cleaning dispatch does NOT require approval:**

Unlike guest messages, cleaning dispatches are internal and time-sensitive. Waiting for operator approval on a same-day turnover could mean the cleaner starts 2 hours late. The cleaning dispatch goes directly to the cleaning team.

However, the operator always receives a summary digest so they have visibility without bottlenecking the process.

### How to Think About It

**The Cleaning Dispatch Pipeline**

```text
PMS Scan (6:00 AM)
     |
     v
Identify Checkouts --> Cross-Reference Check-Ins
     |                          |
     v                          v
Assign Priority Tier      Calculate Cleaning Window
     |                          |
     v                          v
Generate Dispatch Messages (include all details)
     |
     v
Send to Cleaning Team (no approval needed)
     |
     v
Send Operator Digest (summary for awareness)
     |
     v
Track Completion --> Alert if Incomplete 2h Before Check-In
```

**Dispatch message content:**

Every cleaning dispatch message must include these fields. Missing any one of them creates confusion or delays:

| Field | Why | Example |
|---|---|---|
| Property name and address | Cleaner may cover multiple properties | "Lakeside Cottage, 142 Lakeview Drive" |
| Priority tier | Sets urgency expectations | "URGENT — same-day turnover" |
| Guest checkout time | Cleaner knows when to arrive | "Guest checks out at 11:00 AM" |
| Next guest check-in time | Cleaner knows the deadline | "Next guest arrives at 3:00 PM" |
| Cleaning window | Explicit hours available | "4-hour window" |
| Special instructions | Property-specific or guest-specific needs | "Extra towels for party of 6, check hot tub chemistry" |
| Completion confirmation request | Track that cleaning was done | "Reply DONE when complete" |

**The operator summary digest:**

Sent after all dispatches go out, the operator sees a consolidated view:

```text
CLEANING DISPATCH — March 20

URGENT (same-day turnover):
- Lakeside Cottage: Checkout 11 AM, Check-in 3 PM, Cleaner: Maria
  Window: 4 hours. Special: guest had dog, extra vacuum

HIGH (next-day check-in):
- Mountain A-Frame: Checkout 11 AM, Check-in tomorrow 2 PM, Cleaner: Carlos
  Window: 27 hours. Special: restock firewood

NORMAL (no upcoming check-in):
- Downtown Loft: Checkout 10 AM, next guest Mar 24, Cleaner: Maria
  Window: 101 hours. Special: deep clean kitchen

3 dispatches sent. Reply if changes needed.
```

**Cleaner workload balancing:**

When multiple URGENT cleans happen on the same day, you cannot assign them all to one cleaner. Consider:

| Factor | Impact | Rule |
|---|---|---|
| Geography | Travel time between properties | Assign same-area properties to same cleaner |
| Property size | Large homes take 2-3 hours, studios take 1 hour | Do not stack two large URGENT cleans on one person |
| Special requirements | Deep cleans, pet cleans, hot tub maintenance | Allow extra time for special checklist items |
| Backup cleaners | Primary unavailable | Every property must have a backup cleaner assigned |

### Step-by-Step Approach

**Step 1: Run the morning PMS scan for turnovers**

```text
{{pms_data(action="get_bookings", date_range="today", data={"event_types": ["check_out"], "properties": "all", "include": ["guest_name", "checkout_time", "next_booking", "special_notes"]})}}
```

**Step 2: Cross-reference with upcoming check-ins to assign priority**

```text
{{cleaning_dispatch(action="calculate_priorities", date="2026-03-20", data={"turnovers": [{"property": "Lakeside Cottage", "checkout_time": "11:00 AM", "next_checkin": "2026-03-20T15:00:00", "next_guest": "James Cooper"}, {"property": "Mountain View A-Frame", "checkout_time": "11:00 AM", "next_checkin": "2026-03-21T14:00:00", "next_guest": "Elena Vasquez"}, {"property": "Downtown Loft", "checkout_time": "10:00 AM", "next_checkin": "2026-03-24T15:00:00", "next_guest": "Tom Bradley"}]})}}
```

Returns:

- Lakeside Cottage: **URGENT** (same-day turnover, 4-hour window)
- Mountain View A-Frame: **HIGH** (next-day check-in, 27-hour window)
- Downtown Loft: **NORMAL** (4 days until next guest, 101-hour window)

**Step 3: Dispatch cleaning assignments (URGENT first)**

```text
{{cleaning_dispatch(action="dispatch", property="Lakeside Cottage", priority="URGENT", data={"cleaner": "Maria Santos", "checkout_time": "11:00 AM", "checkin_time": "3:00 PM", "window_hours": 4, "special_instructions": "Extra towels for party of 6. Check hot tub chemistry. Guest had a dog — extra vacuum needed.", "address": "142 Lakeview Drive"})}}
```

```text
{{cleaning_dispatch(action="dispatch", property="Mountain View A-Frame", priority="HIGH", data={"cleaner": "Carlos Rivera", "checkout_time": "11:00 AM", "checkin_time": "2:00 PM tomorrow", "window_hours": 27, "special_instructions": "Standard turnover. Restock firewood by back door. Check fireplace damper.", "address": "88 Summit Trail"})}}
```

```text
{{cleaning_dispatch(action="dispatch", property="Downtown Loft", priority="NORMAL", data={"cleaner": "Maria Santos", "checkout_time": "10:00 AM", "checkin_time": "3:00 PM Mar 24", "window_hours": 101, "special_instructions": "Deep clean kitchen — last guest reported stove needed attention. Clean balcony furniture.", "address": "200 Main St, Unit 4B"})}}
```

**Step 4: Send the operator summary digest**

```text
{{telegram_notify(action="send_digest", category="property_ops", message="CLEANING DISPATCH — March 20\n\nURGENT (same-day):\n- Lakeside Cottage: Out 11 AM, In 3 PM, Maria Santos (4h window)\n\nHIGH (next-day):\n- Mountain A-Frame: Out 11 AM, In tomorrow 2 PM, Carlos Rivera\n\nNORMAL:\n- Downtown Loft: Out 10 AM, next guest Mar 24, Maria Santos\n\n3 dispatches sent. Reply if changes needed.")}}
```

**Step 5: Monitor completion with escalation alerts**

```text
{{cleaning_dispatch(action="check_completion", date="2026-03-20", data={"properties": ["Lakeside Cottage", "Mountain View A-Frame", "Downtown Loft"], "alert_if_incomplete_before": {"Lakeside Cottage": "2026-03-20T13:00:00", "Mountain View A-Frame": "2026-03-20T18:00:00"}})}}
```

If Lakeside Cottage cleaning is not confirmed complete by 1:00 PM (2 hours before check-in), fire an escalation:

```text
{{telegram_notify(action="send_alert", priority="P0", category="alert", message="WARNING: Lakeside Cottage cleaning not confirmed complete. Guest checks in at 3:00 PM. Contact Maria Santos immediately at 555-0311.")}}
```

### Practice Exercise

**Scenario:** It is Saturday morning (your busiest turnover day). Here are today's events:

| Property | Checkout | Next Check-In | Guest Notes |
|---|---|---|---|
| Lakeside Cottage | 11:00 AM today | 4:00 PM today | Party of 8, had a dog |
| Mountain A-Frame | 11:00 AM today | 2:00 PM tomorrow | Guest had pets |
| Riverside Bungalow | 10:00 AM today | 10:00 AM today | Early checkout, early check-in |
| Downtown Loft | No checkout | Currently occupied | Mid-stay, no cleaning needed |
| Garden Suite | 11:00 AM today | No upcoming booking | Last booking for 2 weeks |

**Task:**

1. Assign priority tiers to each property needing cleaning
2. Dispatch in priority order (most urgent first)
3. Identify the most critical risk (Riverside Bungalow has a 0-hour window)
4. Create a contingency plan for Riverside

**Expected priority assignment:**

- Riverside Bungalow: **URGENT** (0-hour window -- this is a crisis)
- Lakeside Cottage: **URGENT** (5-hour window -- tight but manageable)
- Mountain A-Frame: **HIGH** (27-hour window)
- Garden Suite: **LOW** (no upcoming booking, schedule for slow period)
- Downtown Loft: No cleaning needed

```text
{{cleaning_dispatch(action="calculate_priorities", date="2026-03-20", data={"turnovers": [{"property": "Lakeside Cottage", "checkout_time": "11:00 AM", "next_checkin": "2026-03-20T16:00:00"}, {"property": "Mountain View A-Frame", "checkout_time": "11:00 AM", "next_checkin": "2026-03-21T14:00:00"}, {"property": "Riverside Bungalow", "checkout_time": "10:00 AM", "next_checkin": "2026-03-20T10:00:00"}, {"property": "Garden Suite", "checkout_time": "11:00 AM", "next_checkin": null}]})}}
```

**Riverside Bungalow contingency plan:**

The check-in and checkout overlap. This needs immediate action:

1. Contact incoming guest NOW to delay check-in by 2-3 hours
2. Assign the fastest cleaner to be on-site at 10:00 AM (the moment outgoing guest leaves)
3. Alert the operator that this is a time-critical situation
4. Have backup cleaner on standby in case primary is delayed

```text
{{guest_messaging(action="draft_message", type="checkin_delay", guest="incoming_guest", property="Riverside Bungalow", data={"original_checkin": "10:00 AM", "new_checkin": "1:00 PM", "reason": "We want to make sure everything is perfect for your arrival", "compensation": "We'll have a welcome treat waiting for you"})}}
```

**Self-check:** Did you flag Riverside Bungalow as the most critical issue, above even Lakeside Cottage? Did you create a proactive communication plan for the incoming guest rather than hoping for the best? Did you assign Garden Suite as LOW priority since there is no upcoming booking?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Treating all cleans as equal priority | No priority tier system | Classify every clean by the URGENT/HIGH/NORMAL/LOW framework |
| Not including next check-in time in dispatch | Thinking cleaners only need checkout info | Always include both checkout and check-in times |
| Dispatching without special instructions | Rushing through the morning batch | Pull PMS notes for each property; mention pets, party size, known issues |
| Not tracking cleaning completion | Assuming the cleaner will just do it | Require a completion confirmation reply ("DONE") |
| Failing to escalate incomplete cleans before check-in | No monitoring after dispatch | Set alerts for 2 hours before check-in if clean is unconfirmed |
| Assigning too many URGENT cleans to one cleaner | Not balancing workload | Spread same-day turnovers across cleaners by geography and capacity |
| Not having backup cleaners assigned | Assuming primary is always available | Every property must have primary and backup cleaner in the config |
| Ignoring overlapping checkout/checkin times | Not cross-referencing bookings | Always calculate the cleaning window; flag zero-gap turnovers immediately |

---

## Lesson: Daily Operations Rhythm

### Why This Matters

A daily rhythm turns chaos into routine. Without a structured cadence, you start every day reactive -- responding to whatever pings your phone first, putting out fires instead of preventing them, and ending the day unsure if you missed something.

The daily operations rhythm is the heartbeat of your property management. It ensures:

- Every property is accounted for every morning
- Guest messages go out at the right times
- Cleaning is dispatched before the operator finishes their coffee
- Issues surface early when they are still fixable
- The day ends with a clear status, not lingering anxiety

**The cost of no rhythm:**

| Without Rhythm | With Rhythm |
|---|---|
| Check Telegram 47 times for scattered notifications | 3 focused check-ins: morning, midday, evening |
| Miss a same-day turnover until guest calls | Same-day turnovers flagged at 7 AM |
| Discover a guest issue at checkout | Guest issues caught mid-stay |
| End the day wondering what you forgot | EOD status confirms everything handled |
| Weekend mornings start with dread | Weekend rhythm runs on autopilot |
| Every day feels different and unpredictable | Every day has the same structure, different content |

**The psychology of operational rhythm:**

Rhythm reduces cognitive load. When you know the morning briefing arrives at 7 AM, you do not need to remember to check the PMS, review the calendar, or scan for turnovers. The system does that and presents it in one place. Your brain is freed from tracking details and can focus on decisions.

This is why the morning briefing and EOD status always send, even on quiet days. They are rhythm anchors. A quiet morning briefing ("No check-ins, no check-outs, all properties stable") is still valuable because it gives you permission to relax and focus on other things.

### How to Think About It

**The Daily Schedule**

The schedule is built around the operator's natural day, not the system's convenience.

```text
6:00 AM   System checks, PMS scan (before operator is active)
7:00 AM   Morning briefing delivered to Telegram
7:30 AM   Guest message drafts ready for approval
8:00 AM   Cleaning dispatch sent to cleaners
9:00 AM   Deadlines and follow-ups surfaced
12:00 PM  Midday triage (only if urgent — skip-silently otherwise)
2:00 PM   Mid-stay check-in messages sent
5:00 PM   EOD status delivered
9:00 PM   Review solicitations sent, tomorrow prep
```

**The Morning Briefing**

The morning briefing is the most important message of the day. It is the operator's dashboard, delivered to their phone before they even open their laptop.

Format (following the standard digest pattern):

```text
MORNING BRIEFING — March 20

TODAY'S ACTIVITY:
- 2 check-ins, 1 check-out, 1 same-day turnover
- 3 guest messages pending approval

URGENT:
- Lakeside Cottage: Same-day turnover, cleaning dispatched to Maria

PROPERTIES:
- Lakeside Cottage: Check-out 11 AM (Mitchell), Check-in 3 PM (Cooper)
- Mountain A-Frame: Occupied (Vasquez, day 3 of 5)
- Riverside Bungalow: Occupied (Park, day 2 of 4)
- Downtown Loft: Check-out 10 AM (Chen), vacant until Mar 24
- Garden Suite: Vacant

PENDING APPROVALS:
- Pre-arrival: James Cooper (Mountain A-Frame) — reply send/skip/edit
- Mid-stay: David Park (Riverside Bungalow) — reply send/skip/edit
- Review: Mark Chen (Downtown Loft) — reply send/skip/edit

REVENUE THIS WEEK: $3,240 (vs $2,890 same week last year, +12.1%)
```

**Morning briefing rules:**

- Lead with the most actionable item (URGENT section first)
- Use bullet points, never paragraphs
- Include counts: "3 check-ins, 2 check-outs" not "several check-ins"
- Timestamps in 12h format with timezone: "2:30 PM ET"
- Currency always with dollar sign and two decimals: "$1,234.56"
- Keep total message under 30 lines -- operator scans on mobile
- Morning briefing ALWAYS sends (never skip-silently) -- it is the daily rhythm anchor
- Include pending approvals so operator can handle them right away

**The EOD Status**

The end-of-day status covers only what changed since the morning briefing. It does not repeat morning items. This prevents information fatigue and makes the EOD scannable.

```text
EOD STATUS — March 20

COMPLETED:
- Lakeside Cottage: Turnover complete (Maria, confirmed 1:45 PM)
- Cooper checked in at 3:15 PM, no issues
- Chen checked out, review request queued for 9 PM

ISSUES:
- Park (Riverside Bungalow) reported slow Wi-Fi — reset router remotely, monitoring

TOMORROW:
- 1 check-out (Vasquez, Mountain A-Frame)
- 0 check-ins
- Cleaning: Mountain A-Frame, NORMAL priority

METRICS:
- Messages sent today: 4 (2 approved, 1 auto-sent checkout, 1 review queued)
- Cleaning dispatches: 3 (all confirmed complete)
- Escalations: 1 (Wi-Fi, resolved)
```

**Skip-silently pattern:**

Most scheduled tasks should NOT send a message when there is nothing to report. This prevents notification fatigue.

| Task | Skip Silently? | Reason |
|---|---|---|
| Morning briefing | Never skip | Daily rhythm anchor |
| Guest message drafts | Skip if no messages to approve | Nothing actionable |
| Cleaning dispatch | Skip if no checkouts today | Nothing to dispatch |
| Midday triage | Skip if no urgent items | Avoid unnecessary interruptions |
| Mid-stay messages | Skip if no guests in window | Nothing to send |
| EOD status | Never skip | Closure signal |
| Review solicitations | Skip if no eligible guests | Nothing to send |
| Error/health check failures | Never skip | Always critical |

**Priority ranking for briefing items:**

| Urgency | Impact | Priority | Action |
|---|---|---|---|
| Today | Revenue or Operations | P0 | Always include, list first |
| Today | Informational | P1 | Include in digest |
| This week | Revenue or Operations | P1 | Include in digest |
| This week | Informational | P2 | Include only if anomaly |
| Future | Informational | P2 | Weekly rollup only |

### Step-by-Step Approach

**Step 1: Configure the daily rhythm schedule**

```text
{{daily_ops(action="configure_schedule", data={"timezone": "America/New_York", "schedule": [{"time": "06:00", "task": "pms_scan", "skip_silently": false}, {"time": "07:00", "task": "morning_briefing", "skip_silently": false}, {"time": "07:30", "task": "guest_message_drafts", "skip_silently": true}, {"time": "08:00", "task": "cleaning_dispatch", "skip_silently": true}, {"time": "09:00", "task": "deadlines_followups", "skip_silently": true}, {"time": "12:00", "task": "midday_triage", "skip_silently": true}, {"time": "14:00", "task": "midstay_messages", "skip_silently": true}, {"time": "17:00", "task": "eod_status", "skip_silently": false}, {"time": "21:00", "task": "review_solicitations", "skip_silently": true}], "weekend_mode": "reduced"})}}
```

**Step 2: Generate the morning briefing**

```text
{{daily_ops(action="generate_briefing", date="2026-03-20", data={"properties": "all", "include": ["checkins", "checkouts", "turnovers", "midstays", "vacant", "revenue_week", "pending_approvals", "open_issues"]})}}
```

**Step 3: Apply priority ranking to briefing items**

```text
{{daily_ops(action="rank_items", data={"items": [{"description": "Same-day turnover at Lakeside Cottage", "urgency": "today", "impact": "operations", "priority": "P0"}, {"description": "Cooper check-in at 3 PM", "urgency": "today", "impact": "operations", "priority": "P0"}, {"description": "Park Wi-Fi issue from yesterday", "urgency": "today", "impact": "informational", "priority": "P1"}, {"description": "Garden Suite vacant until next week", "urgency": "this_week", "impact": "informational", "priority": "P2"}]})}}
```

**Step 4: Generate EOD status (changes since morning only)**

```text
{{daily_ops(action="generate_eod", date="2026-03-20", data={"since": "morning_briefing", "include": ["completed_tasks", "new_issues", "resolved_issues", "tomorrow_preview", "daily_metrics"], "properties": "all"})}}
```

**Step 5: Configure weekend mode**

```text
{{daily_ops(action="configure_weekend", data={"changes": [{"task": "morning_briefing", "time": "08:00", "note": "Later start on weekends"}, {"task": "midday_triage", "enabled": false, "note": "Skip unless P0"}, {"task": "deadlines_followups", "enabled": false, "note": "No client work on weekends"}], "property_ops_continue": true, "note": "Guest messages, cleaning dispatch, and EOD run as normal on weekends"})}}
```

**Step 6: Set up digest deduplication rules**

```text
{{daily_ops(action="configure_deduplication", data={"rules": [{"rule": "Morning briefing owns the overview — task-specific messages add detail, not repeat summary"}, {"rule": "EOD status covers only changes since morning briefing"}, {"rule": "Weekly reports supersede daily reports for same data"}, {"rule": "If a check-in was in the briefing, pre-arrival task should reference 'as noted in briefing'"}]})}}
```

### Practice Exercise

**Scenario:** Set up the daily operations rhythm for a new week. You manage 5 properties with the following Monday landscape:

| Property | Status Monday | Key Event |
|---|---|---|
| Lakeside Cottage | Occupied (day 4) | Mid-stay check-in window already passed (day 2) |
| Mountain A-Frame | Check-in at 2 PM | New guest arriving, pre-arrival message needed |
| Riverside Bungalow | Vacant | No bookings until Wednesday |
| Downtown Loft | Checkout at 10 AM | Turnover, next guest Thursday (NORMAL priority) |
| Garden Suite | Occupied (day 1) | Checked in yesterday, mid-stay fires tomorrow |

**Task:**

1. Generate Monday's morning briefing
2. Determine which scheduled tasks will fire and which will skip silently
3. Create the cleaning dispatch for Downtown Loft
4. Draft the EOD status assuming everything went smoothly

**Expected skip-silently analysis:**

| Task | Fires? | Reason |
|---|---|---|
| PMS scan (6:00 AM) | Yes | Always runs |
| Morning briefing (7:00 AM) | Yes | Never skips |
| Guest message drafts (7:30 AM) | Yes | Mountain A-Frame pre-arrival needs approval |
| Cleaning dispatch (8:00 AM) | Yes | Downtown Loft checkout |
| Deadlines/follow-ups (9:00 AM) | Skip | No pending deadlines |
| Midday triage (12:00 PM) | Skip | No urgent items |
| Mid-stay messages (2:00 PM) | Skip | Lakeside window passed, Garden Suite is day 1 |
| EOD status (5:00 PM) | Yes | Never skips |
| Review solicitations (9:00 PM) | Maybe | Downtown Loft guest eligible if 2+ night stay |

```text
{{daily_ops(action="generate_briefing", date="2026-03-23", data={"properties": "all", "highlight": "Monday start of week"})}}
```

**Self-check:** Does your morning briefing lead with the most actionable item (Mountain A-Frame check-in prep and Downtown Loft cleaning dispatch)? Is it under 30 lines? Did you correctly determine that midday triage skips silently? Did you catch that Garden Suite's mid-stay check-in should fire tomorrow (day 2), not today (day 1)?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Sending notifications when nothing has changed | No skip-silently logic implemented | Configure skip-silently for all non-anchor tasks |
| Repeating morning briefing items in EOD status | Copy-paste mentality or no deduplication rules | EOD covers only changes since morning |
| Running the same schedule on weekends | Set-and-forget configuration | Configure weekend mode with later starts and reduced non-property tasks |
| Making the morning briefing too long | Including every detail | Cap at 30 lines; link to details instead of inlining them |
| Not anchoring the day with a morning briefing | Thinking "no news is good news" | Morning briefing always sends, even on quiet days — it is the anchor |
| Ignoring priority ranking and listing items chronologically | Defaulting to time-based ordering | Always rank by urgency x impact (P0 first, P2 last) |
| Not configuring deduplication | Each task reports independently | Set explicit rules so tasks reference the briefing rather than repeating it |
| Checking notifications constantly throughout the day | Not trusting the rhythm | Trust the schedule — check at briefing, midday (if it fires), and EOD |
