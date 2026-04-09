---
name: hospitality-ops
version: 1.0.0
author: agent-mahoo
tier: 1
trust_level: local
categories:
  - hospitality
  - operations
  - guest-communications
capabilities:
  - guest-messaging
  - cleaning-dispatch
  - review-solicitation
  - pms-data-interpretation
description: Guest communication templates, cleaning priority logic, review solicitation, and PMS data interpretation for vacation rental operations.
---

# Hospitality Operations

## Purpose

Provide operational patterns for vacation rental management: guest messaging, cleaning coordination, review collection, and PMS data interpretation.

## Guest communication templates

### Pre-arrival message

Tone: warm, professional, anticipatory. Include:

- First-name greeting
- Check-in time and property address
- Key/access instructions (pulled from property notes in PMS)
- One seasonal local tip
- "Reach out anytime" closing

Length: 4-6 sentences. Never corporate-sounding.

### Mid-stay check-in

Tone: casual, caring. Sent 1-2 days after check-in. Include:

- "How's everything going?" opening
- One local recommendation (restaurant, trail, activity)
- Reminder that help is available

Length: 2-3 sentences. Never pushy.

### Review solicitation

Tone: genuine, grateful, brief. Sent evening of check-out day. Include:

- Thank them by name, reference the property
- Simple ask: "Would you share your experience?"
- Direct review link if available
- No incentives or pressure

Length: 3-4 sentences max.

### Escalation message

Tone: empathetic, solution-focused. Used when a guest reports a problem. Include:

- Acknowledge the issue immediately
- Provide a concrete next step and timeline
- Offer alternative if resolution is delayed

## Cleaning priority logic

Priority tiers for daily cleaning dispatch:

| Priority | Condition | Action |
|----------|-----------|--------|
| URGENT | Same-day turnover (checkout + checkin same day) | Clean first, alert operator |
| HIGH | Checkout today, checkin tomorrow | Clean by end of day |
| NORMAL | Checkout today, no checkin within 48h | Clean at convenience |
| LOW | Periodic deep clean, no guest turnover | Schedule for slow period |

When dispatching, always include:

- Property name and unit number
- Checkout time (so cleaners know when to arrive)
- Next checkin time (so cleaners know the deadline)
- Any special instructions from PMS notes

## Review solicitation timing

- Send review request on checkout day at 9 PM (guest is settled, reflecting on trip)
- If no response after 3 days, do NOT follow up (one ask only)
- Never send review requests for stays under 2 nights
- Never send if guest reported an unresolved issue during stay

## PMS data interpretation

When reading PMS data:

- Reservation status: confirmed, pending, cancelled, checked-in, checked-out
- "Blocked" dates are owner holds, not bookings — exclude from occupancy calculations
- Channel source matters: direct bookings have no commission; OTA bookings (Airbnb, VRBO) have 3-15% commission
- ADR = total revenue / occupied nights (exclude blocked dates)
- RevPAN = total revenue / available nights (include vacant, exclude blocked)

## Escalation rules

Escalate to operator via Telegram immediately for:

- Guest complaint about safety issue (water, heat, locks)
- Booking cancellation within 48h of check-in
- Payment failure or dispute
- Double-booking detected
- Cleaning not completed 2 hours before check-in
