from typing import Any

from instruments.custom.life_os.life_db import LifeOSDatabase


class LifeOSManager:
    def __init__(self, db_path: str):
        self.db = LifeOSDatabase(db_path)

    def emit_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event_id = self.db.add_event(event_type, payload)
        return {"id": event_id, "type": event_type, "payload": payload}

    def get_dashboard(self) -> dict[str, Any]:
        events = self.db.list_events(limit=50)
        latest = events[0] if events else None
        count = len(events)
        widgets = self.db.list_widgets()
        sources = self._summarize_sources(events)
        return {
            "event_count": count,
            "latest_event": latest,
            "widgets": widgets,
            "sources": sources,
        }

    def generate_daily_plan(self, plan_date: str) -> dict[str, Any]:
        content = f"Daily plan for {plan_date}: review events and set top 3 priorities."
        plan_id = self.db.add_daily_plan(plan_date, content, status="draft")
        return {"id": plan_id, "plan_date": plan_date, "content": content, "status": "draft"}

    def configure_widgets(self, widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for index, widget in enumerate(widgets):
            self.db.upsert_widget(
                widget_id=widget["widget_id"],
                enabled=widget.get("enabled", True),
                order_index=widget.get("order_index", index),
                config=widget.get("config", {}),
            )
        return self.db.list_widgets()

    def _summarize_sources(self, events: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in events:
            source = event["type"].split(".")[0] if event.get("type") else "unknown"
            counts[source] = counts.get(source, 0) + 1
        return counts
