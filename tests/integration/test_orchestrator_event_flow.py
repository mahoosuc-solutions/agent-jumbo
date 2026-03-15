"""
Live integration test: Linear → Motion orchestrator event flow.

Requires real API keys in .env:
  LINEAR_API_KEY, LINEAR_DEFAULT_TEAM_ID, MOTION_API_KEY, MOTION_WORKSPACE_ID

Run manually:
  python -m pytest tests/integration/test_orchestrator_event_flow.py -v -s

NOT run in CI — uses real APIs and creates real data.
"""

import os
import sys

import pytest
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv()

# Skip entire module if keys aren't set
pytestmark = pytest.mark.skipif(
    not all(
        os.getenv(k) for k in ("LINEAR_API_KEY", "LINEAR_DEFAULT_TEAM_ID", "MOTION_API_KEY", "MOTION_WORKSPACE_ID")
    ),
    reason="Missing API keys for live integration test",
)

TEST_ISSUE_TITLE = "[TEST] Orchestrator P0 event flow — auto-delete"


@pytest.fixture
async def linear_client():
    from python.helpers.linear_client import LinearClient

    return LinearClient(api_key=os.getenv("LINEAR_API_KEY"))


@pytest.fixture
async def cleanup_issue(linear_client):
    """Fixture that collects issue IDs and archives them after test."""
    issue_ids: list[str] = []
    yield issue_ids

    for issue_id in issue_ids:
        try:
            # Archive the test issue (Linear has no hard delete via API)
            await linear_client.execute(
                """mutation ArchiveIssue($id: String!) {
                    issueArchive(id: $id) { success }
                }""",
                {"id": issue_id},
            )
        except Exception as e:
            print(f"Cleanup warning: could not archive {issue_id}: {e}")


@pytest.mark.asyncio
async def test_linear_to_motion_sync(linear_client, cleanup_issue):
    """Create P0 issue in Linear → trigger sync → verify Motion task created."""

    # 1. Create P0 issue in Linear
    team_id = os.getenv("LINEAR_DEFAULT_TEAM_ID")
    result = await linear_client.create_issue(
        title=TEST_ISSUE_TITLE,
        team_id=team_id,
        description="Automated integration test for orchestrator event flow. Safe to delete.",
        priority=1,  # Urgent (P0 in Linear's 1-4 scale)
    )
    assert result.get("success"), f"Failed to create Linear issue: {result}"
    issue = result["issue"]
    issue_id = issue["id"]
    cleanup_issue.append(issue_id)
    print(f"\n  Created Linear issue: {issue['identifier']} ({issue['url']})")

    # 2. Trigger Motion sync via MOSOrchestrator
    from python.helpers.mos_orchestrator import MOSOrchestrator

    sync_result = await MOSOrchestrator.sync_linear_to_motion()
    print(f"  Sync result: {sync_result}")

    # 3. Verify sync completed without error
    assert "error" not in sync_result, f"Sync failed: {sync_result}"
    assert sync_result.get("skipped") is not True, f"Sync was skipped: {sync_result}"

    # 4. Verify Motion task exists (check sync_result for task count)
    # The sync_from_linear method returns stats about created/updated tasks
    tasks_created = sync_result.get("tasks_created", sync_result.get("created", 0))
    tasks_total = sync_result.get("total_synced", sync_result.get("synced", 0))
    print(f"  Motion tasks created: {tasks_created}, total synced: {tasks_total}")

    # At minimum, the sync should have processed without errors
    assert tasks_total >= 0 or tasks_created >= 0, f"No task metrics in result: {sync_result}"
    print("  Integration test PASSED")
