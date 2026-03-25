"""E2E tests for the scheduler task management API endpoints.

Covers listing, creating, updating, deleting, and running scheduled tasks.
"""

import urllib.error

import pytest

from tests.e2e.helpers import api_post

pytestmark = [pytest.mark.e2e]


@pytest.mark.e2e
def test_scheduler_list_returns_tasks(app_server, auth_cookies):
    """POST scheduler_tasks_list with empty body returns ok and a tasks list."""
    data = api_post(app_server, auth_cookies, "scheduler_tasks_list", {})
    assert "ok" in data or "success" in data, f"Expected 'ok' or 'success' key in response: {data}"
    assert "tasks" in data, f"Expected 'tasks' key in response: {data}"
    assert isinstance(data["tasks"], list), f"Expected 'tasks' to be a list, got: {type(data['tasks'])}"


@pytest.mark.e2e
def test_scheduler_create_adhoc_task(app_server, auth_cookies):
    """POST scheduler_task_create with name/prompt/system_prompt creates an ad-hoc task."""
    create_body = {
        "name": "e2e_adhoc_test_task",
        "prompt": "Say hello",
        "system_prompt": "You are a test assistant.",
    }
    data = api_post(app_server, auth_cookies, "scheduler_task_create", create_body)
    assert "ok" in data or "success" in data, f"Expected 'ok' or 'success' in response: {data}"
    assert "task" in data, f"Expected 'task' key in response: {data}"
    task = data["task"]
    assert "uuid" in task or "id" in task, f"Expected task to have 'uuid' or 'id': {task}"

    # Cleanup: delete the created task
    task_id = task.get("uuid") or task.get("id")
    api_post(app_server, auth_cookies, "scheduler_task_delete", {"task_id": task_id})


@pytest.mark.e2e
def test_scheduler_create_scheduled_task(app_server, auth_cookies):
    """POST scheduler_task_create with a schedule dict creates a scheduled (cron) task."""
    create_body = {
        "name": "e2e_scheduled_test_task",
        "prompt": "Summarize today",
        "system_prompt": "You are a test assistant.",
        "schedule": {
            "minute": "0",
            "hour": "12",
            "day_of_month": "*",
            "month": "*",
            "day_of_week": "*",
        },
    }
    data = api_post(app_server, auth_cookies, "scheduler_task_create", create_body)
    assert "ok" in data or "success" in data, f"Expected 'ok' or 'success' in response: {data}"
    assert "task" in data, f"Expected 'task' key in response: {data}"
    task = data["task"]
    # The task type should indicate it is scheduled (not ad-hoc)
    if "type" in task:
        assert task["type"] in ("scheduled", "cron"), (
            f"Expected task type to be 'scheduled' or 'cron', got: {task['type']}"
        )

    # Cleanup
    task_id = task.get("uuid") or task.get("id")
    api_post(app_server, auth_cookies, "scheduler_task_delete", {"task_id": task_id})


@pytest.mark.e2e
def test_scheduler_update_task(app_server, auth_cookies):
    """Create a task, update its name, and verify the updated name is returned."""
    # Create
    create_body = {
        "name": "e2e_update_before",
        "prompt": "Test prompt",
        "system_prompt": "Test system prompt",
    }
    create_data = api_post(app_server, auth_cookies, "scheduler_task_create", create_body)
    task = create_data["task"]
    task_id = task.get("uuid") or task.get("id")

    # Update
    update_body = {"task_id": task_id, "name": "e2e_update_after"}
    update_data = api_post(app_server, auth_cookies, "scheduler_task_update", update_body)
    assert "ok" in update_data or "success" in update_data, (
        f"Expected 'ok' or 'success' in update response: {update_data}"
    )
    if "task" in update_data:
        assert update_data["task"].get("name") == "e2e_update_after", (
            f"Expected updated name 'e2e_update_after', got: {update_data['task'].get('name')}"
        )

    # Cleanup
    api_post(app_server, auth_cookies, "scheduler_task_delete", {"task_id": task_id})


@pytest.mark.e2e
def test_scheduler_delete_task(app_server, auth_cookies):
    """Create a task, delete it by uuid, and assert success."""
    # Create
    create_body = {
        "name": "e2e_delete_test_task",
        "prompt": "Delete me",
        "system_prompt": "Test system prompt",
    }
    create_data = api_post(app_server, auth_cookies, "scheduler_task_create", create_body)
    task = create_data["task"]
    task_id = task.get("uuid") or task.get("id")

    # Delete
    delete_data = api_post(app_server, auth_cookies, "scheduler_task_delete", {"uuid": task_id})
    assert delete_data.get("success") is True or delete_data.get("ok") is True, (
        f"Expected success=True in delete response: {delete_data}"
    )


@pytest.mark.e2e
def test_scheduler_delete_nonexistent(app_server, auth_cookies):
    """Deleting a task with a fake uuid returns an error response."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    try:
        data = api_post(app_server, auth_cookies, "scheduler_task_delete", {"task_id": fake_uuid})
        # If the server returns 200 with an error payload, check for error indicators
        assert data.get("success") is False or data.get("ok") is False or "error" in data, (
            f"Expected error response for nonexistent task, got: {data}"
        )
    except urllib.error.HTTPError as exc:
        # 4xx or 5xx is acceptable for a nonexistent resource
        assert exc.code in (400, 404, 422, 500), (
            f"Unexpected HTTP status {exc.code}: {getattr(exc, '_response_body', '')}"
        )
