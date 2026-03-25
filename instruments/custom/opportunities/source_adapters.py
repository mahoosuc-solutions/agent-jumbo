from __future__ import annotations

import json
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


ADAPTERS: dict[str, BaseOpportunitySourceAdapter] = {
    adapter.source_type: adapter
    for adapter in (
        InlineJsonOpportunitySourceAdapter(),
        JsonFileOpportunitySourceAdapter(),
    )
}


def get_adapter(source_type: str) -> BaseOpportunitySourceAdapter:
    adapter = ADAPTERS.get(source_type)
    if not adapter:
        raise ValueError(f"unsupported opportunity source adapter: {source_type}")
    return adapter
