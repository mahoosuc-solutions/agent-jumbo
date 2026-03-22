"""Integration test: work queue execute_item → workflow engine bootstrap.

Verifies the full flow: create work item → execute_item() → workflow template
loaded from disk → workflow execution created with correct context.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration]

TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "instruments/custom/workflow_engine/templates/work_item_implementation.json",
)

SAMPLE_ITEM = {
    "external_id": "test-001",
    "source": "codebase_scan",
    "source_type": "todo",
    "title": "Fix broken import",
    "description": "The import in utils.py is wrong",
    "file_path": "python/helpers/utils.py",
    "line_number": 42,
    "project_path": "/project/alpha",
}


@pytest.fixture()
def paired_dbs():
    """Create paired temp DBs for work queue and workflow engine."""
    with tempfile.TemporaryDirectory() as tmpdir:
        wq_path = os.path.join(tmpdir, "work_queue.db")
        wf_path = os.path.join(tmpdir, "workflow_engine.db")
        yield wq_path, wf_path


def _insert_item(wq_db, item_dict):
    """Insert a work item and return its ID."""
    wq_db.upsert_item(item_dict)
    # Query by title to find the exact item (external_id isn't exposed in get_items filters)
    items, _ = wq_db.get_items(project_path=item_dict["project_path"])
    for item in items:
        if item["title"] == item_dict["title"]:
            return item["id"]
    return items[-1]["id"]


def _patch_paths(wf_path):
    """Create a patch context that redirects workflow DB and template paths."""
    import python.helpers.files

    original = python.helpers.files.get_abs_path

    def patched(path):
        if "workflow_engine/data/workflow.db" in path:
            return wf_path
        if "work_item_implementation.json" in path:
            return TEMPLATE_PATH
        return original(path)

    return patch("python.helpers.files.get_abs_path", side_effect=patched)


def test_execute_item_bootstraps_workflow_from_template(paired_dbs):
    """execute_item() loads the template and creates a workflow execution with correct context."""
    from instruments.custom.work_queue.work_queue_db import WorkQueueDatabase
    from instruments.custom.work_queue.work_queue_manager import WorkQueueManager
    from instruments.custom.workflow_engine.workflow_manager import WorkflowEngineManager

    wq_path, wf_path = paired_dbs

    wq_db = WorkQueueDatabase(wq_path)
    manager = WorkQueueManager(wq_path)
    item_id = _insert_item(wq_db, SAMPLE_ITEM)

    with _patch_paths(wf_path):
        result = manager.execute_item(item_id)

    assert result["success"] is True
    assert "execution_id" in result
    execution_id = result["execution_id"]

    # Verify workflow was created in the workflow engine DB
    wf_manager = WorkflowEngineManager(wf_path)
    workflow = wf_manager.get_workflow(name="work_item_implementation")
    assert "error" not in workflow
    assert workflow["name"] == "work_item_implementation"
    assert len(workflow["definition"]["stages"]) == 4  # plan, implement, test, review

    # Verify execution was started with correct context
    execution = wf_manager.get_execution(execution_id)
    assert execution is not None
    assert execution["status"] == "running"

    context = json.loads(execution["context"]) if isinstance(execution["context"], str) else execution["context"]
    assert context["work_item_id"] == item_id
    assert context["title"] == "Fix broken import"
    assert context["file_path"] == "python/helpers/utils.py"
    assert context["line_number"] == 42
    assert context["project_path"] == "/project/alpha"

    # Verify work queue item was updated
    item = wq_db.get_item(item_id)
    assert item["status"] == "in_progress"


def test_execute_item_reuses_existing_workflow(paired_dbs):
    """Second execute_item() reuses the workflow definition bootstrapped by the first."""
    from instruments.custom.work_queue.work_queue_db import WorkQueueDatabase
    from instruments.custom.work_queue.work_queue_manager import WorkQueueManager
    from instruments.custom.workflow_engine.workflow_manager import WorkflowEngineManager

    wq_path, wf_path = paired_dbs

    wq_db = WorkQueueDatabase(wq_path)
    manager = WorkQueueManager(wq_path)

    item1 = {**SAMPLE_ITEM, "external_id": "test-001"}
    item2 = {**SAMPLE_ITEM, "external_id": "test-002", "title": "Second item"}
    id1 = _insert_item(wq_db, item1)
    id2 = _insert_item(wq_db, item2)

    with _patch_paths(wf_path):
        r1 = manager.execute_item(id1)
        r2 = manager.execute_item(id2)

    assert r1["success"] is True
    assert r2["success"] is True
    assert r1["execution_id"] != r2["execution_id"]

    # Only one workflow definition should exist (created by first call, reused by second)
    wf_manager = WorkflowEngineManager(wf_path)
    workflows = wf_manager.list_workflows()
    work_item_workflows = [w for w in workflows if w["name"] == "work_item_implementation"]
    assert len(work_item_workflows) == 1


def test_execute_item_graceful_fallback_on_missing_template(paired_dbs):
    """If the template file is missing, execute_item still marks item in-progress."""
    from instruments.custom.work_queue.work_queue_db import WorkQueueDatabase
    from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

    wq_path, wf_path = paired_dbs

    wq_db = WorkQueueDatabase(wq_path)
    manager = WorkQueueManager(wq_path)
    item_id = _insert_item(wq_db, SAMPLE_ITEM)

    import python.helpers.files

    original = python.helpers.files.get_abs_path

    def patched(path):
        if "workflow_engine/data/workflow.db" in path:
            return wf_path
        if "work_item_implementation.json" in path:
            return "/nonexistent/path/template.json"
        return original(path)

    with patch("python.helpers.files.get_abs_path", side_effect=patched):
        result = manager.execute_item(item_id)

    assert result["success"] is True
    assert result.get("workflow") is False

    item = wq_db.get_item(item_id)
    assert item["status"] == "in_progress"
