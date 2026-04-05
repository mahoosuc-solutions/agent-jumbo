"""
Solution Catalog Tool
Manages the AI infrastructure solution catalog — list, create, update, publish to Stripe/Square/PayPal.
"""

import sys
from pathlib import Path

from python.helpers import files
from python.helpers.tool import Response, Tool

# Add instruments path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "instruments" / "custom"))


class SolutionCatalog(Tool):
    def __init__(self, agent, name, method, args, message, loop_data, **kwargs):
        super().__init__(agent, name, method, args, message, loop_data, **kwargs)
        from solution_catalog.catalog_manager import SolutionCatalogManager

        solutions_dir = files.get_abs_path("./solutions")
        self.manager = SolutionCatalogManager(solutions_dir)

    async def execute(self, **kwargs):
        """
        Execute solution catalog operations.

        Args:
            action (str): Action to perform — 'list', 'get', 'create', 'update',
                          'publish', 'dashboard', 'proposal_data'
            slug (str): Solution slug for get/update/publish/proposal_data
            name (str): Solution name (for create)
            category (str): Solution category (for create/list filter)
            status (str): Status filter for list
            data (dict): Additional data for create/update
        """
        action = self.args.get("action", "").lower()

        action_map = {
            "list": self._list_solutions,
            "get": self._get_solution,
            "create": self._create_solution,
            "update": self._update_solution,
            "publish": self._publish_to_stripe,
            "publish_to_provider": self._publish_to_provider,
            "dashboard": self._dashboard,
            "proposal_data": self._proposal_data,
        }

        handler = action_map.get(action)
        if not handler:
            valid = ", ".join(sorted(action_map.keys()))
            return Response(
                message=f"Unknown action: '{action}'. Valid actions: {valid}",
                break_loop=False,
            )

        try:
            return await handler()
        except Exception as e:
            return Response(message=f"Solution Catalog error: {e!s}", break_loop=False)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    async def _list_solutions(self) -> Response:
        """List all solutions with optional status/category filter."""
        status = self.args.get("status")
        category = self.args.get("category")

        solutions = self.manager.list_solutions(status=status, category=category)

        if not solutions:
            return Response(message="No solutions found matching criteria.", break_loop=False)

        lines = [f"**Solution Catalog: {len(solutions)} Solutions**\n"]

        # Group by category
        by_cat: dict[str, list] = {}
        for s in solutions:
            cat = s.get("category", "uncategorized")
            by_cat.setdefault(cat, []).append(s)

        for cat, items in sorted(by_cat.items()):
            lines.append(f"\n### {cat.replace('-', ' ').title()} ({len(items)})")
            for s in items:
                pricing = s.get("pricing", {})
                monthly = pricing.get("monthly", 0)
                setup = pricing.get("one_time_setup", 0)
                status_icon = {
                    "published": "🟢",
                    "ready": "🟡",
                    "draft": "⚪",
                }.get(s.get("status", "draft"), "⚪")

                price_str = ""
                if monthly:
                    price_str += f"${monthly:,.0f}/mo"
                if setup:
                    price_str += f" + ${setup:,.0f} setup" if price_str else f"${setup:,.0f} setup"
                if not price_str:
                    price_str = "TBD"

                lines.append(f"- {status_icon} **{s['name']}** — {price_str} — _{s.get('status', 'draft')}_")

        return Response(message="\n".join(lines), break_loop=False)

    async def _get_solution(self) -> Response:
        """Get detailed solution information."""
        slug = self.args.get("slug")
        if not slug:
            return Response(message="Error: 'slug' is required for get action.", break_loop=False)

        solution = self.manager.get_solution(slug)
        pricing = solution.get("pricing", {})
        monthly = pricing.get("monthly", 0)
        setup = pricing.get("one_time_setup", 0)

        detail = f"""## {solution["name"]}

**{solution.get("tagline", "")}**

**Details:**
- **Category**: {solution.get("category", "N/A")}
- **Tier**: {solution.get("tier", "N/A")}
- **Status**: {solution.get("status", "draft")}
- **Complexity**: {solution.get("complexity", "N/A")}
- **Deployment Time**: {solution.get("deployment_time_days", "N/A")} days
- **AI Agents Included**: {solution.get("ai_agents_included", 0)}

**Pricing:**
- Monthly: ${monthly:,.2f}
- One-Time Setup: ${setup:,.2f}
- Annual Discount: {pricing.get("annual_discount_pct", 0)}%

**Description:**
{solution.get("description", "No description.")}

**Instruments:** {", ".join(solution.get("instruments_required", [])) or "None"}
**Tools:** {", ".join(solution.get("tools_required", [])) or "None"}
**Integrations:** {", ".join(solution.get("integrations", [])) or "None"}
**Prerequisites:** {", ".join(solution.get("prerequisites", [])) or "None"}
"""

        if solution.get("stripe_product_id"):
            detail += f"\n**Stripe Product**: `{solution['stripe_product_id']}`"
        if solution.get("stripe_price_id"):
            detail += f"\n**Stripe Price**: `{solution['stripe_price_id']}`"

        architecture = solution.get("architecture_content")
        if architecture:
            detail += f"\n---\n{architecture}"

        return Response(message=detail, break_loop=False)

    async def _create_solution(self) -> Response:
        """Create a new solution from template."""
        name = self.args.get("name")
        slug = self.args.get("slug")
        category = self.args.get("category")

        if not all([name, slug, category]):
            return Response(
                message="Error: 'name', 'slug', and 'category' are required for create action.",
                break_loop=False,
            )

        extra = self.args.get("data", {})
        solution = self.manager.create_solution(name=name, slug=slug, category=category, **extra)

        return Response(
            message=f"Solution created: **{solution['name']}** (`{solution['slug']}`)\n"
            f"Status: {solution['status']}\n"
            f"Path: `solutions/{slug}/`",
            break_loop=False,
        )

    async def _update_solution(self) -> Response:
        """Update solution fields."""
        slug = self.args.get("slug")
        if not slug:
            return Response(message="Error: 'slug' is required for update action.", break_loop=False)

        updates = self.args.get("data", {})
        if not updates:
            return Response(message="Error: 'data' dict with updates is required.", break_loop=False)

        solution = self.manager.update_solution(slug, updates)
        return Response(
            message=f"Solution **{solution['name']}** updated.\nStatus: {solution.get('status', 'draft')}",
            break_loop=False,
        )

    async def _publish_to_stripe(self) -> Response:
        """Publish solution to Stripe as Product + Price."""
        slug = self.args.get("slug")
        if not slug:
            return Response(
                message="Error: 'slug' is required for publish action.",
                break_loop=False,
            )

        # Get Stripe manager from the stripe_payments instrument
        try:
            from instruments.custom.stripe_payments.stripe_manager import StripePaymentManager

            db_path = files.get_abs_path("./instruments/custom/stripe_payments/data/stripe_payments.db")
            stripe_mgr = StripePaymentManager(db_path)
        except Exception as e:
            return Response(
                message=f"Error: Could not initialize Stripe manager: {e!s}",
                break_loop=False,
            )

        result = self.manager.publish_to_stripe(slug, stripe_mgr)
        return Response(
            message=f"Solution published to Stripe.\n"
            f"- Product ID: `{result['stripe_product_id']}`\n"
            f"- Price ID: `{result.get('stripe_price_id', 'N/A')}`\n"
            f"- Setup Price ID: `{result.get('stripe_setup_price_id', 'N/A')}`\n"
            f"- Status: {result['status']}",
            break_loop=False,
        )

    async def _publish_to_provider(self) -> Response:
        """Publish solution to any payment provider (square, paypal, stripe) via PaymentRouter."""
        slug = self.args.get("slug")
        provider_name = (self.args.get("provider") or "stripe").lower()
        if not slug:
            return Response(
                message="Error: 'slug' is required for publish_to_provider action.",
                break_loop=False,
            )

        mock = bool(self.args.get("mock", False))

        try:
            from instruments.custom.stripe_payments.payment_router import PaymentRouter

            provider = PaymentRouter.get_provider(provider_name, mock=mock)
        except Exception as e:
            return Response(
                message=f"Error: Could not initialize {provider_name} provider: {e!s}",
                break_loop=False,
            )

        result = self.manager.publish_to_provider(slug, provider_name, provider)
        return Response(
            message=f"Solution published to {provider_name.title()}.\n"
            f"- Product ID: `{result['product_id']}`\n"
            f"- Price ID: `{result.get('price_id') or 'N/A'}`\n"
            f"- Setup Price ID: `{result.get('setup_price_id') or 'N/A'}`\n"
            f"- Status: {result['status']}",
            break_loop=False,
        )

    async def _dashboard(self) -> Response:
        """Get solution catalog dashboard."""
        stats = self.manager.get_dashboard()

        dashboard = f"""## Solution Catalog Dashboard

### Overview
- **Total Solutions**: {stats["total_solutions"]}
- **Monthly Revenue Potential**: ${stats["total_monthly_revenue_potential"]:,.2f}
- **Setup Revenue Potential**: ${stats["total_setup_revenue_potential"]:,.2f}

### By Status
| Status | Count |
|--------|-------|
"""

        for status, count in sorted(stats["by_status"].items()):
            dashboard += f"| {status.title()} | {count} |\n"

        dashboard += "\n### By Category\n| Category | Count |\n|----------|-------|\n"

        for cat, count in sorted(stats["by_category"].items()):
            dashboard += f"| {cat.replace('-', ' ').title()} | {count} |\n"

        # Top solutions summary
        if stats["solutions"]:
            dashboard += "\n### Solutions\n"
            for s in stats["solutions"]:
                pricing = s.get("pricing", {})
                monthly = pricing.get("monthly", 0)
                icon = "🟢" if s.get("status") == "published" else "🟡" if s.get("status") == "ready" else "⚪"
                dashboard += f"- {icon} **{s['name']}** ({s.get('category', 'N/A')}) — ${monthly:,.0f}/mo\n"

        return Response(message=dashboard, break_loop=False)

    async def _proposal_data(self) -> Response:
        """Extract proposal data for sales_generator."""
        slug = self.args.get("slug")
        if not slug:
            return Response(
                message="Error: 'slug' is required for proposal_data action.",
                break_loop=False,
            )

        data = self.manager.generate_proposal_data(slug)

        pricing = data["pricing"]
        deliverables = data["deliverables"]

        result = f"""## Proposal Data: {data["solution_name"]}

**{data.get("tagline", "")}**

**Category**: {data["category"]} | **Tier**: {data["tier"]} | **Complexity**: {data["complexity"]}

**Pricing:**
- Monthly: ${pricing["monthly"]:,.2f}
- One-Time Setup: ${pricing["one_time_setup"]:,.2f}
- Annual Discount: {pricing["annual_discount_pct"]}%

**Timeline:** {data["timeline_days"]} days | **AI Agents:** {data["ai_agents_included"]}

**Deliverables:**
- Instruments: {", ".join(deliverables["instruments"]) or "None"}
- Tools: {", ".join(deliverables["tools"]) or "None"}
- Integrations: {", ".join(deliverables["integrations"]) or "None"}

**Prerequisites:** {", ".join(data["prerequisites"]) or "None"}

**Description:**
{data["description"]}
"""

        return Response(message=result, break_loop=False)
