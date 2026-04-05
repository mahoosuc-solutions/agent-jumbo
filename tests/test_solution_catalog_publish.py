import json

import pytest

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


# ---------------------------------------------------------------------------
# Helpers shared across tests below
# ---------------------------------------------------------------------------


def _seed_solution(solutions_dir, slug="my-solution", status="draft", category="operations", monthly=100, setup=500):
    sol_dir = solutions_dir / slug
    sol_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "name": slug.replace("-", " ").title(),
        "slug": slug,
        "category": category,
        "tier": "professional",
        "tagline": "A tagline",
        "description": "A description",
        "pricing": {"monthly": monthly, "one_time_setup": setup, "annual_discount_pct": 10},
        "instruments_required": ["stripe_payments"],
        "tools_required": ["solution_catalog"],
        "integrations": ["Stripe"],
        "complexity": "medium",
        "deployment_time_days": 5,
        "ai_agents_included": 2,
        "prerequisites": [],
        "status": status,
    }
    (sol_dir / "solution.json").write_text(__import__("json").dumps(data))
    return data


# ---------------------------------------------------------------------------
# list_solutions
# ---------------------------------------------------------------------------


def test_list_solutions_returns_all(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="alpha")
    _seed_solution(solutions_dir, slug="beta")
    mgr = SolutionCatalogManager(str(solutions_dir))
    results = mgr.list_solutions()
    assert len(results) == 2


def test_list_solutions_filters_by_status(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="draft-sol", status="draft")
    _seed_solution(solutions_dir, slug="ready-sol", status="ready")
    mgr = SolutionCatalogManager(str(solutions_dir))
    ready = mgr.list_solutions(status="ready")
    assert len(ready) == 1
    assert ready[0]["slug"] == "ready-sol"


def test_list_solutions_filters_by_category(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="ops-sol", category="operations")
    _seed_solution(solutions_dir, slug="sales-sol", category="sales")
    mgr = SolutionCatalogManager(str(solutions_dir))
    ops = mgr.list_solutions(category="operations")
    assert len(ops) == 1
    assert ops[0]["slug"] == "ops-sol"


def test_list_solutions_empty_dir_returns_empty(tmp_path):
    solutions_dir = tmp_path / "solutions"
    solutions_dir.mkdir()
    mgr = SolutionCatalogManager(str(solutions_dir))
    assert mgr.list_solutions() == []


# ---------------------------------------------------------------------------
# get_solution
# ---------------------------------------------------------------------------


def test_get_solution_returns_data(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="my-sol")
    mgr = SolutionCatalogManager(str(solutions_dir))
    sol = mgr.get_solution("my-sol")
    assert sol["slug"] == "my-sol"
    assert sol["name"] == "My Sol"


def test_get_solution_raises_for_missing(tmp_path):
    solutions_dir = tmp_path / "solutions"
    solutions_dir.mkdir()
    mgr = SolutionCatalogManager(str(solutions_dir))
    with pytest.raises(FileNotFoundError):
        mgr.get_solution("nonexistent")


# ---------------------------------------------------------------------------
# create_solution
# ---------------------------------------------------------------------------


def test_create_solution_writes_json(tmp_path):
    solutions_dir = tmp_path / "solutions"
    solutions_dir.mkdir()
    mgr = SolutionCatalogManager(str(solutions_dir))
    sol = mgr.create_solution(name="New Solution", slug="new-solution", category="marketing")
    assert sol["status"] == "draft"
    assert sol["slug"] == "new-solution"
    assert (solutions_dir / "new-solution" / "solution.json").exists()


def test_create_solution_raises_if_exists(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="existing-sol")
    mgr = SolutionCatalogManager(str(solutions_dir))
    with pytest.raises(FileExistsError):
        mgr.create_solution(name="Existing", slug="existing-sol", category="operations")


# ---------------------------------------------------------------------------
# update_solution
# ---------------------------------------------------------------------------


def test_update_solution_changes_field(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="upd-sol", status="draft")
    mgr = SolutionCatalogManager(str(solutions_dir))
    updated = mgr.update_solution("upd-sol", {"status": "ready"})
    assert updated["status"] == "ready"


def test_update_solution_merges_pricing(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="pricing-sol", monthly=100, setup=500)
    mgr = SolutionCatalogManager(str(solutions_dir))
    updated = mgr.update_solution("pricing-sol", {"pricing": {"monthly": 200}})
    assert updated["pricing"]["monthly"] == 200
    assert updated["pricing"]["one_time_setup"] == 500  # unchanged


# ---------------------------------------------------------------------------
# get_dashboard
# ---------------------------------------------------------------------------


def test_dashboard_counts_by_status(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="d1", status="draft")
    _seed_solution(solutions_dir, slug="d2", status="draft")
    _seed_solution(solutions_dir, slug="r1", status="ready")
    mgr = SolutionCatalogManager(str(solutions_dir))
    dash = mgr.get_dashboard()
    assert dash["total_solutions"] == 3
    assert dash["by_status"]["draft"] == 2
    assert dash["by_status"]["ready"] == 1


def test_dashboard_totals_pricing(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="p1", monthly=100, setup=500)
    _seed_solution(solutions_dir, slug="p2", monthly=200, setup=1000)
    mgr = SolutionCatalogManager(str(solutions_dir))
    dash = mgr.get_dashboard()
    assert dash["total_monthly_revenue_potential"] == 300
    assert dash["total_setup_revenue_potential"] == 1500


# ---------------------------------------------------------------------------
# generate_proposal_data
# ---------------------------------------------------------------------------


def test_proposal_data_has_expected_keys(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="proposal-sol")
    mgr = SolutionCatalogManager(str(solutions_dir))
    data = mgr.generate_proposal_data("proposal-sol")
    for key in ("solution_name", "pricing", "deliverables", "timeline_days", "ai_agents_included"):
        assert key in data


def test_proposal_data_pricing_matches_solution(tmp_path):
    solutions_dir = tmp_path / "solutions"
    _seed_solution(solutions_dir, slug="prop-sol", monthly=750, setup=3500)
    mgr = SolutionCatalogManager(str(solutions_dir))
    data = mgr.generate_proposal_data("prop-sol")
    assert data["pricing"]["monthly"] == 750
    assert data["pricing"]["one_time_setup"] == 3500
