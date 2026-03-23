# Stripe Payments Tool

The **stripe_payments** tool handles payment processing through Stripe. It manages customers, products, invoices, checkout sessions, subscriptions, and revenue reporting.

## Available Actions

### Customer Management
- **create_customer**: Create a Stripe customer. Args: email, name, metadata
- **sync_customer**: Sync a lifecycle customer to Stripe. Args: lifecycle_customer_id
- **list_customers**: List all Stripe customers

### Product Management
- **sync_product**: Sync a portfolio product to Stripe. Args: portfolio_product_id
- **sync_all_products**: Sync all listed portfolio products to Stripe
- **list_products**: List all Stripe products

### Payments
- **create_checkout**: Create a checkout session URL. Args: portfolio_product_id, customer_email
- **create_invoice**: Create an invoice from a proposal. Args: proposal_id, lifecycle_customer_id
- **list_payments**: List payment activity
- **list_invoices**: List all invoices with status

### Subscriptions
- **create_subscription**: Create a subscription. Args: stripe_customer_id, stripe_price_id, trial_days
- **cancel_subscription**: Cancel a subscription. Args: subscription_id, at_period_end
- **list_subscriptions**: List subscriptions. Args: status (optional)

### Reporting
- **mrr**: Get current Monthly Recurring Revenue
- **revenue_report**: Generate revenue report. Args: days (default 30)
- **churn_report**: Generate churn analysis. Args: days (default 30)
- **dashboard**: Full payments dashboard with MRR, subscriptions, revenue, and churn

### Mock Mode
Pass **mock: true** to any action to use the mock provider (no real Stripe API calls).

## Example

```json
{
    "tool_name": "stripe_payments",
    "tool_args": {
        "action": "dashboard",
        "mock": false
    }
}
```
