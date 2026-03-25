from __future__ import annotations

from pathlib import Path

from instruments.custom.opportunities.opportunities_manager import OpportunitiesManager


def _patch_abs_path(monkeypatch, tmp_path: Path):
    from python.helpers import files

    original = files.get_abs_path

    def patched(*parts: str):
        joined = "/".join(str(part).replace("\\", "/") for part in parts)
        if "usr/projects" in joined:
            name = Path(joined).name
            return str(tmp_path / "usr" / "projects" / name)
        if "instruments/custom/ideas/data/ideas.db" in joined:
            return str(tmp_path / "ideas.db")
        if "instruments/custom/workflow_engine/data/workflow.db" in joined:
            return str(tmp_path / "workflow_engine.db")
        if "instruments/custom/work_queue/data/work_queue.db" in joined:
            return str(tmp_path / "work_queue.db")
        if "instruments/custom/sales_generator/data/sales.db" in joined:
            return str(tmp_path / "sales.db")
        return original(*parts)

    monkeypatch.setattr(files, "get_abs_path", patched)


def test_seeded_territories_exist(tmp_path):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    territories = manager.list_territories()
    assert len(territories) >= 4
    assert all(territory["zips"] for territory in territories)


def test_save_estimate_requires_core_fields(tmp_path):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    territory_id = manager.list_territories()[0]["id"]
    opportunity = manager.create_opportunity(
        {
            "territory_id": territory_id,
            "title": "County reporting modernization",
            "buyer_name": "County health office",
        }
    )
    try:
        manager.save_estimate(opportunity["id"], {"total_hours": 10})
    except ValueError as exc:
        assert "timeline_weeks is required" in str(exc)
    else:
        raise AssertionError("expected ValueError for incomplete estimate")


def test_handoff_requires_approval_and_creates_downstream_artifacts(tmp_path, monkeypatch):
    _patch_abs_path(monkeypatch, tmp_path)
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    territory = manager.list_territories()[0]
    opportunity = manager.create_opportunity(
        {
            "territory_id": territory["id"],
            "title": "Metro care coordination platform",
            "buyer_name": "Regional public health authority",
            "zip_code": territory["zips"][0]["zip_code"],
            "city": territory["zips"][0]["city"],
            "state": territory["zips"][0]["state"],
            "normalized_summary": "FHIR reporting, workflow dashboards, interoperability, and compliance-ready analytics.",
            "raw_requirements": "Need delivery team to modernize reporting, data exchange, and operator workflows.",
            "strategic_fit_score": 82,
            "estimated_contract_value": 125000,
            "confidence_score": 76,
        }
    )

    manager.save_estimate(
        opportunity["id"],
        {
            "total_hours": 260,
            "timeline_weeks": 12,
            "estimated_cost": 52000,
            "roles": [
                {"role": "Solution Architect", "hours": 120, "cost": 24000},
                {"role": "Engineer", "hours": 100, "cost": 20000},
                {"role": "QA", "hours": 40, "cost": 8000},
            ],
            "milestones": [{"name": "Architecture"}, {"name": "MVP"}, {"name": "Validation"}],
            "assumptions": ["Buyer provides subject matter access"],
            "risks": ["Procurement review delays"],
            "pricing_notes": "Fixed fee proposal",
        },
    )

    manager.approve_for_solutioning(opportunity["id"])
    result = manager.handoff_to_solutioning(opportunity["id"])

    assert result["success"] is True
    assert result["opportunity"]["stage"] == "proposal_ready"
    assert result["opportunity"]["linked_project_name"]
    assert result["workflow"]["name"].endswith("Starter Workflow")
    assert result["proposal"]["proposal_id"] > 0
    assert result["work_items_created"] == 3
