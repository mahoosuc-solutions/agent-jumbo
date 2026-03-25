from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

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


def test_qualify_scores_opportunity_and_extracts_requirements(tmp_path):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    territory = manager.list_territories()[0]
    opportunity = manager.create_opportunity(
        {
            "territory_id": territory["id"],
            "title": "Public health FHIR reporting platform",
            "buyer_name": "City public health department",
            "raw_requirements": (
                "Need secure FHIR interoperability, analytics dashboards, reporting, workflow automation, "
                "and API integrations for clinical and public health teams."
            ),
        }
    )

    qualified = manager.qualify_opportunity(opportunity["id"])

    assert qualified["stage"] == "qualified"
    assert qualified["lane"] == "estimation"
    assert qualified["recommendation"] == "pursue"
    assert qualified["strategic_fit_score"] >= 70
    assert qualified["confidence_score"] > 60
    assert "FHIR interoperability" in qualified["must_have_requirements"]
    assert "Security and compliance" in qualified["must_have_requirements"]


def test_import_opportunities_deduplicates_by_source_identity(tmp_path):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    territory = manager.list_territories()[0]

    first = manager.import_opportunities(
        [
            {
                "territory_id": territory["id"],
                "title": "State immunization registry modernization",
                "buyer_name": "State public health agency",
                "source_type": "public_rfp",
                "external_id": "rfp-123",
                "source_url": "https://example.gov/rfp/123",
                "raw_requirements": "Need secure integrations, analytics dashboards, and workflow automation.",
            }
        ]
    )
    second = manager.import_opportunities(
        [
            {
                "territory_id": territory["id"],
                "title": "State immunization registry modernization",
                "buyer_name": "State public health agency",
                "source_type": "public_rfp",
                "external_id": "rfp-123",
                "source_url": "https://example.gov/rfp/123",
                "raw_requirements": "Updated requirements with FHIR interoperability and compliance reporting.",
            }
        ]
    )

    assert first["created"] == 1
    assert first["updated"] == 0
    assert second["created"] == 0
    assert second["updated"] == 1

    opportunities = manager.list_opportunities(territory_id=territory["id"])
    assert len(opportunities) == 1
    assert "FHIR interoperability" in opportunities[0]["must_have_requirements"]


def test_run_collectors_supports_inline_and_file_adapters(tmp_path):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    json_feed = tmp_path / "feed.json"
    json_feed.write_text(
        """
        [
          {
            "territory_id": 1,
            "title": "Municipal public health dashboards",
            "buyer_name": "City public health office",
            "source_type": "public_rfp",
            "external_id": "city-collector-1",
            "raw_requirements": "Need dashboards, FHIR integration, and secure workflows."
          }
        ]
        """.strip(),
        encoding="utf-8",
    )

    result = manager.run_collectors(
        [
            {
                "adapter": "inline_json",
                "config": {
                    "opportunities": [
                        {
                            "territory_id": 1,
                            "title": "Regional interoperability platform",
                            "buyer_name": "Regional health collaborative",
                            "source_type": "public_rfp",
                            "external_id": "inline-1",
                            "raw_requirements": "Need secure FHIR interoperability and workflow automation.",
                        }
                    ]
                },
            },
            {
                "adapter": "json_file",
                "config": {"path": str(json_feed)},
            },
        ]
    )

    assert result["created"] == 2
    assert result["updated"] == 0
    assert result["qualified"] == 2
    assert {run["adapter"] for run in result["runs"]} == {"inline_json", "json_file"}


def test_run_collectors_supports_csv_adapter_and_records_run_report(tmp_path):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    csv_feed = tmp_path / "feed.csv"
    csv_feed.write_text(
        "\n".join(
            [
                "territory_id,title,buyer_name,source_type,external_id,raw_requirements",
                '1,"State quality reporting platform","State health agency","public_rfp","csv-1","Need analytics dashboards and secure integrations."',
            ]
        ),
        encoding="utf-8",
    )

    result = manager.run_collectors(
        [
            {
                "adapter": "csv_file",
                "name": "state-csv-feed",
                "config": {"path": str(csv_feed)},
            }
        ]
    )

    assert result["created"] == 1
    assert result["errors"] == []
    runs = manager.db.list_collector_runs(limit=5)
    assert runs[0]["adapter"] == "csv_file"
    assert runs[0]["collector_name"] == "state-csv-feed"
    assert runs[0]["status"] == "ok"


def test_run_collectors_records_errors_without_aborting_all_runs(tmp_path):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    result = manager.run_collectors(
        [
            {
                "adapter": "json_file",
                "name": "missing-feed",
                "config": {"path": str(tmp_path / "missing.json")},
            }
        ]
    )

    assert result["created"] == 0
    assert len(result["errors"]) == 1
    assert result["runs"][0]["status"] == "error"
    runs = manager.db.list_collector_runs(limit=5)
    assert runs[0]["status"] == "error"


def test_territory_coverage_requires_bundle_evidence_and_backlog_clear(tmp_path):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    territory = manager.list_territories()[0]
    territory_id = territory["id"]

    manager.create_opportunity(
        {
            "territory_id": territory_id,
            "title": "Boston discovered backlog item",
            "buyer_name": "Boston public health office",
            "source_type": "manual",
            "raw_requirements": "Need secure FHIR dashboards.",
        }
    )

    territories = manager.list_territories()
    boston = next(item for item in territories if item["id"] == territory_id)
    assert boston["coverage_complete"] is False
    assert boston["coverage_evidence"]["bundle_ready"] is False

    for collector_name in boston["coverage_evidence"]["required_collectors"]:
        run_id = manager.db.start_collector_run("json_file", collector_name)
        manager.db.finish_collector_run(
            run_id,
            status="ok",
            items_received=1,
            created_count=1,
            updated_count=0,
            qualified_count=1,
        )

    opportunities = manager.list_opportunities(territory_id=territory_id)
    manager.update_opportunity(opportunities[0]["id"], {"stage": "qualified", "lane": "estimation"})

    refreshed = next(item for item in manager.list_territories() if item["id"] == territory_id)
    assert refreshed["coverage_evidence"]["bundle_ready"] is True
    assert refreshed["coverage_evidence"]["backlog_ready"] is True
    assert refreshed["coverage_complete"] is True


class _DummyScheduledTask:
    @staticmethod
    def create(name, system_prompt, prompt, schedule):
        return SimpleNamespace(uuid="collector-task-123", name=name, prompt=prompt, schedule=schedule)


class _DummyTaskScheduler:
    def __init__(self):
        self.added = []
        self.removed = []

    async def reload(self):
        return None

    async def add_task(self, task):
        self.added.append(task)

    async def remove_task_by_uuid(self, task_uuid):
        self.removed.append(task_uuid)

    @classmethod
    def get(cls):
        return dummy_scheduler


dummy_scheduler = _DummyTaskScheduler()


def test_schedule_collectors_persists_settings(tmp_path, monkeypatch):
    manager = OpportunitiesManager(str(tmp_path / "opportunities.db"))
    scheduler_module = SimpleNamespace(
        ScheduledTask=_DummyScheduledTask,
        TaskSchedule=lambda minute, hour, day, month, weekday: SimpleNamespace(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            weekday=weekday,
        ),
        TaskScheduler=_DummyTaskScheduler,
    )
    monkeypatch.setitem(sys.modules, "python.helpers.task_scheduler", scheduler_module)

    import asyncio

    result = asyncio.run(
        manager.schedule_collectors(
            "0 */4 * * *",
            [{"adapter": "json_file", "config": {"path": "/tmp/feed.json"}}],
        )
    )

    assert result["success"] is True
    schedule = manager.get_collector_schedule()
    assert schedule["enabled"] is True
    assert schedule["cron"] == "0 */4 * * *"
    assert schedule["task_uuid"] == "collector-task-123"


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
