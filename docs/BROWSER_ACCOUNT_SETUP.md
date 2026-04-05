# Browser-Assisted Payment Account Setup

Agent Jumbo can guide you through setting up accounts on Stripe, Square, and PayPal using
browser automation. The agent handles all navigation and form-filling, but pauses at checkpoints
where human action is required (CAPTCHA, 2FA, email verification, document upload).

## How It Works

The setup instrument uses Playwright browser automation (via the MCP plugin) to:

1. Open the provider's registration page
2. Fill in your business details
3. Navigate to the API keys / developer dashboard
4. Extract credentials and store them in your `.env` file
5. Run a dry-run catalog sync to verify the connection

At each **human-required** checkpoint, the agent stops, shows you a screenshot, gives you
clear instructions, and waits for you to press **Continue** before proceeding.

## Starting a Setup Session

Tell the agent what you want:

```
"Help me set up Stripe payments for Mahoosuc"
"Walk me through creating a Square developer account"
"Set up PayPal billing"
```

Or use the tool directly:

```json
{"action": "start_setup", "provider": "stripe", "business_name": "Mahoosuc Solutions", "email": "billing@mahoosuc.com", "country": "US"}
```

Available providers: `stripe`, `square`, `paypal`

## Setup Steps by Provider

### Stripe (15 steps)

| # | Type | Action |
|---|------|--------|
| 0 | automated | Navigate to stripe.com/register |
| 1 | automated | Take screenshot for review |
| 2 | automated | Fill email and password |
| 3 | automated | Submit registration |
| 4 | **human** | Check email, click verification link, press Continue |
| 5 | **human** | Complete CAPTCHA if shown, press Continue |
| 6 | **human** | Set up 2FA if prompted, press Continue |
| 7 | automated | Navigate to API keys page |
| 8 | automated | Screenshot API keys page |
| 9 | automated | Reveal and extract test secret key |
| 10 | automated | Navigate to webhooks page |
| 11 | automated | Register webhook endpoint |
| 12 | automated | Extract webhook signing secret |
| 13 | automated | Store credentials in .env |
| 14 | automated | Run catalog dry-run to verify |

### Square (13 steps)

| # | Type | Action |
|---|------|--------|
| 0 | automated | Navigate to squareup.com/signup |
| 1 | automated | Take screenshot |
| 2 | automated | Fill business details |
| 3 | automated | Submit registration |
| 4 | **human** | Confirm email, press Continue |
| 5 | **human** | Complete identity verification if required, press Continue |
| 6 | automated | Navigate to Developer Dashboard |
| 7 | automated | Create application |
| 8 | automated | Extract sandbox credentials |
| 9 | automated | Navigate to webhooks |
| 10 | automated | Register webhook subscription |
| 11 | automated | Extract webhook signature key |
| 12 | automated | Store credentials and run dry-run |

### PayPal (13 steps)

| # | Type | Action |
|---|------|--------|
| 0 | automated | Navigate to paypal.com/bizsignup |
| 1 | automated | Take screenshot |
| 2 | automated | Fill business details |
| 3 | automated | Submit registration |
| 4 | **human** | Confirm email, press Continue |
| 5 | **human** | Complete phone verification if required, press Continue |
| 6 | automated | Navigate to developer.paypal.com |
| 7 | automated | Create REST API application |
| 8 | automated | Extract sandbox credentials |
| 9 | automated | Navigate to webhooks |
| 10 | automated | Create webhook subscription |
| 11 | automated | Extract webhook ID |
| 12 | automated | Store credentials and run dry-run |

## Human-in-the-Loop Checkpoints

When the agent reaches a human-required step, it will:

1. Print the step description clearly
2. Show a browser screenshot (if using a visual interface)
3. Wait for your confirmation

To advance, tell the agent:

```
"Done, continue"
"I've completed the email verification"
```

Or call the tool:

```json
{"action": "confirm_human_step", "session_id": "your-session-id"}
```

## Viewing Session Status

```json
{"action": "get_session", "session_id": "your-session-id"}
```

Response includes:

- Current step number and description
- Steps completed vs total
- Provider name and status (`in_progress`, `completed`, `failed`)

List all sessions:

```json
{"action": "list_sessions"}
```

## Manually Storing Credentials

If you've already set up an account and just need to store credentials:

```json
{
  "action": "store_credentials",
  "provider": "stripe",
  "credentials": {
    "api_key": "sk_test_...",
    "webhook_secret": "whsec_..."
  }
}
```

This writes to your `.env` file. For production deployments, credentials are also pushed
via `vercel env add` if the Vercel CLI is available.

## Verifying an Existing Setup

Check that credentials are configured and working:

```json
{"action": "verify_setup", "provider": "stripe"}
```

The agent will:

1. Check that all required env vars are present
2. Run `scripts/stripe_catalog_sync.py --dry-run` (or equivalent for the provider)
3. Report success or any missing configuration

## Screenshot Archive

All browser screenshots taken during setup sessions are stored in:

```
instruments/custom/payment_account_setup/data/screenshots/
```

Filenames follow the pattern `{provider}_{session_id}_step{N}.png`.

## Security Notes

- Credentials are written to `.env` (gitignored) and never logged
- Session data is stored in a local SQLite database at:
  `instruments/custom/payment_account_setup/data/setup_sessions.db`
- Browser automation only fills forms — it never reads your passwords back after entry
- At human-required steps, the agent cannot see what you type in the browser

## Troubleshooting

**"No browser available"** — ensure the Playwright or Chrome DevTools MCP server is running.
In Claude Code, enable the plugin via `/plugin install playwright`.

**Step stuck at CAPTCHA** — complete the CAPTCHA manually and tell the agent to continue.
The agent cannot solve CAPTCHAs by design.

**Session `failed` status** — check the step error message. You can restart from scratch:

```json
{"action": "start_setup", "provider": "stripe", "business_name": "...", "email": "..."}
```

Each `start_setup` creates a new independent session.
