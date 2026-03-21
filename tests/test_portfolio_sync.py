"""Tests for Core Projects -> Portfolio Manager sync."""

import json
from unittest.mock import MagicMock

import pytest

from python.helpers.portfolio_sync import sync_core_projects_to_portfolio


@pytest.fixture
def mock_projects_dir(tmp_path):
    """Create a fake usr/projects/ structure."""
    projects_dir = tmp_path / "usr" / "projects"
    projects_dir.mkdir(parents=True)

    # Project 1: has metadata
    p1 = projects_dir / "alpha_project"
    p1.mkdir()
    meta1 = p1 / ".a0proj"
    meta1.mkdir()
    (meta1 / "project.json").write_text(
        json.dumps(
            {
                "title": "Alpha Project",
                "description": "First test project",
                "color": "#ff0000",
            }
        )
    )

    # Project 2: has metadata
    p2 = projects_dir / "beta_project"
    p2.mkdir()
    meta2 = p2 / ".a0proj"
    meta2.mkdir()
    (meta2 / "project.json").write_text(
        json.dumps(
            {
                "title": "Beta Project",
                "description": "Second test project",
                "color": "#00ff00",
            }
        )
    )

    # Project 3: no metadata (should still sync with name as title)
    p3 = projects_dir / "gamma_project"
    p3.mkdir()

    return projects_dir


class TestSyncCoreProjectsToPortfolio:
    def test_syncs_new_projects(self, mock_projects_dir):
        """Projects not in portfolio DB should be added."""
        mock_db = MagicMock()
        mock_db.get_project_by_path.return_value = None  # not in DB yet
        mock_db.add_project.return_value = 1

        result = sync_core_projects_to_portfolio(
            projects_dir=str(mock_projects_dir),
            db=mock_db,
        )

        assert result["added"] == 3
        assert result["updated"] == 0
        assert mock_db.add_project.call_count == 3

    def test_updates_existing_projects(self, mock_projects_dir):
        """Projects already in portfolio DB should be updated."""
        mock_db = MagicMock()
        mock_db.get_project_by_path.return_value = {"id": 42, "name": "old_name"}
        mock_db.update_project.return_value = 1

        result = sync_core_projects_to_portfolio(
            projects_dir=str(mock_projects_dir),
            db=mock_db,
        )

        assert result["added"] == 0
        assert result["updated"] == 3
        assert mock_db.update_project.call_count == 3

    def test_reads_project_metadata(self, mock_projects_dir):
        """Should read title and description from project.json."""
        mock_db = MagicMock()
        mock_db.get_project_by_path.return_value = None
        mock_db.add_project.return_value = 1

        sync_core_projects_to_portfolio(
            projects_dir=str(mock_projects_dir),
            db=mock_db,
        )

        # Find the call for alpha_project (called with kwargs)
        calls = mock_db.add_project.call_args_list
        alpha_call = next(c for c in calls if c[1].get("name") == "Alpha Project")
        assert alpha_call[1]["description"] == "First test project"

    def test_project_without_metadata_uses_dirname(self, mock_projects_dir):
        """Projects without .a0proj/project.json should use dir name as title."""
        mock_db = MagicMock()
        mock_db.get_project_by_path.return_value = None
        mock_db.add_project.return_value = 1

        sync_core_projects_to_portfolio(
            projects_dir=str(mock_projects_dir),
            db=mock_db,
        )

        call_names = [c[1]["name"] for c in mock_db.add_project.call_args_list]
        assert "gamma_project" in call_names

    def test_skips_non_directories(self, mock_projects_dir):
        """Files in the projects dir should be ignored."""
        (mock_projects_dir / "random_file.txt").write_text("not a project")

        mock_db = MagicMock()
        mock_db.get_project_by_path.return_value = None
        mock_db.add_project.return_value = 1

        result = sync_core_projects_to_portfolio(
            projects_dir=str(mock_projects_dir),
            db=mock_db,
        )

        # Should still only add 3 projects (dirs), not the file
        assert result["added"] == 3

    def test_returns_summary(self, mock_projects_dir):
        """Should return a summary dict with counts."""
        mock_db = MagicMock()
        mock_db.get_project_by_path.return_value = None
        mock_db.add_project.return_value = 1

        result = sync_core_projects_to_portfolio(
            projects_dir=str(mock_projects_dir),
            db=mock_db,
        )

        assert "added" in result
        assert "updated" in result
        assert "total" in result
        assert result["total"] == 3
