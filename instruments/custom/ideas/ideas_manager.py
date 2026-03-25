"""
Ideas Manager — business logic for action-oriented ideas and project promotion.
"""

from __future__ import annotations

import os
import re
from typing import Any

from python.helpers import files, projects

from .ideas_db import IdeasDatabase

VALID_STATUSES = {"captured", "clarifying", "proposed", "promoted", "archived"}
VALID_PRIORITIES = {"low", "medium", "high"}
VALID_READINESS = {"low", "medium", "high", "ready"}


class IdeasManager:
    def __init__(self, db_path: str):
        self.db = IdeasDatabase(db_path)

    def get_dashboard(self) -> dict[str, Any]:
        return self.db.get_dashboard_data()

    def list_ideas(
        self, status: str | None = None, priority: str | None = None, q: str | None = None
    ) -> list[dict[str, Any]]:
        return self.db.list_ideas(status=status, priority=priority, q=q)

    def get_idea(self, idea_id: int) -> dict[str, Any] | None:
        return self.db.get_idea(idea_id)

    def create_idea(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = str(payload.get("title", "")).strip()
        raw_note = str(payload.get("raw_note", "")).strip()
        if not title:
            raise ValueError("title is required")
        if not raw_note:
            raise ValueError("raw_note is required")

        status = str(payload.get("status", "captured")).strip() or "captured"
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status: {status}")
        priority = str(payload.get("priority", "medium")).strip() or "medium"
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"invalid priority: {priority}")

        summary = str(payload.get("summary", "")).strip() or raw_note[:240]
        return self.db.create_idea(
            {
                "title": title,
                "raw_note": raw_note,
                "summary": summary,
                "status": status,
                "priority": priority,
                "theme": str(payload.get("theme", "")).strip(),
                "source": str(payload.get("source", "manual")).strip() or "manual",
                "conversation_context_id": payload.get("conversation_context_id"),
                "clarified_summary": str(payload.get("clarified_summary", "")).strip(),
                "first_slice": str(payload.get("first_slice", "")).strip(),
                "promotion_readiness": str(payload.get("promotion_readiness", "")).strip(),
            }
        )

    def update_idea(self, idea_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        if "status" in updates and updates["status"] not in VALID_STATUSES:
            raise ValueError(f"invalid status: {updates['status']}")
        if "priority" in updates and updates["priority"] not in VALID_PRIORITIES:
            raise ValueError(f"invalid priority: {updates['priority']}")
        if "promotion_readiness" in updates and updates["promotion_readiness"] not in ("", *VALID_READINESS):
            raise ValueError(f"invalid promotion_readiness: {updates['promotion_readiness']}")
        ok = self.db.update_idea(idea_id, updates)
        if not ok:
            raise ValueError(f"idea {idea_id} not found or no valid updates provided")
        idea = self.db.get_idea(idea_id)
        if not idea:
            raise RuntimeError(f"Failed to reload updated idea {idea_id}")
        return idea

    def promote_to_project(self, idea_id: int) -> dict[str, Any]:
        idea = self.db.get_idea(idea_id)
        if not idea:
            raise ValueError(f"idea {idea_id} not found")

        project_name = self._ensure_unique_project_name(self._slugify(idea["title"]))
        description = idea.get("summary") or idea.get("raw_note") or idea["title"]
        instructions = self._build_project_instructions(idea)
        project_data: projects.BasicProjectData = {
            "title": idea["title"],
            "description": description,
            "instructions": instructions,
            "color": "#2563eb",
            "memory": "own",
            "file_structure": projects._default_file_structure_settings(),
        }
        projects.create_project(project_name, project_data)
        project_folder = projects.get_project_folder(project_name)
        workflow_result = self._create_starter_workflow(idea, project_name, project_folder)
        work_items_created = self._seed_work_queue(idea, project_name, project_folder)
        self.db.mark_promoted(idea_id, project_name, workflow_result["name"])

        project = projects.load_edit_project_data(project_name)
        updated_idea = self.db.get_idea(idea_id)
        return {
            "idea": updated_idea,
            "project": project,
            "workflow": workflow_result,
            "work_items_created": work_items_created,
        }

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
        return slug[:48] or "idea-project"

    def _ensure_unique_project_name(self, base_name: str) -> str:
        candidate = base_name
        index = 2
        while os.path.exists(projects.get_project_folder(candidate)):
            candidate = f"{base_name}-{index}"
            index += 1
        return candidate

    def _build_project_instructions(self, idea: dict[str, Any]) -> str:
        theme = idea.get("theme", "").strip()
        summary = idea.get("summary", "").strip()
        raw_note = idea.get("raw_note", "").strip()
        lines = [
            f"Project origin: promoted from idea #{idea['id']}.",
            "Start by clarifying scope, desired outcome, and the next shippable milestone.",
        ]
        if theme:
            lines.append(f"Theme: {theme}")
        if summary:
            lines.append(f"Summary: {summary}")
        if raw_note:
            lines.append("")
            lines.append("Original idea note:")
            lines.append(raw_note)
        return "\n".join(lines)

    def _create_starter_workflow(self, idea: dict[str, Any], project_name: str, project_folder: str) -> dict[str, Any]:
        from instruments.custom.workflow_engine.workflow_manager import WorkflowEngineManager

        db_path = files.get_abs_path("./instruments/custom/workflow_engine/data/workflow.db")
        manager = WorkflowEngineManager(db_path)

        workflow_name = f"{project_name} Starter Workflow"
        stages = [
            {
                "id": "clarify_scope",
                "name": "Clarify Scope",
                "type": "design",
                "tasks": [
                    {"id": "review_origin", "name": "Review promoted idea context"},
                    {"id": "define_outcome", "name": "Define project outcome and first milestone"},
                ],
            },
            {
                "id": "shape_mvp",
                "name": "Shape MVP",
                "type": "design",
                "tasks": [
                    {"id": "identify_components", "name": "Identify core components and interfaces"},
                    {"id": "choose_first_slice", "name": "Choose the first shippable implementation slice"},
                ],
            },
            {
                "id": "execute_first_slice",
                "name": "Execute First Slice",
                "type": "mvp",
                "tasks": [
                    {"id": "implement_first_slice", "name": "Implement the first slice"},
                    {"id": "verify_first_slice", "name": "Verify and document outcomes"},
                ],
            },
        ]

        result = manager.create_workflow(
            name=workflow_name,
            stages=stages,
            description=f"Starter workflow generated from idea #{idea['id']} for project {project_name}.",
            global_context={
                "idea_id": idea["id"],
                "project_name": project_name,
                "project_path": project_folder,
            },
            settings={"parallel_execution": False, "require_approvals": True, "auto_retry": True},
            changed_by="ideas_dashboard",
            change_notes=f"Auto-generated from promoted idea #{idea['id']}",
        )
        if "error" in result:
            raise ValueError(result["error"])
        return {
            "id": result["workflow_id"],
            "name": workflow_name,
            "status": result["status"],
        }

    def _seed_work_queue(self, idea: dict[str, Any], project_name: str, project_folder: str) -> int:
        from instruments.custom.work_queue.work_queue_manager import WorkQueueManager

        db_path = files.get_abs_path("./instruments/custom/work_queue/data/work_queue.db")
        manager = WorkQueueManager(db_path)
        seed_items = [
            {
                "external_id": f"idea-{idea['id']}-scope",
                "title": f"Clarify scope for {project_name}",
                "description": f"Turn promoted idea #{idea['id']} into a concrete scope and first milestone.\n\n{idea.get('summary') or idea.get('raw_note') or ''}".strip(),
                "source": "idea",
                "source_type": "idea_next_step",
                "status": "queued",
                "priority_score": 72,
                "effort_estimate": "small",
                "effort_minutes": 45,
                "project_path": project_folder,
            },
            {
                "external_id": f"idea-{idea['id']}-mvp",
                "title": f"Define MVP slice for {project_name}",
                "description": "Identify the smallest useful version that can be shipped and validated quickly.",
                "source": "idea",
                "source_type": "idea_next_step",
                "status": "queued",
                "priority_score": 63,
                "effort_estimate": "small",
                "effort_minutes": 30,
                "project_path": project_folder,
            },
            {
                "external_id": f"idea-{idea['id']}-execution",
                "title": f"Implement first execution slice for {project_name}",
                "description": "Start the first concrete implementation task after scope and MVP are settled.",
                "source": "idea",
                "source_type": "idea_next_step",
                "status": "discovered",
                "priority_score": 55,
                "effort_estimate": "medium",
                "effort_minutes": 90,
                "project_path": project_folder,
            },
        ]
        manager.register_project(project_folder, project_name)
        return manager.create_manual_items(seed_items)
