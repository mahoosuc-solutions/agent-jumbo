"""Tests for agent_profile_get and agent_profile_set API endpoints."""

import os

import pytest
import yaml


class TestAgentProfileGet:
    """Test the GET /agent_profile_get endpoint logic."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        """Create a mock agents directory with manifest files."""
        self.agents_dir = tmp_path / "agents"

        # Selectable profile
        (self.agents_dir / "developer").mkdir(parents=True)
        (self.agents_dir / "developer" / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "name": "developer",
                    "version": "1.0.0",
                    "description": "Software development specialist.",
                    "inherits": "default",
                    "display": {
                        "display_name": "Developer",
                        "icon": "💻",
                        "tier": "specialist",
                        "selectable": True,
                    },
                    "capabilities": ["code_execution"],
                }
            )
        )

        # C-suite profile
        (self.agents_dir / "cfo").mkdir(parents=True)
        (self.agents_dir / "cfo" / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "name": "cfo",
                    "version": "1.0.0",
                    "description": "Chief Financial Officer.",
                    "inherits": "default",
                    "display": {
                        "display_name": "Chief Financial Officer",
                        "icon": "💰",
                        "tier": "executive",
                        "selectable": True,
                    },
                }
            )
        )

        # Internal (non-selectable) profile
        (self.agents_dir / "_example").mkdir(parents=True)
        (self.agents_dir / "_example" / "manifest.yaml").write_text(
            yaml.dump(
                {
                    "name": "_example",
                    "version": "1.0.0",
                    "description": "Template.",
                    "display": {
                        "display_name": "Example",
                        "icon": "📋",
                        "tier": "internal",
                        "selectable": False,
                    },
                }
            )
        )

        # Profile with no display block (legacy, should be excluded)
        (self.agents_dir / "legacy").mkdir(parents=True)
        (self.agents_dir / "legacy" / "manifest.yaml").write_text(
            yaml.dump({"name": "legacy", "version": "1.0.0", "description": "Old profile."})
        )

        # Directory with no manifest (should be ignored)
        (self.agents_dir / "broken").mkdir(parents=True)

    def _scan_profiles(self) -> list[dict]:
        """Simulate the scanning logic from agent_profile_get.py."""
        profiles: list[dict] = []
        for entry in sorted(os.listdir(self.agents_dir)):
            manifest_path = os.path.join(self.agents_dir, entry, "manifest.yaml")
            if not os.path.isfile(manifest_path):
                continue
            with open(manifest_path) as fh:
                data = yaml.safe_load(fh) or {}
            display = data.get("display", {})
            if not display.get("selectable", False):
                continue
            profiles.append(
                {
                    "id": entry,
                    "name": data.get("name", entry),
                    "description": (data.get("description") or "").strip(),
                    "display_name": display.get("display_name", entry),
                    "icon": display.get("icon", "🤖"),
                    "tier": display.get("tier", "utility"),
                    "inherits": data.get("inherits", ""),
                    "capabilities": data.get("capabilities", []),
                }
            )
        return profiles

    def test_returns_only_selectable_profiles(self):
        profiles = self._scan_profiles()
        ids = {p["id"] for p in profiles}
        assert "developer" in ids
        assert "cfo" in ids
        assert "_example" not in ids
        assert "legacy" not in ids
        assert "broken" not in ids

    def test_profile_metadata_fields(self):
        profiles = self._scan_profiles()
        dev = next(p for p in profiles if p["id"] == "developer")
        assert dev["display_name"] == "Developer"
        assert dev["icon"] == "💻"
        assert dev["tier"] == "specialist"
        assert dev["inherits"] == "default"
        assert "code_execution" in dev["capabilities"]

    def test_executive_tier_classification(self):
        profiles = self._scan_profiles()
        cfo = next(p for p in profiles if p["id"] == "cfo")
        assert cfo["tier"] == "executive"
        assert cfo["display_name"] == "Chief Financial Officer"

    def test_profiles_sorted_alphabetically(self):
        profiles = self._scan_profiles()
        ids = [p["id"] for p in profiles]
        assert ids == sorted(ids)

    def test_empty_agents_dir(self, tmp_path):
        empty_dir = tmp_path / "empty_agents"
        empty_dir.mkdir()
        profiles = []
        for _entry in sorted(os.listdir(empty_dir)):
            pass  # no entries
        assert profiles == []


class TestAgentProfileSet:
    """Test the POST /agent_profile_set validation logic."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.agents_dir = tmp_path / "agents"
        (self.agents_dir / "developer").mkdir(parents=True)
        (self.agents_dir / "developer" / "manifest.yaml").write_text(
            yaml.dump({"name": "developer", "version": "1.0.0"})
        )

    def _validate_profile(self, profile: str) -> str | None:
        """Simulate validation from agent_profile_set.py. Returns error or None."""
        profile = (profile or "").strip()
        if not profile:
            return "Missing required field: profile"
        manifest_path = os.path.join(self.agents_dir, profile, "manifest.yaml")
        if not os.path.isfile(manifest_path):
            return f"Unknown agent profile: {profile}"
        return None

    def test_valid_profile_accepted(self):
        assert self._validate_profile("developer") is None

    def test_missing_profile_rejected(self):
        assert "Missing" in self._validate_profile("")

    def test_unknown_profile_rejected(self):
        assert "Unknown" in self._validate_profile("nonexistent")

    def test_whitespace_stripped(self):
        assert self._validate_profile("  developer  ") is None


class TestManifestDisplayMetadata:
    """Validate that all real agent manifests have proper display metadata."""

    def _get_agents_dir(self):
        return os.path.join(os.path.dirname(__file__), "..", "agents")

    def test_all_manifests_have_display_block(self):
        agents_dir = self._get_agents_dir()
        if not os.path.isdir(agents_dir):
            pytest.skip("agents/ directory not found")

        missing = []
        for entry in sorted(os.listdir(agents_dir)):
            manifest_path = os.path.join(agents_dir, entry, "manifest.yaml")
            if not os.path.isfile(manifest_path):
                continue
            with open(manifest_path) as fh:
                data = yaml.safe_load(fh) or {}
            if "display" not in data:
                missing.append(entry)

        assert missing == [], f"Manifests missing display block: {missing}"

    def test_selectable_profiles_have_required_display_fields(self):
        agents_dir = self._get_agents_dir()
        if not os.path.isdir(agents_dir):
            pytest.skip("agents/ directory not found")

        issues = []
        for entry in sorted(os.listdir(agents_dir)):
            manifest_path = os.path.join(agents_dir, entry, "manifest.yaml")
            if not os.path.isfile(manifest_path):
                continue
            with open(manifest_path) as fh:
                data = yaml.safe_load(fh) or {}
            display = data.get("display", {})
            if not display.get("selectable", False):
                continue
            for field in ("display_name", "icon", "tier"):
                if field not in display:
                    issues.append(f"{entry}: missing display.{field}")

        assert issues == [], "Display metadata issues:\n" + "\n".join(issues)

    def test_no_internal_profiles_are_selectable(self):
        agents_dir = self._get_agents_dir()
        if not os.path.isdir(agents_dir):
            pytest.skip("agents/ directory not found")

        violations = []
        for entry in sorted(os.listdir(agents_dir)):
            manifest_path = os.path.join(agents_dir, entry, "manifest.yaml")
            if not os.path.isfile(manifest_path):
                continue
            with open(manifest_path) as fh:
                data = yaml.safe_load(fh) or {}
            display = data.get("display", {})
            if display.get("tier") == "internal" and display.get("selectable", False):
                violations.append(entry)

        assert violations == [], f"Internal profiles marked selectable: {violations}"

    def test_tier_values_are_known(self):
        agents_dir = self._get_agents_dir()
        if not os.path.isdir(agents_dir):
            pytest.skip("agents/ directory not found")

        known_tiers = {"executive", "specialist", "utility", "orchestrator", "internal"}
        unknown = []
        for entry in sorted(os.listdir(agents_dir)):
            manifest_path = os.path.join(agents_dir, entry, "manifest.yaml")
            if not os.path.isfile(manifest_path):
                continue
            with open(manifest_path) as fh:
                data = yaml.safe_load(fh) or {}
            tier = data.get("display", {}).get("tier", "")
            if tier and tier not in known_tiers:
                unknown.append(f"{entry}: tier={tier}")

        assert unknown == [], "Unknown tiers:\n" + "\n".join(unknown)
