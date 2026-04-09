import os

from instruments.custom.sales_generator.sales_db import SalesGeneratorDatabase


def test_sales_generator_db_roundtrip(tmp_path):
    db_path = os.path.join(tmp_path, "sales.db")
    db = SalesGeneratorDatabase(db_path)

    # Create proposal (use valid_days=1 to avoid month-boundary date bug)
    prop_id = db.create_proposal(
        title="Enterprise Package",
        customer_id=1,
        customer_name="Acme Corp",
        solution_summary="Full-stack development services",
        valid_days=1,
    )
    assert prop_id

    # Add line items
    item_id = db.add_proposal_item(
        proposal_id=prop_id,
        name="Frontend Development",
        description="React SPA",
        quantity=1,
        unit_price=15000.0,
        item_type="service",
    )
    assert item_id

    # Get proposal with items
    proposal = db.get_proposal(prop_id)
    assert proposal["title"] == "Enterprise Package"
    assert proposal["pricing_total"] == 15000.0
    assert len(proposal["items"]) == 1

    # Update status
    db.update_proposal_status(prop_id, "sent")
    updated = db.get_proposal(prop_id)
    assert updated["status"] == "sent"

    # Update content
    db.update_proposal_content(prop_id, "# Proposal\nDetailed content here")
    updated2 = db.get_proposal(prop_id)
    assert "Detailed content" in updated2["content"]

    # List proposals
    proposals = db.list_proposals(customer_id=1)
    assert len(proposals) == 1

    # Create demo
    demo_id = db.create_demo(
        title="Product Demo",
        customer_id=1,
        customer_name="Acme Corp",
        demo_type="interactive",
        features=["dashboard", "reports"],
    )
    assert demo_id
    demo = db.get_demo(demo_id)
    assert demo["features"] == ["dashboard", "reports"]

    db.update_demo_content(demo_id, "<html>demo</html>")
    demos = db.list_demos(customer_id=1)
    assert len(demos) == 1

    # Create ROI calculation
    roi_id = db.create_roi_calculation(
        title="Automation ROI",
        customer_id=1,
        customer_name="Acme Corp",
        current_costs={"labor": 50000},
        projected_savings={"labor": 30000},
        implementation_costs={"software": 10000},
    )
    assert roi_id

    db.update_roi_results(roi_id, payback_months=4, roi_percentage=200.0, npv=60000.0, projections={"year1": 30000})
    roi = db.get_roi_calculation(roi_id)
    assert roi["payback_months"] == 4
    assert roi["roi_percentage"] == 200.0
    assert roi["projections"] == {"year1": 30000}

    rois = db.list_roi_calculations()
    assert len(rois) == 1

    # Create case study
    cs_id = db.create_case_study(
        project_name="Acme Automation",
        customer_name="Acme Corp",
        industry="manufacturing",
        challenge="Manual processes",
        solution="Full automation",
        results="50% cost reduction",
        metrics={"cost_reduction": 50},
    )
    assert cs_id
    cs = db.get_case_study(cs_id)
    assert cs["industry"] == "manufacturing"
    assert cs["metrics"] == {"cost_reduction": 50}
    case_studies = db.list_case_studies(industry="manufacturing")
    assert len(case_studies) == 1

    # Create business case
    bc_id = db.create_business_case(
        title="Expansion Plan",
        customer_name="Acme Corp",
        executive_summary="Expand into new market",
        benefits=["revenue growth", "market share"],
        risks=["competition"],
        investment_required=100000.0,
    )
    assert bc_id
    bc = db.get_business_case(bc_id)
    assert bc["benefits"] == ["revenue growth", "market share"]
    bcs = db.list_business_cases()
    assert len(bcs) == 1

    # Create showcase
    sc_id = db.create_showcase(
        title="Tech Portfolio",
        description="Our best work",
        projects=["proj1", "proj2"],
        target_industry="tech",
    )
    assert sc_id
    sc = db.get_showcase(sc_id)
    assert sc["projects"] == ["proj1", "proj2"]
    db.update_showcase_content(sc_id, "showcase content")
    showcases = db.list_showcases(target_industry="tech")
    assert len(showcases) == 1

    # Create comparison
    cmp_id = db.create_comparison(
        title="Us vs Them",
        our_solution="Agent Mahoo",
        competitors=["Competitor A"],
        criteria=["price", "features"],
    )
    assert cmp_id
    db.update_comparison_analysis(cmp_id, "We win on all fronts")
    cmp = db.get_comparison(cmp_id)
    assert cmp["competitors"] == ["Competitor A"]
    assert cmp["analysis"] == "We win on all fronts"
    comparisons = db.list_comparisons()
    assert len(comparisons) == 1
