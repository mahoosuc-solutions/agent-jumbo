from instruments.custom.portfolio_manager.portfolio_db import PortfolioDatabase


def test_portfolio_manager_db_roundtrip(tmp_path):
    data_dir = str(tmp_path)
    db = PortfolioDatabase(data_dir=data_dir)

    # Add project
    project_id = db.add_project(
        name="My CLI Tool",
        path="/projects/cli-tool",
        description="A handy CLI tool",
        language="python",
        framework="click",
        version="0.1.0",
        status="draft",
    )
    assert project_id

    project = db.get_project(project_id)
    assert project["name"] == "My CLI Tool"
    assert project["language"] == "python"
    assert project["status"] == "draft"

    # Get by path
    by_path = db.get_project_by_path("/projects/cli-tool")
    assert by_path["id"] == project_id

    # Update project
    db.update_project(project_id, status="ready", version="1.0.0")
    updated = db.get_project(project_id)
    assert updated["status"] == "ready"
    assert updated["version"] == "1.0.0"

    # List projects
    projects = db.list_projects()
    assert len(projects) == 1

    # List filtered by status
    drafts = db.list_projects(status="draft")
    assert len(drafts) == 0
    ready = db.list_projects(status="ready")
    assert len(ready) == 1

    # Metadata
    db.set_metadata(project_id, "loc", 1500)
    db.set_metadata(project_id, "has_tests", True)
    meta = db.get_metadata(project_id)
    assert meta["loc"] == 1500
    assert meta["has_tests"] is True

    # Update metadata
    db.set_metadata(project_id, "loc", 2000)
    assert db.get_metadata(project_id)["loc"] == 2000

    # Tags
    db.add_tag(project_id, "cli")
    db.add_tag(project_id, "python")
    tags = db.get_tags(project_id)
    assert "cli" in tags
    assert "python" in tags
    assert len(tags) == 2

    # Find by tag
    found = db.find_by_tag("cli")
    assert len(found) == 1
    assert found[0]["id"] == project_id

    # Create product
    product_id = db.create_product(
        project_id=project_id,
        name="CLI Tool Pro",
        tagline="The ultimate CLI tool",
        category="developer-tools",
        price=49.99,
        price_model="one-time",
    )
    assert product_id

    product = db.get_product(product_id)
    assert product["name"] == "CLI Tool Pro"
    assert product["project_name"] == "My CLI Tool"
    assert product["price"] == 49.99

    # Update product
    db.update_product(product_id, price=59.99)
    updated_prod = db.get_product(product_id)
    assert updated_prod["price"] == 59.99

    # List products
    products = db.list_products()
    assert len(products) == 1

    # Product features
    db.add_product_feature(product_id, "Autocomplete support", priority=10)
    db.add_product_feature(product_id, "Plugin system", priority=5)
    features = db.get_product_features(product_id)
    assert len(features) == 2
    assert features[0]["feature"] == "Autocomplete support"  # higher priority first

    # Sales pipeline
    lead_id = db.add_lead(
        product_id=product_id,
        customer_name="Jane Doe",
        customer_email="jane@example.com",
        value=59.99,
    )
    assert lead_id

    # Update lead stage
    db.update_lead_stage(lead_id, "closed-won", notes="Purchased via website")

    summary = db.get_pipeline_summary()
    assert "closed-won" in summary
    assert summary["closed-won"]["count"] == 1

    # Documentation
    db.update_documentation(project_id, "readme", exists=True, quality_score=80)
    docs = db.get_documentation_status(project_id)
    assert len(docs) == 1
    assert docs[0]["doc_type"] == "readme"
    assert docs[0]["exists_flag"] == 1
    assert docs[0]["quality_score"] == 80

    # Portfolio stats
    stats = db.get_portfolio_stats()
    assert stats["projects"]["total"] == 1
    assert stats["revenue"] == 59.99

    # Delete project
    db.delete_project(project_id)
    assert db.get_project(project_id) is None

    db.close()
