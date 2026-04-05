---
title: Stripe Setup For Mahoosuc.ai
description: Manual Stripe account bootstrap plus catalog sync workflow for platform tiers and solution packages.
date: 2026-04-05
---

# Stripe Setup For Mahoosuc.ai

This document is the canonical setup path for Stripe test-mode provisioning of the Mahoosuc.ai commercial catalog.

## What This Covers

- Stripe CLI login to the Mahoosuc Solutions account
- test-mode API key setup
- webhook secret capture
- sync of:
  - platform subscription tiers from `docs/product-page/pricing-model.json`
  - solution packages from `solutions/*/solution.json`

## Important Constraint

The Stripe business account itself must be created manually in Stripe. The Stripe CLI can authenticate and manage that account, but it does not replace the initial Stripe account signup flow.

## Environment

Set these values before running the sync or webhook validation steps:

```bash
export STRIPE_API_KEY=sk_test_...
export STRIPE_WEBHOOK_SECRET=whsec_...
export STRIPE_CHECKOUT_SUCCESS_URL=https://mahoosuc.ai/billing/success
export STRIPE_CHECKOUT_CANCEL_URL=https://mahoosuc.ai/billing/cancel
```

## Stripe CLI Login

Use an isolated config path if you do not want to write into the default Stripe CLI config directory:

```bash
XDG_CONFIG_HOME=/tmp/stripe-config stripe login
```

## Webhook Secret

To print a test-mode webhook signing secret for the local webhook endpoint:

```bash
XDG_CONFIG_HOME=/tmp/stripe-config stripe listen \
  --print-secret \
  --forward-to http://localhost:6274/api/stripe/webhook
```

## Dry Run The Catalog

```bash
python3 scripts/stripe_catalog_sync.py --dry-run --catalog both
```

## Sync Test-Mode Catalog

```bash
python3 scripts/stripe_catalog_sync.py \
  --catalog both \
  --output artifacts/validation/stripe-catalog-sync-test.json
```

## Catalog Model

- Platform tiers:
  - `Community (Free)` is treated as a free tier and does not create a paid price
  - `Enterprise Custom` is treated as custom quote and does not create a fixed Stripe price
  - paid tiers create recurring monthly prices
- Solution packages:
  - create one-time setup prices
  - create recurring monthly prices

## Verification

Recommended checks after sync:

```bash
python3 scripts/stripe_catalog_sync.py --dry-run --catalog both
```

Then verify in Stripe Dashboard or CLI that products and prices exist for:

- `mahoosuc_platform_tier_pro`
- `mahoosuc_platform_tier_enterprise`
- `mahoosuc_solution_package_ai_customer_support`
- `mahoosuc_solution_package_ai_document_processing`
- `mahoosuc_solution_package_ai_financial_reporting`
- `mahoosuc_solution_package_ai_property_management`
- `mahoosuc_solution_package_ai_sales_automation`

## Notes

- The sync uses deterministic product IDs and price lookup keys so reruns are idempotent.
- When pricing changes, the sync creates a new price and transfers the lookup key to it.
- The repo does not write Stripe account-specific product IDs back into public pricing docs for tiers. The stable identifiers are derived from the catalog itself.
