"""Tests for EXECUTIVE memory write wiring in finance_manager and mos_orchestrator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _noop_emit(*args, **kwargs):
    """No-op replacement for emit_event to avoid hitting life_os DB."""
    pass


class TestFinanceManagerExecutiveWrite:
    """Verify finance_manager saves to EXECUTIVE memory for C-suite profiles."""

    def _make_tool(self, profile: str, action: str, extra_args: dict | None = None):
        """Build a minimal FinanceManagerTool mock with the given profile."""
        from python.tools.finance_manager import FinanceManagerTool

        agent = MagicMock()
        agent.config = MagicMock()
        agent.config.profile = profile

        args = {"action": action, **(extra_args or {})}

        # Bypass __init__ to avoid hitting real FinanceManager / sqlite DB
        tool = object.__new__(FinanceManagerTool)
        tool.agent = agent
        tool.args = args
        tool.name = "finance_manager"
        tool.method = None
        tool.message = ""
        tool.loop_data = None

        # Mock the FinanceManager backend
        tool.manager = MagicMock()
        tool.manager.generate_report.return_value = {"total_amount": 5000, "period": "2025-04"}
        tool.manager.roi_snapshot.return_value = {"roi": 2.5, "period": "2025-04"}
        tool.manager.export_business_xray_data.return_value = {"revenue": 12000, "growth": 0.08}

        return tool

    @pytest.mark.asyncio
    @patch("python.tools.finance_manager.emit_event", new=_noop_emit)
    async def test_generate_report_writes_executive_for_cfo(self):
        tool = self._make_tool("cfo", "generate_report", {"period": "2025-04"})

        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-123")

        with patch("python.tools.finance_manager.Memory") as MockMemory:
            MockMemory.get = AsyncMock(return_value=mock_db)
            await tool.execute()

        mock_db.insert_text.assert_called_once()
        call_args = mock_db.insert_text.call_args
        text = call_args[0][0]
        metadata = call_args[0][1]
        assert "CFO Financial Update" in text
        assert metadata["area"] == "executive"
        assert metadata["source"] == "finance_manager"
        assert metadata["action"] == "generate_report"

    @pytest.mark.asyncio
    @patch("python.tools.finance_manager.emit_event", new=_noop_emit)
    async def test_roi_snapshot_writes_executive_for_cfo(self):
        tool = self._make_tool("cfo", "roi_snapshot", {"period": "2025-04"})

        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-456")

        with patch("python.tools.finance_manager.Memory") as MockMemory:
            MockMemory.get = AsyncMock(return_value=mock_db)
            await tool.execute()

        mock_db.insert_text.assert_called_once()
        metadata = mock_db.insert_text.call_args[0][1]
        assert metadata["area"] == "executive"
        assert metadata["action"] == "roi_snapshot"

    @pytest.mark.asyncio
    @patch("python.tools.finance_manager.emit_event", new=_noop_emit)
    async def test_export_xray_writes_executive_for_cfo(self):
        tool = self._make_tool("cfo", "export_business_xray", {"period": "2025-04"})

        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-789")

        with patch("python.tools.finance_manager.Memory") as MockMemory:
            MockMemory.get = AsyncMock(return_value=mock_db)
            await tool.execute()

        mock_db.insert_text.assert_called_once()
        metadata = mock_db.insert_text.call_args[0][1]
        assert metadata["area"] == "executive"
        assert metadata["action"] == "export_business_xray"

    @pytest.mark.asyncio
    @patch("python.tools.finance_manager.emit_event", new=_noop_emit)
    async def test_skips_executive_write_for_non_csuite(self):
        tool = self._make_tool("developer", "generate_report", {"period": "2025-04"})

        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-000")

        with patch("python.tools.finance_manager.Memory") as MockMemory:
            MockMemory.get = AsyncMock(return_value=mock_db)
            await tool.execute()

        mock_db.insert_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("python.tools.finance_manager.emit_event", new=_noop_emit)
    async def test_skips_executive_write_for_default_profile(self):
        tool = self._make_tool("agent-mahoo", "generate_report", {"period": "2025-04"})

        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-000")

        with patch("python.tools.finance_manager.Memory") as MockMemory:
            MockMemory.get = AsyncMock(return_value=mock_db)
            await tool.execute()

        mock_db.insert_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("python.tools.finance_manager.emit_event", new=_noop_emit)
    async def test_executive_write_includes_result_keys(self):
        tool = self._make_tool("coo", "generate_report", {"period": "2025-04"})

        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-abc")

        with patch("python.tools.finance_manager.Memory") as MockMemory:
            MockMemory.get = AsyncMock(return_value=mock_db)
            await tool.execute()

        text = mock_db.insert_text.call_args[0][0]
        assert "total_amount" in text
        assert "5000" in text

    @pytest.mark.asyncio
    @patch("python.tools.finance_manager.emit_event", new=_noop_emit)
    async def test_executive_write_failure_does_not_crash_tool(self):
        """Memory write failure should be swallowed — tool still returns."""
        tool = self._make_tool("cfo", "generate_report", {"period": "2025-04"})

        with patch("python.tools.finance_manager.Memory") as MockMemory:
            MockMemory.get = AsyncMock(side_effect=RuntimeError("Memory unavailable"))
            response = await tool.execute()

        assert response is not None
        assert "5000" in response.message

    @pytest.mark.asyncio
    @patch("python.tools.finance_manager.emit_event", new=_noop_emit)
    async def test_estimate_tax_does_not_write_executive(self):
        """estimate_tax is not wired for EXECUTIVE writes."""
        tool = self._make_tool("cfo", "estimate_tax", {"period": "2025-04"})
        tool.manager.estimate_tax.return_value = {"estimated_tax": 1200}

        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-000")

        with patch("python.tools.finance_manager.Memory") as MockMemory:
            MockMemory.get = AsyncMock(return_value=mock_db)
            await tool.execute()

        mock_db.insert_text.assert_not_called()


class TestMOSOrchestratorExecutiveWrite:
    """Verify MOS orchestrator saves digests to EXECUTIVE memory."""

    @pytest.mark.asyncio
    async def test_generate_analytics_digest_writes_executive(self):
        from python.helpers.mos_orchestrator import _save_digest_to_executive

        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-digest-1")

        with patch("python.helpers.memory.Memory.get_by_subdir", new=AsyncMock(return_value=mock_db)):
            await _save_digest_to_executive("generate_analytics_digest", {"type": "test", "period": "24h"})

        mock_db.insert_text.assert_called_once()
        text = mock_db.insert_text.call_args[0][0]
        metadata = mock_db.insert_text.call_args[0][1]
        assert "MOS Digest" in text
        assert "generate_analytics_digest" in text
        assert metadata["area"] == "executive"
        assert metadata["source"] == "generate_analytics_digest"

    @pytest.mark.asyncio
    async def test_executive_write_uses_default_subdir(self):
        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-digest-2")
        mock_get = AsyncMock(return_value=mock_db)

        from python.helpers.mos_orchestrator import _save_digest_to_executive

        with patch("python.helpers.memory.Memory.get_by_subdir", new=mock_get):
            await _save_digest_to_executive("test_source", {"data": True})

        mock_get.assert_called_once_with("default")

    @pytest.mark.asyncio
    async def test_executive_write_failure_does_not_raise(self):
        from python.helpers.mos_orchestrator import _save_digest_to_executive

        with patch(
            "python.helpers.memory.Memory.get_by_subdir", new=AsyncMock(side_effect=RuntimeError("FAISS unavailable"))
        ):
            # Should not raise
            await _save_digest_to_executive("test_source", {"data": True})

    @pytest.mark.asyncio
    async def test_digest_text_contains_json(self):
        mock_db = AsyncMock()
        mock_db.insert_text = AsyncMock(return_value="mem-digest-3")

        from python.helpers.mos_orchestrator import _save_digest_to_executive

        digest = {"work_queue": {"total": 42}, "linear_activity": {"issues_updated": 5}}
        with patch("python.helpers.memory.Memory.get_by_subdir", new=AsyncMock(return_value=mock_db)):
            await _save_digest_to_executive("generate_analytics_digest", digest)

        text = mock_db.insert_text.call_args[0][0]
        assert "42" in text
        assert "issues_updated" in text

        text = mock_db.insert_text.call_args[0][0]
        assert "42" in text
        assert "issues_updated" in text


class TestExecutiveMemoryArea:
    """Validate the EXECUTIVE area exists in the Memory.Area enum."""

    def test_executive_area_exists(self):
        from python.helpers.memory import Memory

        assert hasattr(Memory.Area, "EXECUTIVE")
        assert Memory.Area.EXECUTIVE.value == "executive"

    def test_all_csuite_manifests_declare_executive(self):
        """All C-suite manifests should list 'executive' in memory.areas."""
        import os

        import yaml

        agents_dir = os.path.join(os.path.dirname(__file__), "..", "agents")
        csuite = ["cfo", "cmo", "coo", "cso"]
        missing = []

        for profile in csuite:
            manifest_path = os.path.join(agents_dir, profile, "manifest.yaml")
            if not os.path.isfile(manifest_path):
                missing.append(f"{profile}: no manifest.yaml")
                continue
            with open(manifest_path) as fh:
                data = yaml.safe_load(fh) or {}
            areas = data.get("memory", {}).get("areas", [])
            if "executive" not in [a.lower() for a in areas]:
                missing.append(f"{profile}: executive not in memory.areas")

        assert missing == [], "Missing EXECUTIVE declarations:\n" + "\n".join(missing)
