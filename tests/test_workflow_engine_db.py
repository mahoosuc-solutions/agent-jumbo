import os

from instruments.custom.workflow_engine.workflow_db import WorkflowEngineDatabase


def test_workflow_engine_db_roundtrip(tmp_path):
    db_path = os.path.join(tmp_path, "workflow.db")
    db = WorkflowEngineDatabase(db_path)

    # Save a workflow
    definition = {
        "id": "test_workflow",
        "name": "Test Workflow",
        "version": "1.0.0",
        "stages": [
            {"id": "stage_1", "name": "Design", "type": "design", "tasks": []},
            {"id": "stage_2", "name": "Build", "type": "poc", "tasks": []},
        ],
    }
    wf_id = db.save_workflow(
        name="Test Workflow",
        definition=definition,
        version="1.0.0",
        description="A test workflow",
        workflow_type="product_development",
        changed_by="test",
        change_notes="Initial creation",
    )
    assert wf_id

    # Get workflow by id
    wf = db.get_workflow(workflow_id=wf_id)
    assert wf is not None
    assert wf["name"] == "Test Workflow"
    assert wf["definition"]["stages"][0]["id"] == "stage_1"

    # Get workflow by name (active version)
    wf2 = db.get_workflow(name="Test Workflow")
    assert wf2["workflow_id"] == wf_id

    # List workflows
    workflows = db.list_workflows()
    assert len(workflows) >= 1

    # Start execution
    exec_id = db.start_execution(
        workflow_id=wf_id,
        name="test_run_1",
        context={"env": "test"},
    )
    assert exec_id

    execution = db.get_execution(exec_id)
    assert execution["name"] == "test_run_1"
    assert execution["status"] == "running"

    # Update execution
    db.update_execution(exec_id, current_stage_id="stage_1")
    updated_exec = db.get_execution(exec_id)
    assert updated_exec["current_stage_id"] == "stage_1"

    # Stage progress
    db.update_stage_progress(exec_id, stage_id="stage_1", status="in_progress")
    progress = db.get_stage_progress(exec_id, "stage_1")
    assert progress is not None
    assert progress["status"] == "in_progress"

    # Task execution
    db.update_task_execution(
        execution_id=exec_id,
        stage_id="stage_1",
        task_id="task_1",
        status="running",
        input_data={"key": "value"},
    )
    tasks = db.get_task_executions(exec_id, "stage_1")
    assert len(tasks) == 1
    assert tasks[0]["status"] == "running"

    # Complete task
    db.update_task_execution(
        execution_id=exec_id,
        stage_id="stage_1",
        task_id="task_1",
        status="completed",
        output_data={"result": "ok"},
    )
    tasks_after = db.get_task_executions(exec_id, "stage_1")
    assert tasks_after[0]["status"] == "completed"

    # Save event
    db.save_event(
        execution_id=exec_id,
        event_type="stage_complete",
        stage_id="stage_1",
        data={"duration": 120},
    )
    events = db.get_execution_events(exec_id)
    # Events include auto-logged entries from start_execution, stage/task updates, plus our manual event
    assert len(events) >= 1
    assert any(e["event_type"] == "stage_complete" for e in events)

    # List executions
    execs = db.list_executions(workflow_id=wf_id)
    assert len(execs) == 1

    # Skills
    db.save_skill(
        skill_id="python_dev",
        name="Python Development",
        category="engineering",
        description="Python programming",
    )
    skill = db.get_skill("python_dev")
    assert skill is not None
    assert skill["name"] == "Python Development"

    skills = db.list_skills(category="engineering")
    assert len(skills) == 1

    # Skill progress
    db.update_skill_progress(agent_id="agent_0", skill_id="python_dev", completions=5)
    sp = db.get_skill_progress("agent_0", "python_dev")
    assert len(sp) == 1
    assert sp[0]["completions"] == 5

    # Learning path
    db.save_learning_path(
        path_id="dev_path",
        name="Developer Path",
        target_role="developer",
        description="Learn to code",
        estimated_hours=40.0,
    )
    lp = db.get_learning_path("dev_path")
    assert lp is not None
    assert lp["name"] == "Developer Path"

    paths = db.list_learning_paths()
    assert len(paths) == 1

    # Stats
    stats = db.get_stats()
    assert stats["total_workflows"] >= 1

    # Delete workflow
    assert db.delete_workflow(wf_id) is True
    assert db.get_workflow(workflow_id=wf_id) is None
