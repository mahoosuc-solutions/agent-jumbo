# PayPal Payment Platform Setup

This guide walks through creating a PayPal developer account and connecting it to Agent Mahoo.

## Prerequisites

- A PayPal Business account (or create one at paypal.com/bizsignup)
- Access to the PayPal Developer Dashboard at developer.paypal.com

## Step 1 — Create a PayPal Developer Account

1. Go to [developer.paypal.com](https://developer.paypal.com)
2. Click **Log in to Dashboard** — use your PayPal Business account credentials
3. If you don't have a Business account, create one first at [paypal.com/bizsignup](https://www.paypal.com/bizsignup)

## Step 2 — Create a REST API Application

1. In the Developer Dashboard, go to **Apps & Credentials**
2. Make sure **Sandbox** tab is selected for testing
3. Click **Create App**
4. Name it `Agent Mahoo`, select **Merchant** as app type
5. Click **Create App**
6. Copy the **Client ID** and **Secret**

Switch to the **Live** tab and repeat when ready for production.

## Step 3 — Get Your Credentials

**Sandbox credentials:**

```
PAYPAL_CLIENT_ID=AaBb...  (from Sandbox tab)
PAYPAL_CLIENT_SECRET=EeFf...
PAYPAL_ENVIRONMENT=sandbox
```

**Production credentials:**

```
PAYPAL_CLIENT_ID=...  (from Live tab)
PAYPAL_CLIENT_SECRET=...
PAYPAL_ENVIRONMENT=production
```

## Step 4 — Configure Webhooks

1. In your app settings, scroll to **Webhooks**
2. Click **Add Webhook**
3. Set the **Webhook URL** to: `https://your-domain.com/api/webhooks/paypal`
4. Select events:
   - `BILLING.SUBSCRIPTION.ACTIVATED`
   - `BILLING.SUBSCRIPTION.CANCELLED`
   - `PAYMENT.SALE.COMPLETED`
   - `PAYMENT.SALE.DENIED`
   - `INVOICING.INVOICE.PAID`
5. Click **Save** — PayPal will assign a **Webhook ID** (copy it)

## Step 5 — Add Environment Variables

Add to your `.env` file (or via `vercel env add` for production):

```bash
PAYPAL_CLIENT_ID=AaBb...
PAYPAL_CLIENT_SECRET=EeFf...
PAYPAL_WEBHOOK_ID=...
PAYPAL_ENVIRONMENT=sandbox   # change to 'production' when ready
```

## Step 6 — Sync Your Catalog

PayPal catalog sync creates Products and Billing Plans:

```bash
# Dry-run preview
python3 scripts/paypal_catalog_sync.py --dry-run --catalog both

# Sync platform tiers
python3 scripts/paypal_catalog_sync.py --catalog tiers

# Sync solution packages
python3 scripts/paypal_catalog_sync.py --catalog solutions --output artifacts/paypal-sync.json

# Sync everything
python3 scripts/paypal_catalog_sync.py --catalog both
```

## Step 7 — Verify with Mock Provider

Test without hitting the PayPal API:

```bash
python3 scripts/paypal_catalog_sync.py --mock --catalog both
```

## Browser-Assisted Setup

Agent Mahoo can guide you through account setup interactively:

```
Ask the agent: "Help me set up PayPal payments"
```

The agent will open a browser session and walk through each step, pausing at human-required
checkpoints (CAPTCHA, 2FA, email verification). See
[docs/BROWSER_ACCOUNT_SETUP.md](./BROWSER_ACCOUNT_SETUP.md) for details.

## OAuth Token Caching

Agent Mahoo caches PayPal OAuth tokens at the module level (keyed by `client_id`). Tokens
expire every 30 minutes; the cache refreshes automatically with a 5-minute buffer. This means
your first request after a cold start will be slightly slower (~200ms) while the token is
fetched.

## Key Differences from Stripe

| Feature | Stripe | PayPal |
|---------|--------|--------|
| Auth | API key | OAuth2 client credentials |
| Subscriptions | Stripe Price + Subscription | Product + Billing Plan + Agreement |
| Billing portal | Hosted (Stripe-managed) | PayPal account management deep-link |
| Webhook verification | HMAC-SHA256 | PayPal verify-webhook-signature API |
| Setup fees | Stripe one-time Price | Separate product + one-time payment |

## Troubleshooting

**`401 Unauthorized`** — OAuth token may have expired or `PAYPAL_CLIENT_SECRET` is wrong.
The provider will auto-retry the token fetch on the next call.

**`INSTRUMENT_DECLINED`** — The buyer's payment method was declined. Check the PayPal
sandbox dashboard for detailed decline reason codes.

**Webhook `VALIDATION_FAILURE`** — Ensure `PAYPAL_WEBHOOK_ID` matches the ID shown in
the Developer Dashboard webhook list, not the URL or event ID.

**Sandbox vs Production mismatch** — PayPal sandbox and production use different base URLs
(`api-m.sandbox.paypal.com` vs `api-m.paypal.com`). Set `PAYPAL_ENVIRONMENT` correctly.
