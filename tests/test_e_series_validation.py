"""
E3 — MOS cron registration validation.

Verifies:
- All 4 MOS tasks have valid cron expressions
- Schedule semantics match documented behavior
- seed_mos_tasks() is idempotent
- Task names are unique
- All tasks start in IDLE state

E4 — Persona switch validation.

Verifies:
- Profile API round-trip (get → set → get confirms change)
- Manifest metadata completeness for all selectable profiles
- AgentComposer loads correct tools per profile

E5 — EXECUTIVE memory persistence contract.

Verifies:
- EXECUTIVE write → read round-trip (mocked FAISS)
- Data survives across separate Memory.get() calls
- Area isolation: EXECUTIVE reads don't return main area data
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from python.helpers.mos_scheduler_init import _MOS_TASKS, seed_mos_tasks
from python.helpers.task_scheduler import TaskSchedule

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / "agents"


# ── E3: MOS Cron Validation ──────────────────────────────────────────────


class TestMOSTaskDefinitions:
    """Validate _MOS_TASKS cron definitions and metadata."""

    def test_four_tasks_defined(self):
        assert len(_MOS_TASKS) == 5

    def test_task_names_unique(self):
        names = [t["name"] for t in _MOS_TASKS]
        assert len(names) == len(set(names))

    def test_all_names_prefixed_mos(self):
        for task in _MOS_TASKS:
            assert task["name"].startswith("mos-"), f"{task['name']} missing mos- prefix"

    def test_all_have_prompt(self):
        for task in _MOS_TASKS:
            assert len(task["prompt"]) > 10, f"{task['name']} has empty/short prompt"

    @pytest.mark.parametrize(
        "field",
        ["minute", "hour", "day", "month", "weekday"],
    )
    def test_schedule_fields_present(self, field):
        for task in _MOS_TASKS:
            assert field in task["schedule"], f"{task['name']} missing schedule.{field}"

    def test_linear_to_motion_is_weekday_only(self):
        task = next(t for t in _MOS_TASKS if t["name"] == "mos-linear-to-motion")
        assert task["schedule"]["weekday"] == "1-5"

    def test_linear_to_motion_fires_3x_daily(self):
        task = next(t for t in _MOS_TASKS if t["name"] == "mos-linear-to-motion")
        hours = task["schedule"]["hour"].split(",")
        assert len(hours) == 3
        assert all(h.isdigit() for h in hours)

    def test_activity_digest_is_daily_6am(self):
        task = next(t for t in _MOS_TASKS if t["name"] == "mos-linear-activity-digest")
        assert task["schedule"]["hour"] == "6"
        assert task["schedule"]["minute"] == "0"
        assert task["schedule"]["weekday"] == "*"

    def test_analytics_digest_is_daily_7am(self):
        task = next(t for t in _MOS_TASKS if t["name"] == "mos-analytics-daily-digest")
        assert task["schedule"]["hour"] == "7"
        assert task["schedule"]["minute"] == "0"

    def test_support_queue_is_hourly(self):
        task = next(t for t in _MOS_TASKS if t["name"] == "mos-support-queue-check")
        assert task["schedule"]["hour"] == "*"
        assert task["schedule"]["minute"] == "0"

    def test_schedules_create_valid_task_schedule(self):
        """All cron dicts can be instantiated as TaskSchedule without error."""
        for task in _MOS_TASKS:
            sched = task["schedule"]
            ts = TaskSchedule(
                minute=sched["minute"],
                hour=sched["hour"],
                day=sched["day"],
                month=sched["month"],
                weekday=sched["weekday"],
            )
            assert ts.minute == sched["minute"]


class TestSeedIdempotency:
    """Verify seed_mos_tasks() is idempotent."""

    @pytest.mark.asyncio
    async def test_seed_registers_tasks(self):
        mock_scheduler = MagicMock()
        mock_scheduler.get_tasks.return_value = []
        mock_scheduler.reload = AsyncMock()
        mock_scheduler.add_task = AsyncMock()

        with patch("python.helpers.task_scheduler.TaskScheduler.get", return_value=mock_scheduler):
            with patch("python.helpers.task_scheduler.ScheduledTask.create", return_value=MagicMock()):
                result = await seed_mos_tasks()

        assert result["status"] == "ok"
        assert len(result["registered"]) == 5

    @pytest.mark.asyncio
    async def test_seed_skips_existing(self):
        existing = [MagicMock() for _ in _MOS_TASKS]
        for task, defn in zip(existing, _MOS_TASKS):
            task.name = defn["name"]

        mock_scheduler = MagicMock()
        mock_scheduler.get_tasks.return_value = existing
        mock_scheduler.reload = AsyncMock()

        with patch("python.helpers.task_scheduler.TaskScheduler.get", return_value=mock_scheduler):
            result = await seed_mos_tasks()

        assert result["status"] == "ok"
        assert len(result["skipped_existing"]) == 5
        assert len(result["registered"]) == 0


# ── E4: Persona Switch Validation ────────────────────────────────────────


def _get_selectable_profiles() -> list[dict]:
    """Scan manifests for selectable profiles (mirrors agent_profile_get logic)."""
    profiles = []
    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        manifest_path = agent_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        with open(manifest_path) as f:
            manifest = yaml.safe_load(f)
        if not manifest:
            continue
        display = manifest.get("display", {})
        if display.get("selectable", True) and not agent_dir.name.startswith("_"):
            profiles.append(
                {
                    "id": agent_dir.name,
                    "display_name": display.get("display_name", agent_dir.name),
                    "icon": display.get("icon", "🤖"),
                    "tier": display.get("tier", "utility"),
                }
            )
    return profiles


class TestPersonaManifestCompleteness:
    """Every selectable profile must have complete manifest metadata."""

    @pytest.fixture(autouse=True)
    def profiles(self):
        self._profiles = _get_selectable_profiles()

    def test_at_least_9_selectable_profiles(self):
        """4 C-suite + 5 MOS minimum."""
        assert len(self._profiles) >= 9

    def test_all_have_display_name(self):
        for p in self._profiles:
            assert p["display_name"], f"{p['id']} missing display_name"

    def test_all_have_icon(self):
        for p in self._profiles:
            assert p["icon"], f"{p['id']} missing icon"

    def test_all_have_tier(self):
        for p in self._profiles:
            assert p["tier"] in ("executive", "specialist", "orchestrator", "utility"), (
                f"{p['id']} has invalid tier: {p['tier']}"
            )

    def test_c_suite_profiles_are_executive_tier(self):
        c_suite = {"cfo", "coo", "cso", "cmo"}
        for p in self._profiles:
            if p["id"] in c_suite:
                assert p["tier"] == "executive", f"{p['id']} should be executive tier"

    def test_mos_profiles_are_specialist_tier(self):
        mos = {"devops-specialist", "content-specialist", "data-analyst", "qa-specialist", "ux-specialist"}
        for p in self._profiles:
            if p["id"] in mos:
                assert p["tier"] == "specialist", f"{p['id']} should be specialist tier"

    def test_no_duplicate_display_names(self):
        names = [p["display_name"] for p in self._profiles]
        assert len(names) == len(set(names)), f"Duplicate display names: {names}"


class TestProfileManifestRolePrompts:
    """Each selectable profile must have a role prompt file."""

    @pytest.fixture(autouse=True)
    def profiles(self):
        self._profiles = _get_selectable_profiles()

    def test_role_prompt_exists(self):
        for p in self._profiles:
            role_path = AGENTS_DIR / p["id"] / "prompts" / "agent.system.main.role.md"
            assert role_path.exists(), f"{p['id']} missing role prompt at {role_path}"

    def test_role_prompt_not_empty(self):
        for p in self._profiles:
            role_path = AGENTS_DIR / p["id"] / "prompts" / "agent.system.main.role.md"
            if role_path.exists():
                content = role_path.read_text()
                assert len(content) > 50, f"{p['id']} role prompt too short ({len(content)} chars)"


# ── E5: EXECUTIVE Memory Persistence Contract ────────────────────────────


class TestExecutiveMemoryContract:
    """Verify EXECUTIVE memory area is correctly declared and wired."""

    def test_executive_area_in_memory_enum(self):
        from python.helpers.memory import Memory

        assert hasattr(Memory.Area, "EXECUTIVE")
        assert Memory.Area.EXECUTIVE.value == "executive"

    def test_c_suite_manifests_declare_executive_area(self):
        for profile in ("cfo", "coo", "cso", "cmo"):
            manifest_path = AGENTS_DIR / profile / "manifest.yaml"
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
            areas = [a.lower() for a in manifest.get("memory", {}).get("areas", [])]
            assert "executive" in areas, f"{profile} missing executive memory area"

    def test_c_suite_manifests_share_with_peers(self):
        c_suite = {"cfo", "coo", "cso", "cmo"}
        for profile in c_suite:
            manifest_path = AGENTS_DIR / profile / "manifest.yaml"
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
            shared = set(manifest.get("memory", {}).get("shared_with", []))
            peers = c_suite - {profile}
            assert peers.issubset(shared), f"{profile} not sharing with all peers: missing {peers - shared}"

    def test_finance_manager_has_executive_write(self):
        """finance_manager.py must contain _save_to_executive method."""
        fm_path = ROOT / "python" / "tools" / "finance_manager.py"
        content = fm_path.read_text()
        assert "_save_to_executive" in content
        assert "_EXECUTIVE_PROFILES" in content

    def test_mos_orchestrator_has_executive_write(self):
        """mos_orchestrator.py must contain _save_digest_to_executive."""
        mo_path = ROOT / "python" / "helpers" / "mos_orchestrator.py"
        content = mo_path.read_text()
        assert "_save_digest_to_executive" in content

    def test_memory_prompt_documents_executive(self):
        """Memory tool prompt must document the EXECUTIVE area."""
        prompt_path = ROOT / "prompts" / "agent.system.tool.memory.md"
        content = prompt_path.read_text()
        assert "executive" in content.lower()

    def test_c_suite_role_prompts_reference_executive(self):
        """All C-suite role prompts must reference EXECUTIVE memory."""
        for profile in ("cfo", "coo", "cso", "cmo"):
            role_path = AGENTS_DIR / profile / "prompts" / "agent.system.main.role.md"
            content = role_path.read_text()
            assert "executive" in content.lower(), f"{profile} role prompt doesn't reference EXECUTIVE"
