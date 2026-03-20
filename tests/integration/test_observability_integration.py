"""Integration tests for observability_estimator pure functions — no DB, no server."""

import pytest

pytestmark = [pytest.mark.integration]


def test_estimate_portfolio_empty():
    """estimate_portfolio() with no projects returns valid zero-sum structure."""
    from python.helpers.observability_estimator import estimate_portfolio

    result = estimate_portfolio({})

    assert isinstance(result, dict)
    assert result["project_count"] == 0
    assert result["projects"] == []
    assert result["totals"]["buffered_events"] == 0.0
    assert result["totals"]["commercial_total_usd"] == 0.0
    assert result["totals"]["self_hosted_total_usd"] == 0.0


def test_estimate_portfolio_with_sample_data():
    """estimate_portfolio() correctly computes costs for a realistic project."""
    from python.helpers.observability_estimator import estimate_portfolio

    payload = {
        "pricing_profile": {
            "seat_price_usd": 39,
            "included_events": 10000,
            "billing_unit": 1000,
            "unit_price_usd": 0.5,
        },
        "defaults": {
            "days_per_month": 30,
            "growth_buffer_pct": 20,
            "tool_events_per_turn": 2,
            "ops_hourly_rate_usd": 100,
        },
        "projects": [
            {
                "name": "acme-chat",
                "active_users": 100,
                "sessions_per_user_per_day": 2,
                "avg_turns_per_session": 5,
                "team_seats": 3,
                "infra_monthly_usd": 200,
                "ops_hours_per_month": 4,
            }
        ],
    }

    result = estimate_portfolio(payload)

    assert result["project_count"] == 1
    project = result["projects"][0]
    assert project["name"] == "acme-chat"

    # sessions = 100 users * 2 sessions/day * 30 days = 6000
    assert project["sessions"] == pytest.approx(6000.0)

    # turns = 6000 * 5 = 30000
    assert project["turns"] == pytest.approx(30000.0)

    # buffered_events = 30000 * 2 tool_events * 1.20 growth = 72000
    assert project["buffered_events"] == pytest.approx(72000.0)

    # commercial: 3 seats * $39 = $117 fixed; (72000 - 10000) / 1000 * $0.5 = $31 variable => $148
    assert project["commercial_total_usd"] == pytest.approx(148.0)

    # self-hosted: $200 infra + 4h * $100 = $600
    assert project["self_hosted_total_usd"] == pytest.approx(600.0)

    # Totals match the single project
    assert result["totals"]["commercial_total_usd"] == pytest.approx(148.0)
    assert result["totals"]["self_hosted_total_usd"] == pytest.approx(600.0)
