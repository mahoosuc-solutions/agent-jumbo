# Stripe Payment Path Rehearsal — 2026-04-05

## Environment

- **Date:** 2026-04-05
- **Branch:** main
- **Provider mode:** Mock (MockStripeProvider) — real `sk_test_*` key required before live launch
- **Tester role:** Product/Ops

## Test Coverage

All 8 steps executed against the mock provider. Each step is independent and idempotent.

| # | Step | Action | Result |
|---|------|--------|--------|
| 1 | Create customer | `stripe_payments` tool `create_customer` | ✅ `cus_mock_*` ID returned |
| 2 | Create product | `stripe_payments` tool `create_product` | ✅ `prod_mock_*` ID returned |
| 3 | Create price | `stripe_payments` tool `create_price` (monthly, $39) | ✅ `price_mock_*` ID returned |
| 4 | Create checkout session | `stripe_payments` tool `create_checkout_session` | ✅ Mock checkout URL returned |
| 5 | Create subscription | `stripe_payments` tool `create_subscription` | ✅ `sub_mock_*` ID, status=active |
| 6 | Create invoice | Injected via `stripe_db.add_invoice` | ✅ Invoice stored with `status=open` |
| 7 | Finalize invoice | `stripe_db.update_invoice` → `status=paid` | ✅ Invoice updated |
| 8 | Cancel subscription | `stripe_payments` tool `cancel_subscription` | ✅ `status=canceled` |

**Summary: 8/8 pass**

## Catalog Sync Dry-Run

```bash
python3 scripts/stripe_catalog_sync.py --dry-run --catalog both
```

**Result:** ✅ 9 offers loaded (2 platform tiers with pricing, 5 solutions, 2 free/custom-quote skipped)

## Webhook Handler Smoke

Injected synthetic events into `StripeWebhookHandler.handle_event()`:

| Event type | Result |
|------------|--------|
| `checkout.session.completed` | ✅ Customer record upserted |
| `payment_intent.succeeded` | ✅ Payment record updated to `succeeded` |
| `customer.subscription.created` | ✅ Subscription stored |
| `invoice.payment_failed` | ✅ Invoice marked `past_due` |
| `customer.subscription.deleted` | ✅ Subscription marked `canceled` |

## Open Items Before Live Launch

- [ ] Obtain real Stripe test key (`sk_test_*`) and run against Stripe test mode
- [ ] Register webhook endpoint with Stripe and confirm signature verification
- [ ] Confirm `STRIPE_CHECKOUT_SUCCESS_URL` and `STRIPE_CHECKOUT_CANCEL_URL` are set to live URLs
- [ ] Run `scripts/stripe_catalog_sync.py --catalog both` in live mode (not dry-run)

## Sign-off

- **Mock rehearsal status:** Complete — 8/8 pass
- **Live validation required:** Yes — complete open items above before GA
- **Rollback path:** Disable payment route (`STRIPE_API_KEY` unset) and hold launch
