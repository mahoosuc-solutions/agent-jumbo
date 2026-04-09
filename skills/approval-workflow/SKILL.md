---
name: approval-workflow
version: 1.0.0
author: agent-mahoo
tier: 1
trust_level: local
categories:
  - workflow
  - communications
  - approval
capabilities:
  - draft-review-approve
  - approval-commands
  - timeout-handling
description: Draft-review-approve cycle for guest messages, emails, and proposals. Defines approval commands, timeout handling, and escalation patterns.
---

# Approval Workflow

## Purpose

Define the draft-review-approve cycle used when automated tasks generate messages that require human review before being sent to guests, clients, or external parties.

## Draft-review-approve cycle

### Step 1: Draft

The scheduled task generates a message draft and sends it to Telegram with an approval prefix.

Format:

```text
[APPROVE] {message_type} for {recipient_name}:

{draft message content}

Reply: send | skip | edit: {changes}
```

### Step 2: Review

The operator reviews the draft in Telegram and responds with one of the approval commands.

### Step 3: Execute

Based on the operator's response:

- **send**: Message is sent to the recipient as-is
- **skip**: Message is discarded, no action taken
- **edit: {changes}**: Message is revised per the operator's instructions and re-sent for approval

## Approval commands

| Command | Action | Example |
|---------|--------|---------|
| `send` | Send the draft as-is to the recipient | "send" |
| `skip` | Discard the draft, take no action | "skip" |
| `edit: {changes}` | Revise the draft and re-present for approval | "edit: make it shorter" |
| `send all` | Approve all pending drafts in the batch | "send all" |
| `skip all` | Discard all pending drafts in the batch | "skip all" |

Commands are case-insensitive. Partial matches work: "s" = send, "sk" = skip.

## Which messages require approval

| Message type | Approval required | Reason |
|--------------|-------------------|--------|
| Guest pre-arrival | Yes | Personalized, represents the business |
| Guest mid-stay check-in | Yes | Tone-sensitive, context-dependent |
| Review solicitation | Yes | Reputation impact |
| Proposal follow-up | Yes | Client relationship sensitive |
| Cleaning dispatch | No | Internal operational, time-sensitive |
| New booking alert | No | Informational, no outbound message |
| Morning briefing | No | Internal digest |
| EOD status | No | Internal digest |

## Timeout handling

If no response to an approval request within the timeout window:

| Message type | Timeout | Action on timeout |
|--------------|---------|-------------------|
| Guest pre-arrival | 2 hours | Auto-skip, log as missed |
| Guest mid-stay | 4 hours | Auto-skip, log as missed |
| Review solicitation | No timeout | Stays pending until next day's batch |
| Proposal follow-up | 8 hours | Auto-skip, reschedule for next eligible day |

On timeout, send a brief notification: "Approval timed out for {message_type} to {recipient}. Skipped."

## Batch approval

When multiple drafts are generated in one task run (e.g., pre-arrival messages for 3 guests):

1. Send all drafts as separate Telegram messages
2. Add a summary message at the end: "3 drafts pending approval. Reply 'send all' or review individually."
3. Individual approvals override batch commands for specific messages

## Error handling

- If the recipient's contact info is missing, skip the draft and note it in the approval message
- If the PMS data is stale (>24h old), add a warning to the draft: "[Data may be outdated]"
- If Telegram send fails, retry once after 60 seconds, then log the failure
