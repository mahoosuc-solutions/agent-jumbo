from typing import Any

from instruments.custom.calendar_hub.calendar_db import CalendarHubDatabase
from instruments.custom.calendar_hub.providers.google_provider import GoogleCalendarProvider
from instruments.custom.calendar_hub.providers.mock_provider import MockCalendarProvider
from python.helpers.audit import hash_event
from python.helpers.task_scheduler import PlannedTask, TaskPlan, TaskScheduler, parse_datetime


class CalendarHubManager:
    def __init__(self, db_path: str):
        self.db = CalendarHubDatabase(db_path)
        self._providers = {
            "google": GoogleCalendarProvider,
            "mock": MockCalendarProvider,
        }

    def _get_provider(self, provider: str):
        provider_cls = self._providers.get(provider, MockCalendarProvider)
        return provider_cls()

    def connect_account(self, provider: str, mock: bool = True) -> dict[str, Any]:
        provider_key = provider if not mock else "mock"
        auth_state = "connected" if mock else "pending"
        account_id = self.db.add_account(provider=provider, auth_state=auth_state, token_ref=None, scopes=[])
        provider_impl = self._get_provider(provider_key)
        calendars = provider_impl.list_calendars({"id": account_id})
        if calendars:
            for cal in calendars:
                self.db.add_calendar(
                    account_id, name=cal["name"], external_id=cal.get("external_id"), color=cal.get("color")
                )
        else:
            self.db.add_calendar(account_id, name="Primary", external_id="mock-primary")
        auth_url = provider_impl.get_auth_url()
        return {"id": account_id, "provider": provider, "auth_state": auth_state, "auth_url": auth_url}

    def list_calendars(self, account_id: int) -> list[dict[str, Any]]:
        return self.db.list_calendars(account_id)

    def list_accounts(self) -> list[dict[str, Any]]:
        return self.db.list_accounts()

    def list_events(self, calendar_id: int | None = None, limit: int = 25) -> list[dict[str, Any]]:
        return self.db.list_events(calendar_id=calendar_id, limit=limit)

    def get_auth_url(self, provider: str) -> str | None:
        return self._get_provider(provider).get_auth_url()

    def complete_oauth(self, account_id: int, token_ref: str, scopes: list[str]) -> dict[str, Any]:
        self.db.update_account_auth(account_id, "connected", token_ref, scopes)
        return {"id": account_id, "auth_state": "connected", "token_ref": token_ref, "scopes": scopes}

    def create_event(
        self,
        calendar_id: int,
        title: str,
        start: str,
        end: str,
        attendees: list[str] | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        event_id = self.db.add_event(
            calendar_id=calendar_id,
            title=title,
            start=start,
            end=end,
            attendees=attendees,
            notes=notes,
        )
        event = self.db.get_event(event_id)
        if event:
            event_hash = hash_event("calendar.event_created", {"event_id": event_id, "title": title})
            self.db.add_audit_entry("event", event_id, event_hash)
        return event or {}

    def set_rules(self, account_id: int, rules: dict[str, Any]) -> dict[str, Any]:
        return self.db.upsert_rules(account_id, rules)

    def get_rules(self, account_id: int) -> dict[str, Any]:
        return self.db.get_rules(account_id) or {}

    def generate_prep(self, event_id: int, sources: list[str]) -> dict[str, Any]:
        event = self.db.get_event(event_id)
        if not event:
            return {}
        brief_text = f"Prep brief for {event['title']}: review agenda and related emails."
        return self.db.add_prep(event_id, brief_text, sources)

    async def create_followup(self, event_id: int, summary: str, due_at: str) -> dict[str, Any]:
        due_dt = parse_datetime(due_at)
        if due_dt is None:
            raise ValueError("due_at is required")
        plan = TaskPlan.create(todo=[due_dt])
        task_name = f"Calendar Follow-up: {summary} ({event_id})"
        task = PlannedTask.create(
            name=task_name,
            system_prompt="You are a helpful assistant.",
            prompt=f"Follow up: {summary} for calendar event {event_id}.",
            plan=plan,
            attachments=[],
        )
        await TaskScheduler.get().add_task(task, create_context=False)
        task_uuid = task.uuid
        followup = self.db.add_followup(event_id, task_uuid)
        return {"task_uuid": task_uuid, **followup}

    def update_event(self, event_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        event = self.db.update_event(event_id, updates)
        return event or {}

    def delete_event(self, event_id: int) -> bool:
        return self.db.delete_event(event_id)
