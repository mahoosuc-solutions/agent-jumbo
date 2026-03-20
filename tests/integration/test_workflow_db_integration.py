"""Integration tests for WorkflowEngineDatabase — no server required."""

import os
import tempfile

import pytest

pytestmark = [pytest.mark.integration]

_SIMPLE_DEF = {"stages": [{"id": "stage_1", "tasks": [{"id": "task_a"}]}]}


@pytest.fixture()
def engine_db():
    """Fresh WorkflowEngineDatabase in a temp directory per test."""
    from instruments.custom.workflow_engine.workflow_db import WorkflowEngineDatabase

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "wf.db")
        yield WorkflowEngineDatabase(db_path)


def test_workflow_db_create_workflow(engine_db):
    """save_workflow() inserts a record and returns a positive integer ID."""
    wf_id = engine_db.save_workflow(
        name="test-wf",
        definition=_SIMPLE_DEF,
        description="Integration test workflow",
    )
    assert isinstance(wf_id, int)
    assert wf_id > 0


def test_workflow_db_list_workflows(engine_db):
    """list_workflows() returns all saved workflows."""
    engine_db.save_workflow(name="alpha", definition=_SIMPLE_DEF)
    engine_db.save_workflow(name="beta", definition=_SIMPLE_DEF, version="1.0.0")

    workflows = engine_db.list_workflows()
    names = [w["name"] for w in workflows]
    assert "alpha" in names
    assert "beta" in names
    assert len(workflows) == 2


def test_workflow_db_execution_state_transitions(engine_db):
    """Start an execution, update its status, and verify the final state."""
    wf_id = engine_db.save_workflow(name="state-wf", definition=_SIMPLE_DEF)

    exec_id = engine_db.start_execution(wf_id, name="run-1", context={"env": "test"})
    assert isinstance(exec_id, int)

    # Verify initial state
    execution = engine_db.get_execution(exec_id)
    assert execution is not None
    assert execution["status"] == "running"
    assert execution["context"]["env"] == "test"

    # Transition to completed
    engine_db.update_execution(exec_id, status="completed", result="success")
    updated = engine_db.get_execution(exec_id)
    assert updated["status"] == "completed"
    assert updated["completed_at"] is not None
