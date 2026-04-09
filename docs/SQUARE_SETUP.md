# Square Payment Platform Setup

This guide walks through creating a Square developer account and connecting it to Agent Mahoo.

## Prerequisites

- A Square merchant account (or create one at squareup.com)
- Access to the Square Developer Portal at developer.squareup.com

## Step 1 — Create a Square Developer Account

1. Go to [developer.squareup.com](https://developer.squareup.com)
2. Sign in with your Square merchant account, or create a new one
3. Accept the developer terms of service

## Step 2 — Create an Application

1. From the Developer Dashboard, click **Create Your First Application**
2. Name it `Agent Mahoo` (or your business name)
3. Select **Production** as the environment once you're ready for live payments; use **Sandbox** for testing
4. Click **Save**

## Step 3 — Get Your Access Token

**Sandbox:**

1. Open your application → **Credentials** tab
2. Under **Sandbox**, copy the **Sandbox Access Token** (starts with `EAAAl...`)
3. Copy the **Sandbox Application ID** (starts with `sq0idp-...`)

**Production:**

1. Switch to the **Production** tab
2. Copy the **Production Access Token** and **Application ID**

## Step 4 — Configure Webhooks

1. In your application, click the **Webhooks** tab
2. Click **Add Webhook Subscription**
3. Set the **Notification URL** to: `https://your-domain.com/api/webhooks/square`
4. Select events:
   - `payment.updated`
   - `invoice.payment_failed`
   - `subscription.updated`
5. Click **Save** — Square will show you a **Signature Key** (copy it)

## Step 5 — Add Environment Variables

Add to your `.env` file (or via `vercel env add` for production):

```bash
SQUARE_ACCESS_TOKEN=EAAAl...
SQUARE_APPLICATION_ID=sq0idp-...
SQUARE_WEBHOOK_SIGNATURE_KEY=...
SQUARE_ENVIRONMENT=sandbox   # change to 'production' when ready
```

## Step 6 — Sync Your Catalog

Run a dry-run first to preview what will be created:

```bash
python3 scripts/square_catalog_sync.py --dry-run --catalog both
```

Then sync for real:

```bash
# Sync platform tiers only
python3 scripts/square_catalog_sync.py --catalog tiers

# Sync solution packages only
python3 scripts/square_catalog_sync.py --catalog solutions --output artifacts/square-sync.json

# Sync everything
python3 scripts/square_catalog_sync.py --catalog both
```

## Step 7 — Verify with Mock Provider

Test the integration without hitting the Square API:

```bash
python3 scripts/square_catalog_sync.py --mock --catalog both
```

## Browser-Assisted Setup

Agent Mahoo can guide you through account setup interactively:

```
Ask the agent: "Help me set up Square payments"
```

The agent will open a browser session, walk through each step, and pause at points
requiring human action (CAPTCHA, 2FA, email confirmation). See
[docs/BROWSER_ACCOUNT_SETUP.md](./BROWSER_ACCOUNT_SETUP.md) for details.

## Key Differences from Stripe

| Feature | Stripe | Square |
|---------|--------|--------|
| Billing portal | Hosted (Stripe-managed) | Dashboard deep-link only |
| Idempotency | Optional header | Required UUID per write |
| Webhooks | HMAC-SHA256 on payload | HMAC-SHA256 on body |
| Prices | Stripe Price objects | Catalog `ITEM_VARIATION` objects |

## Troubleshooting

**`401 Unauthorized`** — check that `SQUARE_ACCESS_TOKEN` matches the environment (`sandbox` vs `production`).

**`409 Conflict`** — Square's idempotency key was reused with different data; rotate the key and retry.

**Webhook signature mismatch** — ensure `SQUARE_WEBHOOK_SIGNATURE_KEY` is set from the **Webhooks** tab, not the credentials tab.
