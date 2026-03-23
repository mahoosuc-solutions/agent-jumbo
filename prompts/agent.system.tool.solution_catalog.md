# Solution Catalog Tool

The **solution_catalog** tool manages the AI Infrastructure Solutions marketplace. It lists, creates, and publishes deployable AI solutions with pricing, architecture docs, and Stripe integration.

## Available Actions

### list
List all available AI solutions with status and pricing.
- **status** (optional): Filter by status (draft, ready, listed, sold)
- **category** (optional): Filter by category
- Returns: list of solutions with name, category, pricing, status

### get
Get full details for a specific solution including architecture content.
- **slug** (required): Solution slug (e.g., "ai-customer-support")
- Returns: complete solution details with architecture markdown

### create
Scaffold a new solution from the template.
- **name** (required): Solution name
- **slug** (required): URL-safe slug
- **category** (required): Solution category
- Returns: created solution with file paths

### update
Update a solution's metadata.
- **slug** (required): Solution to update
- **updates** (required): Fields to update (name, pricing, status, etc.)

### publish
Sync a solution to Stripe as a Product + Price.
- **slug** (required): Solution to publish
- Returns: Stripe product ID, price ID, and sync status

### dashboard
Get a summary of the solution catalog.
- Returns: counts by status, total revenue potential, categories

### proposal_data
Extract data for generating a sales proposal for a solution.
- **slug** (required): Solution slug
- Returns: structured data for the sales_generator tool

## Available Solutions

- **ai-customer-support**: Multi-channel AI support ($3,500 + $750/mo)
- **ai-document-processing**: Document ingestion and extraction ($5,000 + $1,200/mo)
- **ai-sales-automation**: Lead qualification and pipeline management ($4,000 + $900/mo)
- **ai-property-management**: Rental property automation ($2,500 + $500/mo)
- **ai-financial-reporting**: Automated financial analysis ($3,000 + $600/mo)

## Example

```json
{
    "tool_name": "solution_catalog",
    "tool_args": {
        "action": "list"
    }
}
```
