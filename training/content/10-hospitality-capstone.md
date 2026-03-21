# Module 10: Hospitality Capstone

> **Learning Path:** Hospitality Operations Manager
> **Audience:** Property managers and vacation rental operators
> **Prerequisites:** Modules 7-9 (Guest Communication, Cleaning & Operations, Revenue & Reviews)

---

## Lesson: Multi-Property Setup Project

### Why This Matters

Everything you have learned in Modules 7 through 9 has been in isolation: a messaging lesson here, a cleaning dispatch there, a pricing strategy in the abstract. This capstone brings it all together into a single, end-to-end implementation.

Setting up a multi-property operation from scratch is the ultimate test of your skills. It requires you to:

- Configure each property with its messaging templates, cleaning protocols, and pricing strategy
- Wire up the automated guest lifecycle so no message is missed
- Establish the daily operations rhythm so your mornings start with clarity, not chaos
- Build the review solicitation pipeline so social proof compounds automatically
- Set up revenue monitoring so you catch problems before they become crises

If you can set up three properties from zero to fully operational in a single session, you can manage thirty.

**What "fully operational" means:**

| Component | Status: Not Ready | Status: Fully Operational |
|---|---|---|
| Guest messaging | No templates, manual copy-paste | Automated lifecycle with approval workflow |
| Cleaning dispatch | Text cleaners individually, miss turnovers | Priority-tiered dispatch with completion tracking |
| Reviews | Hope guests leave reviews | Systematic solicitation with eligibility filters |
| Revenue | Check PMS when you remember | Automated monitoring with threshold alerts |
| Daily rhythm | Reactive, checking phone constantly | Structured morning briefing and EOD status |
| Pricing | Same rate year-round | Seasonal tiers with event overrides and rate floors |

**Why setup order matters:**

The temptation is to set up whatever feels most exciting first. Resist that. Each system depends on the ones before it:

- Messaging depends on property configuration (access codes, addresses, group templates)
- Cleaning depends on PMS data interpretation (which checkouts trigger which priority)
- Reviews depend on messaging pipeline (the solicitation uses the same approval workflow)
- Revenue monitoring depends on PMS data flowing correctly (metrics built on booking data)
- Daily rhythm depends on all systems being active (it orchestrates everything)

### How to Think About It

**The Setup Sequence**

```text
1. Property Configuration
        |
        v
2. Template Groups & Messaging
        |
        v
3. Cleaning Protocols
        |
        v
4. Review Pipeline
        |
        v
5. Revenue & Pricing
        |
        v
6. Daily Rhythm
        |
        v
7. Test Run (Dry Run with simulated bookings)
```

**The three properties for this exercise:**

| Property | Type | Group | Max Guests | Special Features |
|---|---|---|---|---|
| Cedar Ridge Cabin | Mountain cabin | Mountain | 6 | Fireplace, hiking trails, pet-friendly |
| Harborfront Suite | Urban waterfront | Waterfront | 4 | Marina views, walking distance to downtown, balcony |
| Orchard Farmhouse | Rural farmhouse | Rural | 8 | Garden, fire pit, fresh eggs, 20 min from town |

Each property represents a different operational profile:

- **Cedar Ridge Cabin:** Mountain group templates, pet-friendly overrides, fireplace maintenance in cleaning checklist
- **Harborfront Suite:** Waterfront group templates, urban amenity tips, smart lock management
- **Orchard Farmhouse:** New "rural" group (requires creating a new template group), unique amenities (garden, chickens), distance-from-town communication

**Time budget for setup:**

| Step | Estimated Time | Notes |
|---|---|---|
| Property configuration | 10 minutes | Data entry, straightforward |
| Template groups & overrides | 15 minutes | Creative work, tone matters |
| Cleaning protocols | 10 minutes | Checklists and cleaner assignments |
| Review pipeline | 5 minutes | Configuration, mostly rule-based |
| Revenue & pricing | 10 minutes | Base rates, seasons, floors/ceilings |
| Daily rhythm | 5 minutes | Schedule configuration |
| Dry run | 10 minutes | Simulate a week, verify all systems |
| **Total** | **65 minutes** | Target: under 90 minutes for 3 properties |

### Step-by-Step Approach

**Step 1: Configure all three properties**

```text
{{guest_messaging(action="configure_portfolio", data={"properties": [{"name": "Cedar Ridge Cabin", "group": "mountain", "address": "450 Pine Ridge Road, Asheville, NC", "access_type": "lockbox", "lockbox_code": "8823", "lockbox_location": "Left side of front door, behind the planter", "max_guests": 6, "bedrooms": 3, "special_amenities": ["fireplace", "hiking_trails"], "pet_policy": "dogs_allowed", "checkout_time": "11:00 AM", "checkin_time": "3:00 PM"}, {"name": "Harborfront Suite", "group": "waterfront", "address": "22 Marina Boulevard, Unit 5A, Asheville, NC", "access_type": "smart_lock", "max_guests": 4, "bedrooms": 2, "special_amenities": ["marina_view", "balcony"], "pet_policy": "no_pets", "checkout_time": "10:00 AM", "checkin_time": "4:00 PM"}, {"name": "Orchard Farmhouse", "group": "rural", "address": "1200 Orchard Lane, Fairview, NC", "access_type": "keypad", "keypad_code": "5567", "max_guests": 8, "bedrooms": 4, "special_amenities": ["garden", "fire_pit", "farm_eggs", "outdoor_dining"], "pet_policy": "dogs_allowed", "checkout_time": "11:00 AM", "checkin_time": "2:00 PM"}]})}}
```

**Step 2: Create template groups (including the new "rural" group)**

```text
{{guest_messaging(action="create_template_group", group="mountain", data={"pre_arrival_extras": "The mountain air is crisp — bring layers even in summer. Firewood is stocked by the back door and the fireplace is ready to go.", "mid_stay_recommendation": "The trail behind the property leads to a gorgeous overlook — about a 25-minute hike each way.", "checkout_note": "Please close the fireplace damper and make sure all windows are latched."})}}
```

```text
{{guest_messaging(action="create_template_group", group="waterfront", data={"pre_arrival_extras": "The marina views from the balcony are stunning, especially at sunset. The waterfront walking path is right outside the building.", "mid_stay_recommendation": "The seafood market on Dock Street has the freshest catch in town — grab some and use the suite's kitchen!", "checkout_note": "Please lock the balcony door and leave the key fob on the kitchen counter."})}}
```

```text
{{guest_messaging(action="create_template_group", group="rural", data={"pre_arrival_extras": "Welcome to the countryside! The garden is yours to explore — feel free to pick any ripe herbs or vegetables. Fresh eggs from the chickens are in the fridge each morning.", "mid_stay_recommendation": "The fire pit is perfect tonight — firewood is in the shed, and the stars out here are incredible. You won't see skies like this in the city.", "checkout_note": "No need to tend the garden or the chickens. Just make sure the fire pit is fully extinguished and the front gate is closed."})}}
```

**Step 3: Add property-specific overrides**

```text
{{guest_messaging(action="create_property_override", property="Cedar Ridge Cabin", data={"pet_override": "Your pup is welcome! We've left a dog bed and water bowl by the fireplace. The trails are dog-friendly — just keep them leashed near the road.", "quirk_note": "Hot water takes 90 seconds to warm up — this is normal for the cabin and not a problem."})}}
```

```text
{{guest_messaging(action="create_property_override", property="Orchard Farmhouse", data={"distance_note": "The property is about 20 minutes from downtown Asheville — we recommend stocking up on groceries on your way in. The farm kitchen is fully equipped and the garden has fresh herbs year-round.", "special_note": "Rural location — always mention distance to town and suggest provisioning in pre-arrival message"})}}
```

**Step 4: Configure cleaning protocols for each property**

```text
{{cleaning_dispatch(action="configure_property", property="Cedar Ridge Cabin", data={"standard_clean_time_minutes": 120, "deep_clean_time_minutes": 180, "special_checklist": ["Check fireplace — remove ash if used, close damper", "Restock firewood (minimum 4 logs by back door)", "Vacuum all floors thoroughly (pet hair even if no pet reported)", "Check trail gate latch is secure", "Verify lockbox code is current and lockbox is accessible"], "cleaner_primary": "Maria Santos", "cleaner_backup": "Carlos Rivera"})}}
```

```text
{{cleaning_dispatch(action="configure_property", property="Harborfront Suite", data={"standard_clean_time_minutes": 90, "deep_clean_time_minutes": 150, "special_checklist": ["Clean balcony railing and furniture (salt spray accumulation)", "Check smart lock battery — replace if below 30%", "Wipe marina-side windows inside and out", "Restock coffee pods and tea selection", "Verify balcony door locks properly"], "cleaner_primary": "Carlos Rivera", "cleaner_backup": "Maria Santos"})}}
```

```text
{{cleaning_dispatch(action="configure_property", property="Orchard Farmhouse", data={"standard_clean_time_minutes": 150, "deep_clean_time_minutes": 240, "special_checklist": ["Check fire pit — remove ash completely, restock firewood in shed", "Collect eggs from coop and place in fridge with date label", "Check garden gate latch — must close securely (wildlife)", "Inspect exterior for wildlife entry points (rural property)", "Extra kitchen cleaning — guests cook more at this property", "Verify keypad battery and code are working", "Check outdoor dining area — clean table and chairs"], "cleaner_primary": "Maria Santos", "cleaner_backup": "Ana Garcia"})}}
```

**Step 5: Set up the review pipeline**

```text
{{review_manager(action="configure_pipeline", data={"properties": ["Cedar Ridge Cabin", "Harborfront Suite", "Orchard Farmhouse"], "rules": {"min_stay_nights": 2, "skip_if_open_issues": true, "skip_if_safety_issue_resolved": true, "send_time": "21:00", "max_requests_per_stay": 1, "follow_up": "never"}, "review_links": {"Cedar Ridge Cabin": {"airbnb": "https://airbnb.com/reviews/write/cabin123", "google": "https://g.page/r/cedar-ridge/review"}, "Harborfront Suite": {"airbnb": "https://airbnb.com/reviews/write/harbor456", "google": "https://g.page/r/harborfront/review"}, "Orchard Farmhouse": {"airbnb": "https://airbnb.com/reviews/write/orchard789", "google": "https://g.page/r/orchard-farm/review"}}})}}
```

**Step 6: Configure revenue monitoring and seasonal pricing**

```text
{{revenue_monitor(action="set_base_rates", data={"properties": [{"name": "Cedar Ridge Cabin", "base_rate": 225, "min_rate": 135, "max_rate": 400, "weekend_premium": 1.2}, {"name": "Harborfront Suite", "base_rate": 195, "min_rate": 120, "max_rate": 350, "weekend_premium": 1.15}, {"name": "Orchard Farmhouse", "base_rate": 250, "min_rate": 150, "max_rate": 450, "weekend_premium": 1.25}]})}}
```

```text
{{revenue_monitor(action="configure_alerts", data={"properties": ["Cedar Ridge Cabin", "Harborfront Suite", "Orchard Farmhouse"], "alerts": [{"name": "low_occupancy", "condition": "occupancy_next_14_days < 60%", "priority": "P1"}, {"name": "no_new_bookings", "condition": "new_bookings_14_days == 0", "priority": "P1"}, {"name": "cancellation_spike", "condition": "cancellations_7_days >= 2", "priority": "P0"}]})}}
```

**Step 7: Wire up the daily operations rhythm**

```text
{{daily_ops(action="configure_schedule", data={"timezone": "America/New_York", "properties": ["Cedar Ridge Cabin", "Harborfront Suite", "Orchard Farmhouse"], "schedule": [{"time": "06:00", "task": "pms_scan", "skip_silently": false}, {"time": "07:00", "task": "morning_briefing", "skip_silently": false}, {"time": "07:30", "task": "guest_message_drafts", "skip_silently": true}, {"time": "08:00", "task": "cleaning_dispatch", "skip_silently": true}, {"time": "14:00", "task": "midstay_messages", "skip_silently": true}, {"time": "17:00", "task": "eod_status", "skip_silently": false}, {"time": "21:00", "task": "review_solicitations", "skip_silently": true}]})}}
```

**Step 8: Dry run with simulated bookings**

```text
{{daily_ops(action="dry_run", date="2026-03-21", data={"properties": ["Cedar Ridge Cabin", "Harborfront Suite", "Orchard Farmhouse"], "simulate_bookings": [{"property": "Cedar Ridge Cabin", "guest": "Test Guest A", "check_in": "2026-03-21", "check_out": "2026-03-24", "channel": "airbnb", "party_size": 4, "has_pet": true}, {"property": "Harborfront Suite", "guest": "Test Guest B", "check_in": "2026-03-22", "check_out": "2026-03-23", "channel": "direct", "party_size": 2}, {"property": "Orchard Farmhouse", "guest": "Test Guest C", "check_in": "2026-03-21", "check_out": "2026-03-25", "channel": "vrbo", "party_size": 6}], "validate": ["morning_briefing_generates", "pre_arrival_drafts_fire", "cleaning_dispatch_assigns_priority", "review_eligibility_filters_apply", "eod_status_generates", "skip_silently_works_correctly"]})}}
```

### Practice Exercise

**Scenario:** Complete the full setup, then simulate one week of activity:

| Day | Event |
|---|---|
| Monday | Guest A checks in to Cedar Ridge Cabin (3-night stay, has dog) |
| Monday | Guest C checks in to Orchard Farmhouse (4-night stay, party of 6) |
| Tuesday | Guest B checks in to Harborfront Suite (1-night stay) |
| Tuesday | Mid-stay check-in fires for Guest A (day 2) and Guest C (day 2) |
| Wednesday | Guest B checks out of Harborfront Suite |
| Wednesday | No mid-stay for Guest C (already sent on day 2) |
| Thursday | Guest A checks out of Cedar Ridge Cabin |
| Friday | Guest C checks out of Orchard Farmhouse |

**Walk through each day and verify all systems:**

**Monday:**

- Morning briefing: 2 check-ins (Cedar Ridge, Orchard), 0 check-outs
- Guest messages: Pre-arrival for Guest A (include pet info) and Guest C (include distance/provisioning note)
- Cleaning: No dispatches (no checkouts)
- Reviews: None

**Tuesday:**

- Morning briefing: 1 check-in (Harborfront), 0 check-outs
- Guest messages: Pre-arrival for Guest B; mid-stay for Guest A and Guest C at 2 PM
- Cleaning: No dispatches
- Reviews: None

**Wednesday:**

- Morning briefing: 0 check-ins, 1 check-out (Harborfront)
- Guest messages: Checkout reminder for Guest B
- Cleaning: Harborfront Suite, NORMAL priority (no upcoming booking assumed)
- Reviews: Guest B ineligible (1-night stay, skip silently)
- Mid-stay for Guest C: Does NOT fire (already sent Tuesday)

**Thursday:**

- Morning briefing: 0 check-ins, 1 check-out (Cedar Ridge)
- Cleaning: Cedar Ridge Cabin, priority depends on next booking
- Reviews: Guest A eligible (3-night stay, no issues) -- queued for 9 PM

**Friday:**

- Morning briefing: 0 check-ins, 1 check-out (Orchard)
- Cleaning: Orchard Farmhouse, priority depends on next booking
- Reviews: Guest C eligible (4-night stay, no issues) -- queued for 9 PM

```text
{{daily_ops(action="simulate_week", date_range="2026-03-23:2026-03-27", data={"properties": ["Cedar Ridge Cabin", "Harborfront Suite", "Orchard Farmhouse"], "validate_all_systems": true})}}
```

**Self-check:** Guest B stays only 1 night. Does your system correctly skip the mid-stay check-in AND the review solicitation? Guest C's mid-stay should fire on Tuesday (day 2), not Monday (day 1) or Wednesday (day 3). Did Guest A's pre-arrival include the pet-friendly override? Did Guest C's pre-arrival mention the 20-minute distance to town?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Setting up messaging but not cleaning dispatch | Focusing on guest-facing systems only | Configure all systems before going live — cleaning is as critical as messaging |
| Skipping the dry run | Confidence that config is correct | Always dry run with simulated bookings; errors are invisible until a guest is affected |
| Not assigning backup cleaners | Assuming primary is always available | Every property needs primary and backup cleaner assigned |
| Configuring systems in isolation without connecting to daily rhythm | Building components, not a system | The daily rhythm orchestrates everything — wire all systems into it |
| Going live with all properties simultaneously | Impatience to get everything running | Start with one property for a week, verify, then add the next |
| Not setting rate floors and ceilings | Trusting automation without guard rails | Always set min/max rates to prevent extreme pricing |
| Forgetting to create template group for new property types | Only thinking about existing groups | If a property does not fit an existing group, create a new one (e.g., "rural") |
| Not testing pet-friendly and distance overrides | Assuming overrides work automatically | Verify in dry run that property-specific overrides appear in the correct messages |

---

## Lesson: Operations Playbook Creation

### Why This Matters

A playbook turns your operational knowledge from tribal memory into a durable, shareable system. Without a playbook:

- If you go on vacation, your properties go on autopilot with no human backup plan
- If you hire a co-host, they spend 3 months learning what you know by instinct
- If you sell the business, the buyer gets properties but not the operational intelligence that makes them profitable
- If you forget how you configured something 6 months ago, you reverse-engineer your own system
- If an emergency happens at 2 AM, you need to remember the plumber's number from memory

The playbook is not documentation for documentation's sake. It is an operational asset that makes your business transferable, scalable, and resilient.

**What a complete playbook contains:**

| Section | Purpose | When Used |
|---|---|---|
| SOPs (Standard Operating Procedures) | How to do each recurring task | Daily/weekly routine |
| Runbooks | Step-by-step for handling specific situations | When incidents occur |
| Escalation chains | Who to contact and when | During any escalation |
| Property guides | Per-property operational details and quirks | During setup, troubleshooting, onboarding |
| Vendor contacts | Service providers for each property | When repairs or services are needed |
| System configuration docs | How the automation is set up and why | During troubleshooting, quarterly review |

### How to Think About It

**The SOP Framework**

Every SOP follows the same structure. Consistency makes SOPs scannable under pressure.

```text
TITLE: What this SOP covers
TRIGGER: When to execute this SOP
OWNER: Who is responsible
FREQUENCY: How often this happens
STEPS: Numbered steps with specific tool calls
ESCALATION: What to do if something goes wrong
VERIFICATION: How to confirm it worked
ESTIMATED TIME: How long this should take
```

**Runbook vs. SOP:**

| Attribute | SOP | Runbook |
|---|---|---|
| When used | Recurring, routine tasks | Specific incidents or emergencies |
| Frequency | Daily, weekly, or per-event | As-needed, hopefully rarely |
| Structure | Linear steps | Decision tree (if X, then Y) |
| Example | "Morning briefing review" | "Guest locked out at midnight" |
| Tone | Procedural, calm | Diagnostic, action-oriented |
| Who writes it | Operations manager | Operations manager after experiencing the incident |

**The "write it after it happens" rule for runbooks:**

Every time you encounter a new incident type, write a runbook for it afterward. The first time is always improvised. The second time should be systematic. If you handle a guest lockout at midnight, write the runbook the next morning while it is fresh. Over 6-12 months, your runbook library covers every scenario you are likely to face.

**Escalation Chain Template:**

```text
Level 1: Automated System
  - Handles: Routine messages, standard dispatch, scheduled tasks
  - Failure mode: Skips silently, logs the miss, alerts Level 2

Level 2: On-Call Operator
  - Handles: Guest complaints, non-standard requests, cleaning issues
  - Contacted via: Telegram P0 alert
  - Response time: 30 min (business hours), 1 hour (after hours)
  - Failure mode: No response in 30 min, auto-escalate to Level 3

Level 3: Property Owner / Emergency Services
  - Handles: Safety issues, major damage, legal situations
  - Contacted via: Phone call (never text for emergencies)
  - Response time: Immediate
```

### Step-by-Step Approach

**Step 1: Document your core SOPs (start with the top 5)**

```text
{{playbook_manager(action="create_sop", name="Same-Day Turnover", data={"trigger": "PMS shows checkout and checkin on same day for same property", "owner": "Operations Manager", "frequency": "1-3 times per week during peak season", "estimated_time": "5 minutes (dispatch), 2-4 hours (cleaning)", "steps": [{"step": 1, "action": "Verify checkout time and checkin time from PMS", "tool": "{{pms_data(action='get_bookings', date_range='today')}}"}, {"step": 2, "action": "Calculate cleaning window (checkin time minus checkout time)", "decision": "If window < 3 hours, alert operator immediately as high-risk"}, {"step": 3, "action": "Dispatch cleaning with URGENT priority", "tool": "{{cleaning_dispatch(action='dispatch', priority='URGENT')}}"}, {"step": 4, "action": "Confirm cleaner acknowledged within 15 minutes", "escalation": "If no acknowledgment, call cleaner directly"}, {"step": 5, "action": "Monitor completion — alert if not confirmed 2 hours before checkin", "tool": "{{cleaning_dispatch(action='check_completion')}}"}], "escalation": "If cleaning cannot complete in time, contact incoming guest to delay check-in by 1-2 hours. Offer a warm apology and a small gesture (bottle of wine, late checkout).", "verification": "Cleaner sends DONE confirmation. Operator spot-checks if photo is available."})}}
```

```text
{{playbook_manager(action="create_sop", name="Morning Briefing Review", data={"trigger": "Daily at 7:00 AM when morning briefing arrives in Telegram", "owner": "Operations Manager", "frequency": "Daily, 7 days a week", "estimated_time": "10-15 minutes", "steps": [{"step": 1, "action": "Read morning briefing in Telegram", "time": "2 minutes"}, {"step": 2, "action": "Review URGENT items first — take immediate action on any P0 items", "time": "3-5 minutes"}, {"step": 3, "action": "Approve or edit pending guest message drafts", "tool": "Reply send/skip/edit to each draft in Telegram", "time": "3-5 minutes"}, {"step": 4, "action": "Verify cleaning dispatch assignments are correct", "time": "1 minute"}, {"step": 5, "action": "Note any items needing follow-up later in the day", "time": "1 minute"}], "verification": "All pending approvals responded to, no URGENT items left unaddressed, all dispatch assignments confirmed"})}}
```

**Step 2: Create runbooks for common incidents**

```text
{{playbook_manager(action="create_runbook", name="Guest Locked Out", data={"trigger": "Guest messages or calls reporting they cannot access the property", "severity": "Tier 1 (business hours) / Tier 2 (after 10 PM)", "diagnostic_tree": [{"check": "What type of lock does the property have?", "if_keypad": "Verify guest has correct code — codes may have rotated. Check current code in PMS notes.", "if_lockbox": "Guide guest to lockbox location. Provide combination. Common issue: guests look in the wrong spot.", "if_smart_lock": "Check smart lock app for battery status. Attempt remote unlock. If battery dead, guide to backup access."}, {"check": "Did the code change recently?", "if_yes": "Provide updated code immediately. Log that pre-arrival message had stale code.", "if_no": "Walk guest through entry process step by step. Common issue: keypad requires pressing # after code."}, {"check": "Is it after 10 PM?", "if_yes": "Escalate to Tier 2 — operator calls guest directly within 5 minutes. Do not leave guest waiting outside in the dark.", "if_no": "Resolve via messaging if possible, call if not resolved in 10 minutes."}], "resolution": "Guest gains access. Log incident for root cause analysis.", "prevention": "Include access instructions in pre-arrival message with clear, specific formatting. Add access type to morning briefing for check-in day guests."})}}
```

```text
{{playbook_manager(action="create_runbook", name="Double Booking Detected", data={"trigger": "PMS data audit shows overlapping confirmed reservations for same property and dates", "severity": "Tier 3 — immediate operator action required", "steps": [{"step": 1, "action": "Identify which booking was confirmed first — that booking has priority"}, {"step": 2, "action": "Check if the second booking can be moved to another property in your portfolio"}, {"step": 3, "action": "Contact the displaced guest immediately with a sincere apology"}, {"step": 4, "action": "If you have an alternative property, offer it at a discount or rate match"}, {"step": 5, "action": "If no alternative available, offer full refund plus help finding comparable accommodation"}, {"step": 6, "action": "Investigate root cause — channel sync failure? Manual error? PMS bug?"}, {"step": 7, "action": "Implement fix to prevent recurrence — verify calendar sync is real-time"}], "escalation": "If both guests have already arrived, operator handles personally by phone. Never delegate a double-booking resolution.", "prevention": "Run daily PMS audit for overlapping bookings. Ensure all channel calendars sync in real-time. Never manually block dates without updating all channels."})}}
```

**Step 3: Document escalation chains with real contacts**

```text
{{playbook_manager(action="create_escalation_chain", data={"levels": [{"level": 1, "name": "Automated System", "handles": ["Routine guest messages (via approval workflow)", "Standard cleaning dispatch", "Scheduled review solicitations", "Morning briefing and EOD status"], "response_time": "Immediate (automated)", "failure_mode": "Skips silently, logs miss, alerts Level 2"}, {"level": 2, "name": "Operations Manager", "handles": ["Guest complaints and escalations (Tier 1-2)", "Non-standard requests", "Cleaning no-shows and delays", "Revenue anomalies", "Approval queue items"], "contact_method": "Telegram P0 alert", "response_time": "30 min business hours, 1 hour after hours", "failure_mode": "No response in 30 min triggers phone call to backup operator"}, {"level": 3, "name": "Property Owner / Emergency Services", "handles": ["Safety issues (gas, fire, flood, intruder)", "Major property damage", "Legal situations (guest injury, property damage claim)", "Guest medical emergency"], "contact_method": "Phone call (never text for Level 3)", "response_time": "Immediate", "contacts": {"fire_police_ems": "911", "plumber": "John's Plumbing, 555-0142, available 7 AM - 9 PM", "electrician": "Spark Electric, 555-0198, available 8 AM - 6 PM", "locksmith": "QuickKey, 555-0234, 24/7 emergency", "hvac": "Mountain Air HVAC, 555-0267, available 8 AM - 5 PM", "pest_control": "Green Shield Pest, 555-0389, available 9 AM - 5 PM"}}]})}}
```

**Step 4: Create property guides**

```text
{{playbook_manager(action="create_property_guide", property="Cedar Ridge Cabin", data={"address": "450 Pine Ridge Road, Asheville, NC", "access": {"type": "lockbox", "location": "Left side of front door, behind the planter", "code": "8823", "backup": "Spare key under third stepping stone from porch"}, "known_quirks": ["Hot water takes 90 seconds to warm up — mention in pre-arrival to prevent false alarm complaints", "Fireplace damper sticks — pull hard then push up. Include in cleaning checklist to verify.", "Cell service is spotty — Wi-Fi is CedarRidge_Guest, password pinecone2026", "Driveway is steep — warn guests with low-clearance vehicles in pre-arrival"], "vendors": {"cleaner_primary": "Maria Santos, 555-0311", "cleaner_backup": "Carlos Rivera, 555-0322", "plumber": "John's Plumbing, 555-0142", "hvac": "Mountain Air HVAC, 555-0267", "pest_control": "Green Shield Pest, 555-0389"}, "seasonal_notes": {"winter": "Pipes can freeze if heat drops below 60F — NEVER let guests turn heat off completely. Set minimum to 62F.", "spring": "Pollen heavy in April — stock extra cleaning supplies, warn allergy-prone guests", "summer": "Trail behind property gets overgrown — arrange monthly trimming with landscaper", "fall": "Leaf cleanup required after every guest in Oct-Nov. Add 30 min to cleaning estimate."}})}}
```

### Practice Exercise

**Scenario:** Create a complete operations playbook covering:

1. Three SOPs: Same-day turnover, Morning briefing review, Guest checkout processing
2. Two runbooks: Guest reports pest/wildlife issue, Payment dispute received
3. Complete escalation chain with vendor contacts
4. Property guides for all three properties

**Task:** Draft the "Guest Reports Pest/Wildlife Issue" runbook. This is particularly important for Orchard Farmhouse (rural property where wildlife encounters are more common).

```text
{{playbook_manager(action="create_runbook", name="Guest Reports Pest or Wildlife Issue", data={"trigger": "Guest messages about insects, rodents, or wildlife in or near the property", "severity_assessment": "Tier 1 (minor: spider, ants, flies) to Tier 2 (major: rodent inside, snake, raccoon in trash)", "diagnostic_tree": [{"check": "What type of pest/wildlife and where?", "if_minor_inside": "Acknowledge immediately. Provide self-help tip (ant spray under kitchen sink, fly swatter in closet). Schedule pest control for next vacancy.", "if_major_inside": "Acknowledge immediately. Dispatch pest control same-day if available. If animal is trapped or dangerous, advise guest to avoid the area.", "if_outside_only": "Acknowledge. Set expectations — some wildlife is normal, especially at rural properties. Ensure trash bins are secured."}, {"check": "Is the property rural (Orchard Farmhouse)?", "if_yes": "Rural wildlife encounters are more frequent. Frame as part of the charm when possible (deer in garden = beautiful), address genuine threats (snake near entrance = immediate action). Never dismiss the guest's concern.", "if_no": "This is unexpected for urban/waterfront properties. Take it more seriously — investigate entry point, schedule immediate inspection."}, {"check": "Is the guest panicking or calm?", "if_panicking": "Call the guest directly. Voice reassurance is more powerful than text for pest/wildlife fears.", "if_calm": "Handle via messaging. Provide clear next steps and timeline."}], "resolution": "Issue addressed, guest reassured, pest control scheduled if warranted. Add to cleaning checklist: check for signs of pest activity.", "prevention": "Cleaning checklist includes: check for pest signs, ensure screens intact, seal visible gaps. Seasonal pest treatment schedule for all properties."})}}
```

**Self-check:** Could a co-host who has never visited your properties follow this runbook at 2 AM without calling you? If not, add more detail. Does the runbook account for the different expectations at rural vs urban properties? Did you include both self-help steps (for minor issues the guest can handle) and escalation steps (for issues requiring professional intervention)?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Writing SOPs that are too vague ("handle the situation") | Assuming the reader knows what you know | Include specific tool calls, exact steps, and decision criteria |
| Creating a playbook and never updating it | Treating it as a one-time project | Review quarterly; add new runbooks after every novel incident |
| Not including vendor contact information | Assuming you will always remember | Every property guide must have complete, current vendor contacts |
| Writing runbooks for only the common scenarios | Thinking rare events will not happen | Cover edge cases — they cause the most damage precisely because nobody planned for them |
| Not testing runbooks with another person | Assuming they are clear because you wrote them | Have someone unfamiliar with your properties walk through a runbook |
| Documenting the "how" but not the "why" | Focusing on steps, not reasoning | Include reasoning behind key decisions so future editors understand the intent |

---

## Lesson: Performance Review

### Why This Matters

You cannot improve what you do not measure. After setting up your properties and running your playbook for a period, you need to step back and evaluate: is it working? Where are the gaps? What should change?

Performance review is not a vanity exercise. It is the feedback loop that turns a good operation into a great one. The operators who review their performance monthly outperform those who do not, because they catch trends early, double down on what works, and fix what does not before it compounds.

**The KPIs that matter for hospitality operations:**

| KPI | What It Measures | Target | Why |
|---|---|---|---|
| Response time (guest messages) | Speed of first reply to guest inquiry | < 1 hour | Fast responses prevent escalations and improve reviews |
| Review solicitation rate | % of eligible guests who receive a request | > 95% | Measures system reliability — are you asking consistently? |
| Review conversion rate | % of solicited guests who leave a review | > 40% | Measures template and timing effectiveness |
| Cleaning on-time rate | % of cleans completed before check-in | > 99% | Core operational reliability — one miss is a crisis |
| Escalation resolution time | Average time from report to resolution | < 2h (Tier 1), < 4h (Tier 2) | Guest satisfaction and review impact |
| Occupancy rate | % of available nights booked | 70-85% (market-dependent) | Demand and pricing health |
| RevPAN | Revenue per available night | Property-dependent | Combined pricing and occupancy effectiveness |
| Guest satisfaction (avg rating) | Average review score across platforms | > 4.7/5.0 | Listing competitiveness and long-term viability |

**Leading vs. Lagging Indicators:**

| Leading (predict future) | Lagging (confirm past) |
|---|---|
| Booking pace for next 60 days | Monthly revenue |
| Response time trend | Average review score |
| Cleaning completion rate | Guest complaint count |
| Review solicitation rate | Occupancy rate |
| Approval queue response time | Cancellation rate |

Leading indicators give you time to act. Lagging indicators tell you if your actions worked. Track both, but prioritize acting on leading indicators.

### How to Think About It

**The Performance Review Cadence**

```text
WEEKLY (15 min)                 MONTHLY (1 hour)              QUARTERLY (half day)
- Scan KPI dashboard            - Deep dive on trends          - Strategic review
- Note anomalies                - Compare to targets           - Pricing strategy update
- Quick corrections             - Property-level analysis      - Template and tone refresh
                                - Identify top/bottom          - Playbook update
                                  performers                   - Goal setting for next quarter
                                - Create 2-3 action items      - Vendor relationship review
```

**The Performance Matrix**

Plot each property on two dimensions to understand your portfolio at a glance:

```text
                    HIGH SATISFACTION (> 4.7 rating)
                          |
              Stars        |        Champions
          (loved but       |      (loved AND
           unprofitable)   |       profitable)
                          |
    LOW REVENUE -----------+----------- HIGH REVENUE
    (below RevPAN target)  |            (above RevPAN target)
                          |
              Problems     |        Cash Cows
          (not loved,      |      (profitable but
           not profitable) |       satisfaction declining)
                          |
                    LOW SATISFACTION (< 4.7 rating)
```

**What to do with each quadrant:**

| Quadrant | Strategy | Action |
|---|---|---|
| Champions | Protect and replicate | Understand why it works; apply patterns to other properties |
| Stars | Optimize pricing | Raise rates or improve channel mix — the experience is great, capture more value |
| Cash Cows | Improve experience | Investigate complaints; invest in property improvements before reviews tank further |
| Problems | Investigate deeply | Root cause analysis; may need major renovation, repositioning, or exit |

**The monthly review process:**

1. Pull all KPI data for the period
2. Compare against targets and prior period
3. Plot properties on the performance matrix
4. Identify the top 3 findings (both positive and negative)
5. Create 2-3 specific action items with owners and deadlines
6. Document insights for the quarterly strategic review

### Step-by-Step Approach

**Step 1: Pull the KPI dashboard**

```text
{{revenue_monitor(action="generate_kpi_dashboard", date_range="2026-02-20:2026-03-20", data={"properties": ["Cedar Ridge Cabin", "Harborfront Suite", "Orchard Farmhouse"], "kpis": ["occupancy_rate", "adr", "revpan", "net_revenue", "channel_mix", "booking_lead_time", "cancellation_rate"]})}}
```

**Step 2: Pull guest communication metrics**

```text
{{guest_messaging(action="get_performance_metrics", date_range="2026-02-20:2026-03-20", data={"metrics": ["avg_response_time", "messages_sent", "approval_queue_time", "messages_skipped_timeout", "escalation_count", "escalation_resolution_time"], "properties": "all"})}}
```

**Step 3: Pull review performance**

```text
{{review_manager(action="get_performance", date_range="2026-02-20:2026-03-20", data={"metrics": ["solicitations_sent", "solicitations_eligible", "solicitation_rate", "reviews_received", "conversion_rate", "average_rating", "rating_by_property"], "properties": "all"})}}
```

**Step 4: Pull cleaning operations metrics**

```text
{{cleaning_dispatch(action="get_performance", date_range="2026-02-20:2026-03-20", data={"metrics": ["total_dispatches", "on_time_rate", "urgent_cleans", "completion_confirmation_rate", "avg_clean_time_by_property", "missed_cleans"], "properties": "all"})}}
```

**Step 5: Generate the monthly performance report**

```text
{{daily_ops(action="generate_monthly_report", month="2026-03", data={"include": ["revenue_summary", "occupancy_trend", "guest_satisfaction", "operational_metrics", "property_rankings", "performance_matrix", "recommendations"], "format": "telegram_digest", "compare_to": ["last_month", "same_month_last_year"]})}}
```

Example report:

```text
MONTHLY PERFORMANCE — March 2026

REVENUE:
- Total: $14,200 ($12,800 Feb, +10.9%)
- Best: Cedar Ridge Cabin ($5,800, RevPAN $187)
- Needs work: Harborfront Suite ($3,400, RevPAN $113)

OCCUPANCY:
- Portfolio avg: 74% (vs 68% Feb)
- Cedar Ridge: 84% | Harborfront: 60% | Orchard: 78%

GUEST SATISFACTION:
- Avg rating: 4.8/5.0
- Reviews received: 12 (solicitation rate 94%, conversion 48%)
- Escalations: 3 total (all resolved within SLA)

OPERATIONS:
- Cleaning on-time: 100% (22/22 dispatches)
- Avg approval queue time: 18 minutes
- Messages timed out: 1 (review solicitation — operator was unavailable)

PERFORMANCE MATRIX:
- Cedar Ridge Cabin: CHAMPION (high satisfaction, high revenue)
- Harborfront Suite: PROBLEM (low satisfaction 4.5, low revenue)
- Orchard Farmhouse: CHAMPION (high satisfaction, high revenue)

TOP 3 ACTION ITEMS:
1. Deep dive on Harborfront Suite — 5 escalations, 4.5 rating, 60% occupancy
2. Investigate timed-out review solicitation — process issue?
3. Update spring templates (pollen warnings for Cedar Ridge)
```

**Step 6: Create specific action items**

```text
{{daily_ops(action="create_action_items", data={"items": [{"action": "Audit all 5 Harborfront Suite escalations — categorize by root cause, identify patterns", "owner": "Operations Manager", "due": "2026-03-25", "priority": "P0", "source": "Monthly performance review — Harborfront in Problem quadrant"}, {"action": "Reduce Harborfront Suite midweek rate by 15% for April to stimulate occupancy", "owner": "Operations Manager", "due": "2026-03-27", "priority": "P1", "source": "Monthly review — 60% occupancy below 70% target"}, {"action": "Review approval workflow timing — investigate the timed-out review solicitation", "owner": "Operations Manager", "due": "2026-03-22", "priority": "P2", "source": "Monthly review — 1 missed solicitation"}]})}}
```

### Practice Exercise

**Scenario:** You have been running your three-property portfolio for 3 months. Here is your Q1 performance data:

| Metric | Cedar Ridge | Harborfront | Orchard Farm | Target |
|---|---|---|---|---|
| Occupancy | 82% | 58% | 76% | 70% |
| ADR | $240 | $180 | $260 | -- |
| RevPAN | $197 | $104 | $198 | $150 |
| Avg Review Score | 4.9 | 4.5 | 4.8 | 4.7 |
| Review Conversion | 52% | 35% | 48% | 40% |
| Cleaning On-Time | 100% | 96% | 100% | 99% |
| Escalations/Month | 2 | 5 | 1 | < 3 |
| Avg Response Time | 12 min | 45 min | 15 min | < 60 min |

**Task:**

1. Plot each property on the performance matrix
2. Identify the top 3 action items based on the data
3. Set specific, measurable improvement targets for Q2
4. Determine what additional data you need to diagnose Harborfront's issues

**Expected analysis:**

- **Cedar Ridge Cabin: Champion.** Exceeds targets on every metric. 82% occupancy, $197 RevPAN, 4.9 rating, 100% cleaning, only 2 escalations. This is your model property. Understand why it works and apply those patterns.

- **Harborfront Suite: Problem.** Below target on occupancy (58% vs 70%), satisfaction (4.5 vs 4.7), and cleaning (96% vs 99%). Five escalations per month is nearly double the target. Review conversion is low (35% vs 40%), possibly because guests had mediocre experiences. Response time (45 min) is within SLA but 3x longer than other properties — why?

- **Orchard Farmhouse: Champion.** Strong across all metrics. $198 RevPAN leads the portfolio. Only 1 escalation per month despite being the most complex property (rural, garden, chickens, fire pit). Well-configured.

**Performance matrix placement:**

```text
{{revenue_monitor(action="plot_performance_matrix", data={"properties": [{"name": "Cedar Ridge Cabin", "satisfaction": 4.9, "revpan": 197, "quadrant": "champion"}, {"name": "Harborfront Suite", "satisfaction": 4.5, "revpan": 104, "quadrant": "problem"}, {"name": "Orchard Farmhouse", "satisfaction": 4.8, "revpan": 198, "quadrant": "champion"}]})}}
```

**Top 3 action items for Q2:**

1. **Harborfront deep dive:** Read every escalation report and every review below 4.5 stars. Categorize issues. Is it the property (maintenance), the communication (response time), or the location (noise, parking)?
2. **Harborfront cleaning audit:** The 96% on-time rate means at least 1 clean was late. For a property with satisfaction issues, even one late clean compounds the problem. Investigate the miss and implement prevention.
3. **Harborfront rate and channel strategy:** At 58% occupancy and $180 ADR, consider reducing midweek rates by 15-20% to boost occupancy while investigating quality issues. Also check channel mix — if heavily OTA, the net revenue is even lower.

**Q2 targets for Harborfront Suite:**

| Metric | Q1 Actual | Q2 Target | How |
|---|---|---|---|
| Occupancy | 58% | 68% | Rate reduction + listing optimization |
| Avg Rating | 4.5 | 4.7 | Address root causes from escalation audit |
| Escalations | 5/month | 3/month | Fix the top 2 recurring issues |
| Cleaning On-Time | 96% | 100% | Investigate Q1 miss, add buffer time |
| Review Conversion | 35% | 42% | Improve experience first, conversion follows |

**Self-check:** Did you identify Harborfront as the clear underperformer needing immediate attention? Did your action items address root causes (what is causing the escalations?) rather than just symptoms (low occupancy)? Are your Q2 targets specific, measurable, and realistic? Did you resist the temptation to set "100% on everything" targets?

### Common Mistakes

| Mistake | Why It Happens | What To Do Instead |
|---|---|---|
| Only reviewing revenue and ignoring operational metrics | Revenue feels most important | Track response time, cleaning rate, and escalation count alongside revenue |
| Reviewing monthly but not acting on findings | Analysis paralysis or daily urgency takes over | Every monthly review must produce 2-3 specific action items with owners and due dates |
| Comparing properties without accounting for differences | Treating all properties as equal | Normalize by available nights, property size, and market segment |
| Focusing only on lagging indicators | They are easier to measure and understand | Track leading indicators (booking pace, response time) to predict problems early |
| Setting vague improvement goals ("do better at Harborfront") | Not investing time in specifics | Every goal needs a number and a deadline: "Increase occupancy from 58% to 68% by June 30" |
| Not celebrating wins and understanding success | Fixation on problems | Analyze why Cedar Ridge and Orchard succeed — those insights are as valuable as fixing failures |
| Reviewing data but not updating the playbook | Treating review as separate from operations | Every performance review finding should feed back into SOPs, runbooks, or system config |
| Reviewing quarterly instead of monthly | Thinking monthly is too frequent | Monthly catches problems in time to fix them; quarterly discovers problems that are already entrenched |
