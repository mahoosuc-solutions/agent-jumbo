"""Tests for multi-tenant data path isolation."""

import os


class TestDbPath:
    """Tests for db_path with org scoping."""

    def test_standalone_path_no_org(self):
        from python.helpers.db_paths import db_path

        path = db_path("test.db")
        assert path.endswith("data/test.db")
        assert "/None/" not in path

    def test_org_scoped_path(self):
        from python.helpers.db_paths import db_path

        path = db_path("test.db", organization_id="org-123")
        assert "org-123/test.db" in path
        assert path.endswith("data/org-123/test.db")

    def test_org_directory_created(self, tmp_path, monkeypatch):
        from python.helpers import db_paths

        monkeypatch.setattr(db_paths, "get_db_dir", lambda: tmp_path)

        path = db_paths.db_path("chat.db", organization_id="org-abc")

        assert os.path.isdir(tmp_path / "org-abc")
        assert path == str(tmp_path / "org-abc" / "chat.db")

    def test_different_orgs_different_paths(self):
        from python.helpers.db_paths import db_path

        path_a = db_path("data.db", organization_id="org-a")
        path_b = db_path("data.db", organization_id="org-b")

        assert path_a != path_b
        assert "org-a" in path_a
        assert "org-b" in path_b

    def test_none_org_falls_back_to_root(self):
        from python.helpers.db_paths import db_path

        path = db_path("test.db", organization_id=None)
        assert "/None/" not in path
        assert path.endswith("data/test.db")
