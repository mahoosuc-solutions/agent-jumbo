from __future__ import annotations

import json
from csv import DictReader
from pathlib import Path
from typing import Any


class BaseOpportunitySourceAdapter:
    source_type = "base"

    def collect(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError


class InlineJsonOpportunitySourceAdapter(BaseOpportunitySourceAdapter):
    source_type = "inline_json"

    def collect(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        opportunities = config.get("opportunities", [])
        if not isinstance(opportunities, list):
            raise ValueError("inline_json collector requires an opportunities list")
        return [item for item in opportunities if isinstance(item, dict)]


class JsonFileOpportunitySourceAdapter(BaseOpportunitySourceAdapter):
    source_type = "json_file"

    def collect(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        path = Path(str(config.get("path", "")).strip())
        if not path:
            raise ValueError("json_file collector requires a path")
        if not path.exists():
            raise ValueError(f"collector file not found: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("json_file collector must contain a JSON array")
        return [item for item in data if isinstance(item, dict)]


class JsonLinesOpportunitySourceAdapter(BaseOpportunitySourceAdapter):
    source_type = "jsonl_file"

    def collect(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        path = Path(str(config.get("path", "")).strip())
        if not path:
            raise ValueError("jsonl_file collector requires a path")
        if not path.exists():
            raise ValueError(f"collector file not found: {path}")
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        return rows


class CsvFileOpportunitySourceAdapter(BaseOpportunitySourceAdapter):
    source_type = "csv_file"

    def collect(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        path = Path(str(config.get("path", "")).strip())
        if not path:
            raise ValueError("csv_file collector requires a path")
        if not path.exists():
            raise ValueError(f"collector file not found: {path}")

        defaults = config.get("defaults", {})
        field_map = config.get("field_map", {})
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = DictReader(handle)
            for raw_row in reader:
                row = dict(defaults)
                for source_key, value in raw_row.items():
                    target_key = field_map.get(source_key, source_key)
                    row[target_key] = value
                rows.append(row)
        return rows


ADAPTERS: dict[str, BaseOpportunitySourceAdapter] = {
    adapter.source_type: adapter
    for adapter in (
        InlineJsonOpportunitySourceAdapter(),
        JsonFileOpportunitySourceAdapter(),
        JsonLinesOpportunitySourceAdapter(),
        CsvFileOpportunitySourceAdapter(),
    )
}


def get_adapter(source_type: str) -> BaseOpportunitySourceAdapter:
    adapter = ADAPTERS.get(source_type)
    if not adapter:
        raise ValueError(f"unsupported opportunity source adapter: {source_type}")
    return adapter
