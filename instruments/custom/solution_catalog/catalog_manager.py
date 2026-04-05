"""
Solution Catalog Manager
Filesystem-based catalog of AI infrastructure solutions (no SQLite needed).
Each solution lives in solutions/{slug}/ with a solution.json and architecture.md.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone


class SolutionCatalogManager:
    def __init__(self, solutions_dir: str):
        self.solutions_dir = solutions_dir
        self.template_dir = os.path.join(solutions_dir, "_template")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _solution_path(self, slug: str) -> str:
        return os.path.join(self.solutions_dir, slug)

    def _read_solution_json(self, slug: str) -> dict | None:
        path = os.path.join(self._solution_path(slug), "solution.json")
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            return json.load(f)

    def _write_solution_json(self, slug: str, data: dict) -> None:
        path = os.path.join(self._solution_path(slug), "solution.json")
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    def _read_architecture(self, slug: str) -> str | None:
        path = os.path.join(self._solution_path(slug), "architecture.md")
        if not os.path.isfile(path):
            return None
        with open(path) as f:
            return f.read()

    def _iter_slugs(self) -> list[str]:
        """Return slugs of all solutions (excluding _template and hidden dirs)."""
        if not os.path.isdir(self.solutions_dir):
            return []
        return sorted(
            d
            for d in os.listdir(self.solutions_dir)
            if not d.startswith("_")
            and not d.startswith(".")
            and os.path.isdir(os.path.join(self.solutions_dir, d))
            and os.path.isfile(os.path.join(self.solutions_dir, d, "solution.json"))
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_solutions(self, status: str | None = None, category: str | None = None) -> list[dict]:
        """List all solutions, optionally filtered by status/category."""
        results = []
        for slug in self._iter_slugs():
            data = self._read_solution_json(slug)
            if data is None:
                continue
            if status and data.get("status") != status:
                continue
            if category and data.get("category") != category:
                continue
            results.append(data)
        return results

    def get_solution(self, slug: str) -> dict:
        """Get full solution details including architecture content."""
        data = self._read_solution_json(slug)
        if data is None:
            raise FileNotFoundError(f"Solution '{slug}' not found")
        architecture = self._read_architecture(slug)
        if architecture:
            data["architecture_content"] = architecture
        return data

    def create_solution(self, name: str, slug: str, category: str, **kwargs) -> dict:
        """Scaffold a new solution from _template/."""
        dest = self._solution_path(slug)
        if os.path.exists(dest):
            raise FileExistsError(f"Solution '{slug}' already exists")

        # Copy template
        if os.path.isdir(self.template_dir):
            shutil.copytree(self.template_dir, dest)
        else:
            os.makedirs(dest, exist_ok=True)

        # Build solution.json
        now = datetime.now(timezone.utc).isoformat()
        data = {
            "name": name,
            "slug": slug,
            "version": kwargs.get("version", "1.0.0"),
            "category": category,
            "tier": kwargs.get("tier", "professional"),
            "tagline": kwargs.get("tagline", ""),
            "description": kwargs.get("description", ""),
            "pricing": kwargs.get(
                "pricing",
                {
                    "one_time_setup": 0,
                    "monthly": 0,
                    "annual_discount_pct": 10,
                },
            ),
            "instruments_required": kwargs.get("instruments_required", []),
            "tools_required": kwargs.get("tools_required", []),
            "integrations": kwargs.get("integrations", []),
            "complexity": kwargs.get("complexity", "medium"),
            "deployment_time_days": kwargs.get("deployment_time_days", 5),
            "ai_agents_included": kwargs.get("ai_agents_included", 1),
            "prerequisites": kwargs.get("prerequisites", []),
            "demo_url": kwargs.get("demo_url"),
            "stripe_product_id": None,
            "stripe_price_id": None,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
        }
        self._write_solution_json(slug, data)

        # Fill architecture.md template placeholders
        arch_path = os.path.join(dest, "architecture.md")
        if os.path.isfile(arch_path):
            with open(arch_path) as f:
                content = f.read()
            content = content.replace("{{SOLUTION_NAME}}", name)
            with open(arch_path, "w") as f:
                f.write(content)

        return data

    def update_solution(self, slug: str, updates: dict) -> dict:
        """Update solution.json fields."""
        data = self._read_solution_json(slug)
        if data is None:
            raise FileNotFoundError(f"Solution '{slug}' not found")

        # Merge updates (supports nested pricing dict)
        for key, value in updates.items():
            if key == "pricing" and isinstance(value, dict) and isinstance(data.get("pricing"), dict):
                data["pricing"].update(value)
            else:
                data[key] = value

        self._write_solution_json(slug, data)
        return data

    def publish_to_stripe(self, slug: str, stripe_manager) -> dict:
        """Sync solution to Stripe as Product + Price."""
        data = self._read_solution_json(slug)
        if data is None:
            raise FileNotFoundError(f"Solution '{slug}' not found")

        pricing = data.get("pricing", {})
        monthly = pricing.get("monthly", 0)
        setup = pricing.get("one_time_setup", 0)

        # Create Stripe product
        product = stripe_manager.create_product(
            name=data["name"],
            description=data.get("tagline") or data.get("description", ""),
            metadata={
                "solution_slug": slug,
                "category": data.get("category", ""),
                "tier": data.get("tier", ""),
            },
        )

        # Create recurring price if monthly > 0
        price = None
        if monthly > 0:
            price = stripe_manager.create_price(
                stripe_product_id=product["id"],
                amount_cents=int(monthly * 100),
                currency="usd",
                recurring_interval="month",
            )

        # Create one-time setup price if setup > 0
        setup_price = None
        if setup > 0:
            setup_price = stripe_manager.create_price(
                stripe_product_id=product["id"],
                amount_cents=int(setup * 100),
                currency="usd",
            )

        # Update solution.json with Stripe IDs
        data["stripe_product_id"] = product["id"]
        if price:
            data["stripe_price_id"] = price["id"]
        if setup_price:
            data["stripe_setup_price_id"] = setup_price["id"]
        data["status"] = "published"

        self._write_solution_json(slug, data)
        return {
            "stripe_product_id": product["id"],
            "stripe_price_id": price["id"] if price else None,
            "stripe_setup_price_id": setup_price["id"] if setup_price else None,
            "status": "published",
        }

    def publish_to_provider(self, slug: str, provider_name: str, provider) -> dict:
        """Sync solution to any payment provider (Square, PayPal, etc.) using the abstract PaymentProvider interface."""
        data = self._read_solution_json(slug)
        if data is None:
            raise FileNotFoundError(f"Solution '{slug}' not found")

        pricing = data.get("pricing", {})
        monthly = float(pricing.get("monthly", 0) or 0)
        setup = float(pricing.get("one_time_setup", 0) or 0)

        product = provider.create_product(
            name=data["name"],
            description=data.get("tagline") or data.get("description", ""),
        )
        product_id = product.get("id", "")

        price_id = None
        if monthly > 0:
            price = provider.create_price(
                product_id=product_id,
                unit_amount_cents=int(monthly * 100),
                currency="usd",
                recurring_interval="month",
            )
            price_id = price.get("id")

        setup_price_id = None
        if setup > 0:
            setup_price = provider.create_price(
                product_id=product_id,
                unit_amount_cents=int(setup * 100),
                currency="usd",
                recurring_interval=None,
            )
            setup_price_id = setup_price.get("id")

        # Store provider-specific IDs in solution.json
        provider_key = provider_name.lower()
        data[f"{provider_key}_product_id"] = product_id
        if price_id:
            data[f"{provider_key}_price_id"] = price_id
        if setup_price_id:
            data[f"{provider_key}_setup_price_id"] = setup_price_id
        data["status"] = "published"

        self._write_solution_json(slug, data)
        return {
            "provider": provider_name,
            "product_id": product_id,
            "price_id": price_id,
            "setup_price_id": setup_price_id,
            "status": "published",
        }

    def get_dashboard(self) -> dict:
        """Solution catalog summary: counts by status, category, total pricing."""
        solutions = self.list_solutions()
        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}
        total_monthly = 0.0
        total_setup = 0.0

        for s in solutions:
            status = s.get("status", "draft")
            by_status[status] = by_status.get(status, 0) + 1

            cat = s.get("category", "uncategorized")
            by_category[cat] = by_category.get(cat, 0) + 1

            pricing = s.get("pricing", {})
            total_monthly += pricing.get("monthly", 0)
            total_setup += pricing.get("one_time_setup", 0)

        return {
            "total_solutions": len(solutions),
            "by_status": by_status,
            "by_category": by_category,
            "total_monthly_revenue_potential": total_monthly,
            "total_setup_revenue_potential": total_setup,
            "solutions": solutions,
        }

    def generate_proposal_data(self, slug: str) -> dict:
        """Extract data suitable for sales_generator.generate_proposal()."""
        data = self._read_solution_json(slug)
        if data is None:
            raise FileNotFoundError(f"Solution '{slug}' not found")

        pricing = data.get("pricing", {})

        return {
            "solution_name": data.get("name", ""),
            "solution_slug": slug,
            "description": data.get("description", ""),
            "tagline": data.get("tagline", ""),
            "category": data.get("category", ""),
            "tier": data.get("tier", "professional"),
            "pricing": {
                "one_time_setup": pricing.get("one_time_setup", 0),
                "monthly": pricing.get("monthly", 0),
                "annual_discount_pct": pricing.get("annual_discount_pct", 10),
            },
            "timeline_days": data.get("deployment_time_days", 5),
            "complexity": data.get("complexity", "medium"),
            "ai_agents_included": data.get("ai_agents_included", 1),
            "deliverables": {
                "instruments": data.get("instruments_required", []),
                "tools": data.get("tools_required", []),
                "integrations": data.get("integrations", []),
            },
            "prerequisites": data.get("prerequisites", []),
        }
