import os

from instruments.custom.ai_migration.migration_db import MigrationDatabase


def test_migration_db_roundtrip(tmp_path):
    db_path = os.path.join(tmp_path, "migration.db")
    db = MigrationDatabase(db_path)

    # Create project
    project_id = db.create_project(
        business_name="Acme Corp",
        customer_id=1,
        industry="manufacturing",
        company_size="50-200",
        goals=["reduce costs", "automate invoicing"],
    )
    assert project_id

    project = db.get_project(project_id)
    assert project["business_name"] == "Acme Corp"
    assert project["industry"] == "manufacturing"
    assert project["goals"] == ["reduce costs", "automate invoicing"]

    # Update project
    assert db.update_project(project_id, status="in_progress", assessment_score=75)
    updated = db.get_project(project_id)
    assert updated["status"] == "in_progress"
    assert updated["assessment_score"] == 75

    # List projects
    projects = db.list_projects()
    assert len(projects) == 1

    # Add process
    process_id = db.add_process(
        project_id,
        "Invoice Processing",
        department="Finance",
        priority="high",
        current_time_hours=4.0,
    )
    assert process_id

    process = db.get_process(process_id)
    assert process["name"] == "Invoice Processing"
    assert process["department"] == "Finance"

    # Update process
    assert db.update_process(process_id, automation_score=80, status="analyzed")
    updated_proc = db.get_process(process_id)
    assert updated_proc["automation_score"] == 80

    # List processes
    processes = db.list_processes(project_id)
    assert len(processes) == 1

    # Add task
    task_id = db.add_task(
        process_id,
        "Extract data from PDF",
        task_type="data_extraction",
        time_minutes=30.0,
        complexity="high",
    )
    assert task_id

    task = db.get_task(task_id)
    assert task["name"] == "Extract data from PDF"
    assert task["complexity"] == "high"

    # Update task
    assert db.update_task(task_id, automation_score=90, proposed_owner="AI")

    tasks = db.list_tasks(process_id)
    assert len(tasks) == 1

    # Add workflow
    steps = [{"step": 1, "action": "OCR scan"}, {"step": 2, "action": "Validate"}]
    workflow_id = db.add_workflow(
        process_id,
        "Automated Invoice Flow",
        steps=steps,
        human_touchpoints=1,
        ai_touchpoints=3,
    )
    assert workflow_id

    workflow = db.get_workflow(workflow_id)
    assert workflow["name"] == "Automated Invoice Flow"
    assert workflow["steps"] == steps

    workflows = db.list_workflows(process_id=process_id)
    assert len(workflows) == 1

    # Add roadmap
    phases = [{"phase": 1, "name": "Quick wins"}, {"phase": 2, "name": "Scale"}]
    roadmap_id = db.add_roadmap(
        project_id,
        "Digital Transformation Roadmap",
        phases=phases,
        total_investment=50000.0,
        roi_percentage=150.0,
    )
    assert roadmap_id

    roadmap = db.get_roadmap(roadmap_id)
    assert roadmap["name"] == "Digital Transformation Roadmap"
    assert roadmap["phases"] == phases

    roadmaps = db.list_roadmaps(project_id)
    assert len(roadmaps) == 1

    # Add ROI projection
    proj_id = db.add_roi_projection(
        project_id,
        "optimistic",
        implementation_cost=50000.0,
        labor_savings_annual=80000.0,
        confidence_level="high",
    )
    assert proj_id

    projections = db.list_roi_projections(project_id)
    assert len(projections) == 1
    assert projections[0]["scenario"] == "optimistic"

    # Add quick win
    qw_id = db.add_quick_win(
        project_id,
        "Automate email sorting",
        effort_days=2,
        estimated_savings=5000.0,
        priority_score=90,
    )
    assert qw_id

    quick_wins = db.list_quick_wins(project_id)
    assert len(quick_wins) == 1
    assert quick_wins[0]["name"] == "Automate email sorting"
