import os

from instruments.custom.diagram_architect.architect_db import DiagramArchitectDatabase


def test_diagram_architect_db_roundtrip(tmp_path):
    db_path = os.path.join(tmp_path, "architect.db")
    db = DiagramArchitectDatabase(db_path)

    # Create analysis
    analysis_id = db.create_analysis(
        project_path="/projects/my-app",
        project_name="my-app",
        analysis_type="full",
        metadata={"source": "cli"},
    )
    assert analysis_id

    analysis = db.get_analysis(analysis_id)
    assert analysis["project_name"] == "my-app"
    assert analysis["status"] == "pending"
    assert analysis["components_count"] == 0

    # List analyses
    analyses = db.list_analyses()
    assert len(analyses) == 1

    # Filter by project_path
    filtered = db.list_analyses(project_path="/projects/my-app")
    assert len(filtered) == 1
    empty = db.list_analyses(project_path="/nonexistent")
    assert len(empty) == 0

    # Update status
    db.update_analysis_status(analysis_id, "completed")
    completed = db.get_analysis(analysis_id)
    assert completed["status"] == "completed"
    assert completed["completed_at"] is not None

    # Add components
    comp1_id = db.add_component(
        analysis_id,
        name="UserService",
        component_type="service",
        file_path="src/services/user.py",
        description="Handles user operations",
        properties={"methods": ["create", "update"]},
    )
    comp2_id = db.add_component(
        analysis_id,
        name="UserDB",
        component_type="database",
        description="User data store",
    )
    assert comp1_id
    assert comp2_id

    components = db.get_components(analysis_id)
    assert len(components) == 2

    # Filter by type
    services = db.get_components(analysis_id, component_type="service")
    assert len(services) == 1
    assert services[0]["name"] == "UserService"
    assert services[0]["properties"] == {"methods": ["create", "update"]}

    # Add relationship
    rel_id = db.add_relationship(
        analysis_id,
        source_id=comp1_id,
        target_id=comp2_id,
        relationship_type="uses",
        label="queries",
    )
    assert rel_id

    relationships = db.get_relationships(analysis_id)
    assert len(relationships) == 1
    assert relationships[0]["source_name"] == "UserService"
    assert relationships[0]["target_name"] == "UserDB"
    assert relationships[0]["relationship_type"] == "uses"

    # Verify counts in analysis
    refreshed = db.get_analysis(analysis_id)
    assert refreshed["components_count"] == 2
    assert refreshed["relationships_count"] == 1

    # Add integration
    integ_id = db.add_integration(
        analysis_id,
        name="Stripe API",
        integration_type="rest_api",
        endpoint="https://api.stripe.com",
        protocol="https",
    )
    assert integ_id

    integrations = db.get_integrations(analysis_id)
    assert len(integrations) == 1
    assert integrations[0]["name"] == "Stripe API"

    # Add data flow
    flow_id = db.add_data_flow(
        analysis_id,
        name="User Registration",
        source="API Gateway",
        destination="UserService",
        data_type="json",
        flow_type="sync",
    )
    assert flow_id

    flows = db.get_data_flows(analysis_id)
    assert len(flows) == 1
    assert flows[0]["source"] == "API Gateway"

    # Save diagram
    diagram_id = db.save_diagram(
        diagram_type="class",
        title="Class Diagram",
        mermaid_code="classDiagram\n  UserService --> UserDB",
        analysis_id=analysis_id,
        metadata={"format": "mermaid"},
    )
    assert diagram_id

    diagram = db.get_diagram(diagram_id)
    assert diagram["title"] == "Class Diagram"
    assert "classDiagram" in diagram["mermaid_code"]

    diagrams = db.get_diagrams(analysis_id=analysis_id)
    assert len(diagrams) == 1

    # Verify final count
    final = db.get_analysis(analysis_id)
    assert final["diagrams_count"] == 1
