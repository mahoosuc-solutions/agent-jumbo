import json

from instruments.custom.solution_catalog.catalog_manager import SolutionCatalogManager


class _FakeStripeManager:
    def __init__(self):
        self.created_products = []
        self.created_prices = []

    def create_product(self, name, description, metadata=None, mock=False):
        self.created_products.append(
            {
                "name": name,
                "description": description,
                "metadata": metadata or {},
                "mock": mock,
            }
        )
        return {"id": "prod_test_123"}

    def create_price(self, stripe_product_id, amount_cents, currency="usd", recurring_interval=None, mock=False):
        self.created_prices.append(
            {
                "stripe_product_id": stripe_product_id,
                "amount_cents": amount_cents,
                "currency": currency,
                "recurring_interval": recurring_interval,
                "mock": mock,
            }
        )
        suffix = "monthly" if recurring_interval else "setup"
        return {"id": f"price_{suffix}_123"}


def test_publish_to_stripe_writes_monthly_and_setup_ids(tmp_path):
    solutions_dir = tmp_path / "solutions"
    solution_dir = solutions_dir / "demo-solution"
    solution_dir.mkdir(parents=True)
    solution_path = solution_dir / "solution.json"
    solution_path.write_text(
        json.dumps(
            {
                "name": "Demo Solution",
                "slug": "demo-solution",
                "category": "operations",
                "tier": "professional",
                "tagline": "Demo package",
                "description": "Demo description",
                "pricing": {
                    "monthly": 99,
                    "one_time_setup": 499,
                },
                "status": "draft",
            }
        )
    )

    manager = SolutionCatalogManager(str(solutions_dir))
    stripe = _FakeStripeManager()

    result = manager.publish_to_stripe("demo-solution", stripe)
    updated = json.loads(solution_path.read_text())

    assert result["stripe_product_id"] == "prod_test_123"
    assert result["stripe_price_id"] == "price_monthly_123"
    assert result["stripe_setup_price_id"] == "price_setup_123"
    assert updated["stripe_product_id"] == "prod_test_123"
    assert updated["stripe_price_id"] == "price_monthly_123"
    assert updated["stripe_setup_price_id"] == "price_setup_123"
    assert updated["status"] == "published"
    assert stripe.created_prices[0]["recurring_interval"] == "month"
    assert stripe.created_prices[1]["recurring_interval"] is None
