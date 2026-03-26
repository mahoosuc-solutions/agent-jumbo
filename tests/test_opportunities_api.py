from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from python.api.opportunities_dashboard import OpportunitiesDashboard
from python.api.opportunities_update import OpportunitiesUpdate


class DummyRequest:
    def __init__(self, payload=None):
        self._payload = payload or {}
        self.is_json = True
        self.data = json.dumps(self._payload).encode("utf-8")

    def get_json(self):
        return self._payload


def _patch_abs_path(monkeypatch, tmp_path: Path):
    from python.helpers import files

    original = files.get_abs_path

    def patched(*parts: str):
        joined = "/".join(str(part).replace("\\", "/") for part in parts)
        if "instruments/custom/opportunities/data/opportunities.db" in joined:
            return str(tmp_path / "opportunities.db")
        if "instruments/custom/ideas/data/ideas.db" in joined:
            return str(tmp_path / "ideas.db")
        if "instruments/custom/workflow_engine/data/workflow.db" in joined:
            return str(tmp_path / "workflow_engine.db")
        if "instruments/custom/work_queue/data/work_queue.db" in joined:
            return str(tmp_path / "work_queue.db")
        if "instruments/custom/sales_generator/data/sales.db" in joined:
            return str(tmp_path / "sales.db")
        if "usr/projects" in joined:
            name = Path(joined).name
            return str(tmp_path / "usr" / "projects" / name)
        return original(*parts)

    monkeypatch.setattr(files, "get_abs_path", patched)


@pytest.mark.asyncio
async def test_opportunities_dashboard_lists_seeded_territories(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)
    handler = OpportunitiesDashboard(SimpleNamespace(), SimpleNamespace())
    result = await handler.process({"action": "dashboard"}, DummyRequest())
    assert result["success"] is True
    assert result["stats"]["total_territories"] >= 4
    assert set(result["lane_board"].keys()) == {"discovery", "qualification", "estimation", "solutioning"}
    assert "next_action" in result["territories"][0]


@pytest.mark.asyncio
async def test_opportunity_qualify_action_updates_lane_and_scores(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)
    dashboard = OpportunitiesDashboard(SimpleNamespace(), SimpleNamespace())
    territories = await dashboard.process({"action": "territories"}, DummyRequest())
    territory_id = territories["territories"][0]["id"]

    update = OpportunitiesUpdate(SimpleNamespace(), SimpleNamespace())
    created = await update.process(
        {
            "action": "create",
            "opportunity": {
                "territory_id": territory_id,
                "title": "County health interoperability modernization",
                "buyer_name": "County public health authority",
                "raw_requirements": "Need FHIR integration, security controls, analytics dashboards, and workflow automation.",
            },
        },
        DummyRequest(),
    )

    qualified = await update.process(
        {"action": "qualify", "opportunity_id": created["opportunity"]["id"]},
        DummyRequest(),
    )
    assert qualified["success"] is True
    assert qualified["opportunity"]["stage"] == "qualified"
    assert qualified["opportunity"]["lane"] == "estimation"
    assert qualified["opportunity"]["recommendation"] == "pursue"
    assert qualified["opportunity"]["must_have_requirements"]


@pytest.mark.asyncio
async def test_opportunity_ingest_deduplicates_and_returns_counts(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)
    dashboard = OpportunitiesDashboard(SimpleNamespace(), SimpleNamespace())
    territories = await dashboard.process({"action": "territories"}, DummyRequest())
    territory_id = territories["territories"][0]["id"]

    update = OpportunitiesUpdate(SimpleNamespace(), SimpleNamespace())
    first = await update.process(
        {
            "action": "ingest",
            "opportunities": [
                {
                    "territory_id": territory_id,
                    "title": "County analytics modernization",
                    "buyer_name": "County health office",
                    "source_type": "public_rfp",
                    "external_id": "county-001",
                    "source_url": "https://example.gov/opps/county-001",
                    "raw_requirements": "Need dashboards, workflow automation, and secure integrations.",
                }
            ],
        },
        DummyRequest(),
    )
    second = await update.process(
        {
            "action": "ingest",
            "opportunities": [
                {
                    "territory_id": territory_id,
                    "title": "County analytics modernization",
                    "buyer_name": "County health office",
                    "source_type": "public_rfp",
                    "external_id": "county-001",
                    "source_url": "https://example.gov/opps/county-001",
                    "raw_requirements": "Need FHIR dashboards, workflow automation, and secure integrations.",
                }
            ],
        },
        DummyRequest(),
    )

    assert first["success"] is True
    assert first["created"] == 1
    assert first["updated"] == 0
    assert second["created"] == 0
    assert second["updated"] == 1
    assert second["qualified"] == 1
    assert len(second["opportunities"]) == 1


@pytest.mark.asyncio
async def test_run_collectors_action_supports_inline_adapter(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)
    update = OpportunitiesUpdate(SimpleNamespace(), SimpleNamespace())
    result = await update.process(
        {
            "action": "run_collectors",
            "collectors": [
                {
                    "adapter": "inline_json",
                    "config": {
                        "opportunities": [
                            {
                                "territory_id": 1,
                                "title": "Metro public health workflow modernization",
                                "buyer_name": "Metro health authority",
                                "source_type": "public_rfp",
                                "external_id": "inline-api-1",
                                "raw_requirements": "Need secure dashboards and workflow automation.",
                            }
                        ]
                    },
                }
            ],
        },
        DummyRequest(),
    )

    assert result["success"] is True
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["runs"][0]["adapter"] == "inline_json"


@pytest.mark.asyncio
async def test_dashboard_exposes_collector_run_history(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)
    update = OpportunitiesUpdate(SimpleNamespace(), SimpleNamespace())
    await update.process(
        {
            "action": "run_collectors",
            "collectors": [
                {
                    "adapter": "inline_json",
                    "name": "dashboard-feed",
                    "config": {
                        "opportunities": [
                            {
                                "territory_id": 1,
                                "title": "City interoperability refresh",
                                "buyer_name": "City health department",
                                "source_type": "public_rfp",
                                "external_id": "history-1",
                                "raw_requirements": "Need secure FHIR dashboards.",
                            }
                        ]
                    },
                }
            ],
        },
        DummyRequest(),
    )

    dashboard = OpportunitiesDashboard(SimpleNamespace(), SimpleNamespace())
    result = await dashboard.process({"action": "dashboard"}, DummyRequest())
    assert result["success"] is True
    assert result["collector_runs"]
    assert result["collector_runs"][0]["collector_name"] == "dashboard-feed"


@pytest.mark.asyncio
async def test_dashboard_exposes_territory_bundle_and_coverage_evidence(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)
    dashboard = OpportunitiesDashboard(SimpleNamespace(), SimpleNamespace())
    result = await dashboard.process({"action": "dashboard"}, DummyRequest())
    territory = result["territories"][0]

    assert result["success"] is True
    assert territory["collector_bundle"]
    assert territory["coverage_thresholds"]["required_successful_collectors"] >= 1
    assert "coverage_evidence" in territory
    assert "required_collectors" in territory["coverage_evidence"]


@pytest.mark.asyncio
async def test_opportunity_create_estimate_approve_handoff(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)
    dashboard = OpportunitiesDashboard(SimpleNamespace(), SimpleNamespace())
    territories = await dashboard.process({"action": "territories"}, DummyRequest())
    territory_id = territories["territories"][0]["id"]

    update = OpportunitiesUpdate(SimpleNamespace(), SimpleNamespace())
    created = await update.process(
        {
            "action": "create",
            "opportunity": {
                "territory_id": territory_id,
                "title": "City data modernization",
                "buyer_name": "City health department",
                "normalized_summary": "Operator dashboards, reporting, and secure integrations.",
                "raw_requirements": "Need modern platform with dashboards and public health reporting.",
            },
        },
        DummyRequest(),
    )
    assert created["success"] is True
    opportunity_id = created["opportunity"]["id"]

    estimated = await update.process(
        {
            "action": "estimate",
            "opportunity_id": opportunity_id,
            "estimate": {
                "total_hours": 200,
                "timeline_weeks": 8,
                "estimated_cost": 42000,
                "roles": [{"role": "Architect", "hours": 100, "cost": 21000}],
                "milestones": [{"name": "Discovery"}],
                "assumptions": ["Buyer access"],
                "risks": ["Timeline compression"],
                "pricing_notes": "Milestone-based pricing",
            },
        },
        DummyRequest(),
    )
    assert estimated["success"] is True
    assert estimated["opportunity"]["stage"] == "estimated"

    approved = await update.process({"action": "approve", "opportunity_id": opportunity_id}, DummyRequest())
    assert approved["success"] is True
    assert approved["opportunity"]["approval_status"] == "approved"

    handed_off = await update.process({"action": "handoff", "opportunity_id": opportunity_id}, DummyRequest())
    assert handed_off["success"] is True
    assert handed_off["opportunity"]["stage"] == "proposal_ready"
    assert handed_off["proposal"]["proposal_id"] > 0
