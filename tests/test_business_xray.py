import os

from instruments.custom.business_xray.comprehensive_xray import BusinessXRay


def test_business_xray_scoring(tmp_path):
    """Test BusinessXRay scoring and report methods (no external deps, no user input)."""
    output_dir = os.path.join(tmp_path, "xray_output")
    xray = BusinessXRay("Test Biz", output_dir)

    # Verify initialization
    assert xray.business_name == "Test Biz"
    assert xray.output_dir.exists()
    assert xray.report["business_name"] == "Test Biz"

    # Test health score calculation
    high_health_metrics = {
        "revenue": {"current_monthly": 50000, "growth_rate": 15, "target_revenue": 100000},
        "profitability": {"profit_margin": 35, "operating_expenses": 30000, "burn_rate": 20000},
        "customers": {"total_customers": 100, "new_this_month": 10, "churn_rate": 3, "cac": 100, "ltv": 500},
        "team": {"team_size": 5, "productivity_score": 8},
    }
    score = xray._calculate_health_score(high_health_metrics)
    assert score == 100  # high growth + high margin + high LTV/CAC + low churn

    low_health_metrics = {
        "revenue": {"current_monthly": 1000, "growth_rate": -5, "target_revenue": 10000},
        "profitability": {"profit_margin": -10, "operating_expenses": 2000, "burn_rate": -1000},
        "customers": {"total_customers": 5, "new_this_month": 0, "churn_rate": 20, "cac": 500, "ltv": 100},
        "team": {"team_size": 1, "productivity_score": 3},
    }
    low_score = xray._calculate_health_score(low_health_metrics)
    assert low_score == 0

    # Test balance score calculation
    good_balance = {
        "work": {"hours_per_week": 40, "ideal_hours": 40, "stress_level": 2},
        "health": {"exercise_hours_week": 5, "sleep_hours_night": 8, "health_satisfaction": 9},
        "relationships": {"family_time_hours_week": 20, "social_time_hours_week": 8, "relationship_satisfaction": 9},
        "personal": {"hobby_time_hours_week": 5, "learning_time_hours_week": 3, "life_satisfaction": 9},
    }
    balance = xray._calculate_balance_score(good_balance)
    assert balance == 100

    # Test effort estimation
    assert "Low" in xray._estimate_effort("Invoice generation")
    assert "Medium" in xray._estimate_effort("Email responses")
    assert "High" in xray._estimate_effort("Customer onboarding")

    # Test priority calculation
    priority = xray._calculate_priority(5000.0, 90.0)
    assert priority == 5.0 * 0.9

    # Test balance recommendations
    unbalanced = {
        "work": {"hours_per_week": 70, "ideal_hours": 40, "stress_level": 9},
        "health": {"exercise_hours_week": 1, "sleep_hours_night": 5, "health_satisfaction": 3},
        "relationships": {"family_time_hours_week": 5, "social_time_hours_week": 1, "relationship_satisfaction": 4},
        "personal": {"hobby_time_hours_week": 1, "learning_time_hours_week": 0, "life_satisfaction": 3},
    }
    recs = xray._generate_balance_recommendations(unbalanced)
    assert len(recs) >= 4  # Should flag work hours, exercise, sleep, stress, family, hobbies

    # Test executive summary generation (with pre-populated report)
    xray.report["modules"]["business_health"] = high_health_metrics
    xray.report["modules"]["business_health"]["overall_health_score"] = score
    summary = xray.generate_executive_summary()
    assert "Test Biz" in summary
    assert "Health Score" in summary
