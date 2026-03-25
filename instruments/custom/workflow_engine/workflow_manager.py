"""
Workflow Engine Manager - Orchestration logic for workflows and training
Coordinates workflow execution, stage transitions, and skill development
"""

import json
import os
from datetime import datetime
from pathlib import Path

import jsonschema

from python.helpers import folder_delivery_workflow

from .workflow_db import WorkflowEngineDatabase


class WorkflowEngineManager:
    """Manager for workflow orchestration and training"""

    def __init__(self, db_path: str):
        self.db = WorkflowEngineDatabase(db_path)
        self._schema_cache = {}
        self._load_schemas()

    def _load_schemas(self):
        """Load JSON schemas for validation"""
        schema_dir = Path(__file__).parent / "schemas"
        for schema_file in schema_dir.glob("*.schema.json"):
            with open(schema_file) as f:
                schema_name = schema_file.stem.replace(".schema", "")
                self._schema_cache[schema_name] = json.load(f)

    def _validate_workflow(self, definition: dict, strict: bool = False) -> dict:
        """Validate workflow definition against schema"""
        # Skip validation if schema not loaded or not in strict mode
        if "workflow" not in self._schema_cache or not strict:
            # Do basic validation
            if not definition.get("name"):
                return {"valid": False, "errors": ["Workflow name is required"]}
            if not definition.get("stages"):
                return {"valid": False, "errors": ["Workflow must have at least one stage"]}
            return {"valid": True, "errors": []}

        try:
            jsonschema.validate(definition, self._schema_cache["workflow"])
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {"valid": False, "errors": [str(e.message)]}

    # ========== Workflow Management ==========

    def create_workflow(
        self,
        name: str,
        stages: list,
        description: str | None = None,
        version: str = "1.0.0",
        global_context: dict | None = None,
        settings: dict | None = None,
        is_template: bool = False,
        required_secrets: list | None = None,
        changed_by: str = "system",
        change_notes: str | None = None,
    ) -> dict:
        """Create a new workflow definition with versioning and secrets support"""
        definition = {
            "id": name.lower().replace(" ", "_"),
            "name": name,
            "version": version,
            "description": description,
            "stages": stages,
            "required_secrets": required_secrets or [],
            "global_context": global_context or {},
            "settings": settings or {"parallel_execution": False, "require_approvals": True, "auto_retry": True},
        }

        # Validate
        validation = self._validate_workflow(definition)
        if not validation["valid"]:
            return {"error": f"Invalid workflow: {validation['errors']}"}

        # Determine workflow type from stages
        stage_types = [s.get("type") for s in stages if s.get("type")]
        workflow_type = self._infer_workflow_type(stage_types)

        workflow_id = self.db.save_workflow(
            name=name,
            definition=definition,
            version=version,
            description=description,
            workflow_type=workflow_type,
            is_template=is_template,
            changed_by=changed_by,
            change_notes=change_notes,
        )

        return {
            "workflow_id": workflow_id,
            "name": name,
            "type": workflow_type,
            "stages": len(stages),
            "status": "created",
        }

    def _infer_workflow_type(self, stage_types: list) -> str:
        """Infer workflow type from stage types"""
        if all(t in ["design", "poc", "mvp", "production"] for t in stage_types):
            return "product_development"
        elif "support" in stage_types:
            return "service_delivery"
        elif "upgrade" in stage_types:
            return "maintenance"
        return "custom"

    def get_workflow(self, workflow_id: int | None = None, name: str | None = None) -> dict:
        """Get workflow details"""
        return self.db.get_workflow(workflow_id, name) or {"error": "Workflow not found"}

    def list_workflows(self, workflow_type: str | None = None, templates_only: bool = False) -> list:
        """List all workflows"""
        return self.db.list_workflows(workflow_type, templates_only)

    def list_executions(self, workflow_id: int | None = None, status: str | None = None, limit: int = 50) -> list:
        """List workflow executions"""
        return self.db.list_executions(workflow_id, status, limit)

    def delete_workflow(self, workflow_id: int) -> dict:
        """Delete a workflow"""
        if self.db.delete_workflow(workflow_id):
            return {"status": "deleted", "workflow_id": workflow_id}
        return {"error": "Workflow not found"}

    def clone_workflow(self, workflow_id: int, new_name: str) -> dict:
        """Clone a workflow to create a new one"""
        original = self.db.get_workflow(workflow_id=workflow_id)
        if not original:
            return {"error": "Workflow not found"}

        definition = original["definition"].copy()
        definition["id"] = new_name.lower().replace(" ", "_")
        definition["name"] = new_name

        return self.create_workflow(
            name=new_name,
            stages=definition["stages"],
            description=f"Cloned from: {original['name']}",
            version="1.0.0",
            global_context=definition.get("global_context"),
            settings=definition.get("settings"),
        )

    # ========== Workflow Execution ==========

    def start_workflow(
        self,
        workflow_id: int | None = None,
        workflow_name: str | None = None,
        execution_name: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Start executing a workflow, verifying required secrets first"""
        workflow = self.db.get_workflow(workflow_id=workflow_id, name=workflow_name)
        if not workflow:
            return {"error": "Workflow not found"}

        # Check required secrets
        required_secrets = workflow["definition"].get("required_secrets", [])
        missing_secrets = self._check_secrets_availability(required_secrets)
        if missing_secrets:
            return {
                "error": "Missing required secrets",
                "missing_secrets": missing_secrets,
                "guide": "Please configure these secrets in Settings > External or providing them via the secrets tool.",
            }

        execution_id = self.db.start_execution(
            workflow_id=workflow["workflow_id"],
            name=execution_name or f"{workflow['name']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            context=context,
        )

        # Initialize first stage
        stages = workflow["definition"].get("stages", [])
        if stages:
            first_stage = stages[0]
            self.db.update_execution(execution_id=execution_id, current_stage_id=first_stage["id"])
            self.db.update_stage_progress(execution_id=execution_id, stage_id=first_stage["id"], status="pending")

        return {
            "execution_id": execution_id,
            "workflow_id": workflow["workflow_id"],
            "workflow_name": workflow["name"],
            "current_stage": stages[0]["id"] if stages else None,
            "status": "running",
        }

    def get_execution_status(self, execution_id: int) -> dict:
        """Get current execution status"""
        execution = self.db.get_execution(execution_id)
        if not execution:
            return {"error": "Execution not found"}

        workflow = self.db.get_workflow(workflow_id=execution["workflow_id"])
        stage_progress = self.db.get_stage_progress(execution_id)
        task_progress = self.db.get_task_executions(execution_id)

        # Calculate overall progress
        definition = workflow["definition"]
        total_stages = len(definition.get("stages", []))
        completed_stages = len([s for s in stage_progress if s["status"] == "completed"])

        return {
            "execution_id": execution_id,
            "workflow_name": workflow["name"],
            "status": execution["status"],
            "current_stage": execution["current_stage_id"],
            "current_task": execution["current_task_id"],
            "progress": {
                "stages_completed": completed_stages,
                "stages_total": total_stages,
                "percentage": round((completed_stages / total_stages * 100) if total_stages else 0, 1),
            },
            "stage_details": stage_progress,
            "task_details": task_progress,
            "started_at": execution["started_at"],
            "context": execution["context"],
        }

    def advance_stage(self, execution_id: int, force: bool = False) -> dict:
        """Advance to next stage"""
        execution = self.db.get_execution(execution_id)
        if not execution:
            return {"error": "Execution not found"}

        workflow = self.db.get_workflow(workflow_id=execution["workflow_id"])
        definition = workflow["definition"]
        stages = definition.get("stages", [])

        current_stage_id = execution["current_stage_id"]
        current_stage = next((s for s in stages if s["id"] == current_stage_id), None)

        if not current_stage:
            return {"error": "Current stage not found"}

        # Check exit criteria unless forced
        if not force:
            criteria_check = self._check_exit_criteria(execution_id, current_stage)
            if not criteria_check["met"]:
                return {"error": "Exit criteria not met", "unmet_criteria": criteria_check["unmet"]}

        # Check approval if required
        if current_stage.get("approval_required"):
            stage_progress = self.db.get_stage_progress(execution_id, current_stage_id)
            if stage_progress and stage_progress.get("approval_status") != "approved":
                return {"error": "Stage requires approval before advancing"}

        # Mark current stage complete
        self.db.update_stage_progress(execution_id=execution_id, stage_id=current_stage_id, status="completed")

        # Find next stage
        current_idx = next((i for i, s in enumerate(stages) if s["id"] == current_stage_id), -1)
        if current_idx >= len(stages) - 1:
            # Workflow complete
            self.db.update_execution(execution_id=execution_id, status="completed")
            return {"status": "workflow_completed", "execution_id": execution_id}

        # Advance to next stage
        next_stage = stages[current_idx + 1]
        self.db.update_execution(execution_id=execution_id, current_stage_id=next_stage["id"], current_task_id=None)
        self.db.update_stage_progress(execution_id=execution_id, stage_id=next_stage["id"], status="pending")

        return {
            "status": "advanced",
            "previous_stage": current_stage_id,
            "current_stage": next_stage["id"],
            "stage_name": next_stage["name"],
        }

    def _check_exit_criteria(self, execution_id: int, stage: dict) -> dict:
        """Check if stage exit criteria are met"""
        exit_criteria = stage.get("exit_criteria", [])
        if not exit_criteria:
            return {"met": True, "unmet": []}

        stage_progress = self.db.get_stage_progress(execution_id, stage["id"])
        exit_met = stage_progress.get("exit_criteria_met", []) if stage_progress else []

        unmet = [c for c in exit_criteria if c["id"] not in exit_met]

        return {"met": len(unmet) == 0, "unmet": unmet}

    def approve_stage(self, execution_id: int, stage_id: str, approved_by: str, notes: str | None = None) -> dict:
        """Approve a stage for advancement"""
        self.db.update_stage_progress(
            execution_id=execution_id,
            stage_id=stage_id,
            approval_status="approved",
            approved_by=approved_by,
            notes=notes,
        )

        return {"status": "approved", "stage_id": stage_id, "approved_by": approved_by}

    def complete_criterion(
        self, execution_id: int, stage_id: str, criterion_id: str, criterion_type: str = "exit"
    ) -> dict:
        """Mark a criterion as met"""
        stage_progress = self.db.get_stage_progress(execution_id, stage_id)
        if not stage_progress:
            return {"error": "Stage not found"}

        if criterion_type == "entry":
            criteria_met = stage_progress.get("entry_criteria_met", [])
        else:
            criteria_met = stage_progress.get("exit_criteria_met", [])

        if criterion_id not in criteria_met:
            criteria_met.append(criterion_id)

        if criterion_type == "entry":
            self.db.update_stage_progress(execution_id=execution_id, stage_id=stage_id, entry_criteria_met=criteria_met)
        else:
            self.db.update_stage_progress(execution_id=execution_id, stage_id=stage_id, exit_criteria_met=criteria_met)

        return {"status": "criterion_completed", "criterion_id": criterion_id, "type": criterion_type}

    def complete_deliverable(
        self, execution_id: int, stage_id: str, deliverable_id: str, artifact_path: str | None = None
    ) -> dict:
        """Mark a deliverable as completed"""
        stage_progress = self.db.get_stage_progress(execution_id, stage_id)
        if not stage_progress:
            return {"error": "Stage not found"}

        completed = stage_progress.get("deliverables_completed", [])
        if deliverable_id not in completed:
            completed.append(deliverable_id)
            self.db.update_stage_progress(
                execution_id=execution_id, stage_id=stage_id, deliverables_completed=completed
            )

        return {"status": "deliverable_completed", "deliverable_id": deliverable_id, "artifact_path": artifact_path}

    # ========== Task Execution ==========

    def start_task(
        self,
        execution_id: int,
        stage_id: str,
        task_id: str,
        input_data: dict | None = None,
        assigned_to: str | None = None,
        agent_id: str | None = None,
    ) -> dict:
        """Start executing a task

        If the task has ralph_loop configuration, this will also start a
        Ralph loop to autonomously iterate until completion.
        """
        execution = self.db.get_execution(execution_id)
        run_binding = self._get_folder_delivery_binding(execution)
        if run_binding and stage_id == "execution":
            folder_delivery_workflow.ensure_task_claim_owner(
                project_name=run_binding["project_name"],
                run_id=run_binding["run_id"],
                task_id=task_id,
                assigned_to=assigned_to or "",
            )

        self.db.update_task_execution(
            execution_id=execution_id,
            stage_id=stage_id,
            task_id=task_id,
            status="running",
            input_data=input_data,
            assigned_to=assigned_to,
        )

        self.db.update_execution(execution_id=execution_id, current_task_id=task_id)

        # Update stage to in_progress if pending
        stage_progress = self.db.get_stage_progress(execution_id, stage_id)
        if stage_progress and stage_progress.get("status") == "pending":
            self.db.update_stage_progress(execution_id=execution_id, stage_id=stage_id, status="in_progress")

        result = {"status": "started", "task_id": task_id, "stage_id": stage_id}

        # Check if task has Ralph loop configuration
        task_config = self._get_task_config(execution_id, stage_id, task_id)
        if task_config and task_config.get("ralph_loop", {}).get("enabled"):
            ralph_result = self._start_ralph_loop_for_task(
                execution_id=execution_id,
                stage_id=stage_id,
                task_id=task_id,
                task_config=task_config,
                agent_id=agent_id,
            )
            result["ralph_loop"] = ralph_result

        return result

    def _get_task_config(self, execution_id: int, stage_id: str, task_id: str) -> dict:
        """Get task configuration from workflow definition"""
        execution = self.db.get_execution(execution_id)
        if not execution:
            return None

        workflow = self.db.get_workflow(workflow_id=execution["workflow_id"])
        if not workflow:
            return None

        definition = workflow.get("definition", {})
        for stage in definition.get("stages", []):
            if stage["id"] == stage_id:
                for task in stage.get("tasks", []):
                    if task["id"] == task_id:
                        return task
        return None

    def _start_ralph_loop_for_task(
        self, execution_id: int, stage_id: str, task_id: str, task_config: dict, agent_id: str | None = None
    ) -> dict:
        """Start a Ralph loop for a workflow task

        Returns the Ralph loop information or error.
        """
        try:
            from instruments.custom.ralph_loop.ralph_manager import RalphLoopManager

            ralph_config = task_config.get("ralph_loop", {})

            ralph_manager = RalphLoopManager()
            result = ralph_manager.start_task_loop(
                workflow_execution_id=execution_id,
                task_id=task_id,
                prompt=ralph_config.get("prompt", task_config.get("description", "")),
                name=f"{task_config.get('name', task_id)} (Workflow Task)",
                completion_promise=ralph_config.get("completion_promise"),
                max_iterations=ralph_config.get("max_iterations", 30),
                agent_id=agent_id,
            )

            return result

        except ImportError:
            return {"error": "Ralph Loop module not available"}
        except Exception as e:
            return {"error": str(e)}

    def complete_task(self, execution_id: int, stage_id: str, task_id: str, output_data: dict | None = None) -> dict:
        """Complete a task successfully with optional auditing"""
        execution = self.db.get_execution(execution_id)
        run_binding = self._get_folder_delivery_binding(execution)
        if run_binding and output_data and isinstance(output_data, dict):
            artifact_updates = output_data.get("artifact_updates")
            if artifact_updates:
                artifact_result = folder_delivery_workflow.apply_artifact_updates(
                    project_name=run_binding["project_name"],
                    run_id=run_binding["run_id"],
                    task_id=task_id,
                    stage_family=stage_id,
                    producer=run_binding["workflow_profile"],
                    artifact_updates=artifact_updates,
                    assigned_to=str(output_data.get("assigned_to", "")).strip(),
                )
                output_data = {**output_data, "artifact_write_result": artifact_result}

        self.db.update_task_execution(
            execution_id=execution_id, stage_id=stage_id, task_id=task_id, status="completed", output_data=output_data
        )

        # Record audit event in DB if task has auditing enabled
        task_config = self._get_task_config(execution_id, stage_id, task_id)
        if task_config and task_config.get("metadata", {}).get("auditing") == "enabled":
            self.db.save_event(
                execution_id=execution_id,
                event_type="audit",
                stage_id=stage_id,
                task_id=task_id,
                data={
                    "action": task_config.get("action", "manual_task"),
                    "output_summary": output_data,
                },
            )

        return {"status": "completed", "task_id": task_id, "output": output_data}

    def fail_task(self, execution_id: int, stage_id: str, task_id: str, error: str, retry: bool = False) -> dict:
        """Mark a task as failed"""
        if retry:
            # Reset for retry
            self.db.update_task_execution(
                execution_id=execution_id, stage_id=stage_id, task_id=task_id, status="pending", error=error
            )
            return {"status": "retry_scheduled", "task_id": task_id, "error": error}

        self.db.update_task_execution(
            execution_id=execution_id, stage_id=stage_id, task_id=task_id, status="failed", error=error
        )

        return {"status": "failed", "task_id": task_id, "error": error}

    def get_next_task(self, execution_id: int) -> dict:
        """Get the next task to execute"""
        execution = self.db.get_execution(execution_id)
        if not execution:
            return {"error": "Execution not found"}

        workflow = self.db.get_workflow(workflow_id=execution["workflow_id"])
        definition = workflow["definition"]
        current_stage_id = execution["current_stage_id"]

        current_stage = next((s for s in definition.get("stages", []) if s["id"] == current_stage_id), None)
        if not current_stage:
            return {"error": "Current stage not found"}

        tasks = current_stage.get("tasks", [])
        task_executions = self.db.get_task_executions(execution_id, current_stage_id)
        completed_tasks = {t["task_id"] for t in task_executions if t["status"] == "completed"}

        # Find next available task (considering dependencies)
        for task in tasks:
            if task["id"] in completed_tasks:
                continue

            # Check dependencies
            deps = task.get("dependencies", [])
            if all(d in completed_tasks for d in deps):
                return {"task": task, "stage_id": current_stage_id, "has_more": len(completed_tasks) + 1 < len(tasks)}

        # All tasks complete
        return {"task": None, "stage_complete": True, "stage_id": current_stage_id}

    def _get_folder_delivery_binding(self, execution: dict | None) -> dict[str, str] | None:
        if not execution:
            return None
        context = execution.get("context")
        if not isinstance(context, dict):
            return None
        if context.get("workflow_profile") != folder_delivery_workflow.WORKFLOW_PROFILE_ID:
            return None
        project_name = str(context.get("project_name", "")).strip()
        run_id = str(context.get("run_id", "")).strip()
        if not project_name or not run_id:
            return None
        return {
            "project_name": project_name,
            "run_id": run_id,
            "workflow_profile": str(context.get("workflow_profile", "")),
        }

    # ========== Workflow Templates ==========

    def load_template(self, template_path: str) -> dict:
        """Load a workflow template from file"""
        path = Path(template_path)
        if not path.exists():
            return {"error": f"Template not found: {template_path}"}

        try:
            with open(path) as f:
                template = json.load(f)

            validation = self._validate_workflow(template)
            if not validation["valid"]:
                return {"error": f"Invalid template: {validation['errors']}"}

            return template
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON: {e}"}

    def create_from_template(self, template_path: str, name: str, customizations: dict | None = None) -> dict:
        """Create workflow from template with customizations"""
        template = self.load_template(template_path)
        if "error" in template:
            return template

        # Apply customizations
        if customizations:
            if "stages" in customizations:
                for custom_stage in customizations["stages"]:
                    for i, stage in enumerate(template["stages"]):
                        if stage["id"] == custom_stage.get("id"):
                            template["stages"][i].update(custom_stage)

            if "global_context" in customizations:
                template["global_context"] = {**template.get("global_context", {}), **customizations["global_context"]}

            if "settings" in customizations:
                template["settings"] = {**template.get("settings", {}), **customizations["settings"]}

        return self.create_workflow(
            name=name,
            stages=template["stages"],
            description=template.get("description"),
            version=template.get("version", "1.0.0"),
            global_context=template.get("global_context"),
            settings=template.get("settings"),
        )

    def list_templates(self) -> list:
        """List available workflow templates"""
        templates = []

        # Check built-in templates
        template_dir = Path(__file__).parent / "templates"
        if template_dir.exists():
            for template_file in template_dir.glob("*.json"):
                try:
                    with open(template_file) as f:
                        t = json.load(f)
                        templates.append(
                            {
                                "id": template_file.stem,
                                "name": t.get("name", template_file.stem),
                                "description": t.get("description"),
                                "stages": len(t.get("stages", [])),
                                "path": str(template_file),
                            }
                        )
                except Exception:
                    pass

        return templates

    # ========== Skill & Training Management ==========

    def register_skill(
        self,
        skill_id: str,
        name: str,
        category: str,
        description: str | None = None,
        proficiency_levels: list | None = None,
        prerequisites: list | None = None,
        related_tools: list | None = None,
    ) -> dict:
        """Register a new skill"""
        self.db.save_skill(
            skill_id=skill_id,
            name=name,
            category=category,
            description=description,
            proficiency_levels=proficiency_levels
            or [
                {"level": 1, "name": "novice", "criteria": ["Basic understanding"]},
                {"level": 2, "name": "beginner", "criteria": ["Can perform with guidance"]},
                {"level": 3, "name": "intermediate", "criteria": ["Can perform independently"]},
                {"level": 4, "name": "advanced", "criteria": ["Can optimize and improve"]},
                {"level": 5, "name": "expert", "criteria": ["Can teach and innovate"]},
            ],
            prerequisites=prerequisites,
            related_tools=related_tools,
        )

        return {"status": "registered", "skill_id": skill_id, "name": name, "category": category}

    def get_skill(self, skill_id: str) -> dict:
        """Get skill details"""
        return self.db.get_skill(skill_id) or {"error": "Skill not found"}

    def list_skills(self, category: str | None = None) -> list:
        """List all skills"""
        return self.db.list_skills(category)

    def track_skill_usage(
        self, agent_id: str, skill_id: str, success: bool = True, assessment_score: float | None = None
    ) -> dict:
        """Track skill usage for an agent"""
        self.db.update_skill_progress(
            agent_id=agent_id, skill_id=skill_id, completions=1 if success else 0, assessment_score=assessment_score
        )

        # Check for level up
        progress = self.db.get_skill_progress(agent_id, skill_id)
        skill = self.db.get_skill(skill_id)

        if progress and skill:
            current_level = progress[0]["current_level"] if progress else 1
            completions = progress[0]["completions"] if progress else 0
            levels = skill.get("proficiency_levels", [])

            for level in levels:
                if level["level"] > current_level:
                    min_completions = level.get("min_completions", level["level"] * 5)
                    if completions >= min_completions:
                        self.db.update_skill_progress(
                            agent_id=agent_id, skill_id=skill_id, current_level=level["level"]
                        )
                        return {
                            "status": "level_up",
                            "skill_id": skill_id,
                            "new_level": level["level"],
                            "level_name": level["name"],
                        }
                    break

        return {"status": "tracked", "skill_id": skill_id, "success": success}

    def get_agent_skills(self, agent_id: str) -> list:
        """Get all skills for an agent with progress"""
        return self.db.get_skill_progress(agent_id)

    def create_learning_path(
        self,
        path_id: str,
        name: str,
        target_role: str,
        description: str | None = None,
        modules: list | None = None,
        estimated_hours: float | None = None,
        certification: dict | None = None,
    ) -> dict:
        """Create a learning path"""
        self.db.save_learning_path(
            path_id=path_id,
            name=name,
            target_role=target_role,
            description=description,
            estimated_hours=estimated_hours,
            modules=modules,
            certification=certification,
        )

        return {"status": "created", "path_id": path_id, "name": name, "target_role": target_role}

    def get_learning_path(self, path_id: str) -> dict:
        """Get learning path details"""
        return self.db.get_learning_path(path_id) or {"error": "Learning path not found"}

    def list_learning_paths(self, target_role: str | None = None) -> list:
        """List learning paths"""
        return self.db.list_learning_paths(target_role)

    # ========== Cleanup ==========

    def cleanup_stale_executions(self, max_age_hours: int = 24) -> dict:
        """Clean up stale running executions older than max_age_hours"""
        return self.db.cleanup_stale_executions(max_age_hours)

    # ========== Execution History ==========

    def get_execution_history(self, workflow_id: int | None = None, status: str | None = None, limit: int = 50) -> list:
        """Get execution history"""
        return self.db.list_executions(workflow_id, status, limit)

    def get_execution_events(self, execution_id: int) -> list:
        """Get execution event log"""
        return self.db.get_execution_events(execution_id)

    # ========== Statistics ==========

    def get_stats(self) -> dict:
        """Get workflow engine statistics.

        Also performs opportunistic cleanup of stale executions
        (older than 24h) so the system stays tidy without needing
        a separate scheduled task.
        """
        try:
            self.cleanup_stale_executions()
        except Exception:
            pass  # never let cleanup failure break stats retrieval
        return self.db.get_stats()

    def get_recent_executions(self, limit: int = 5) -> list:
        """Get recent workflow executions"""
        return self.db.get_recent_executions(limit)

    def get_top_skills(self, limit: int = 5) -> list:
        """Get top skills by level"""
        return self.db.get_top_skills(limit)

    def get_execution(self, execution_id: int) -> dict:
        """Get execution details"""
        return self.db.get_execution(execution_id)

    def get_learning_progress(self, path_id: str, agent_id: str = "agent_0") -> dict:
        """Get learning progress for a path"""
        return self.db.get_learning_progress(path_id, agent_id)

    def get_training_module(self, module_id: str) -> dict:
        """Get training module details"""
        return self.db.get_training_module(module_id)

    def get_agent_proficiency(self, agent_id: str = "agent_0") -> list:
        """Get all skill proficiencies for an agent"""
        return self.db.get_agent_proficiency(agent_id)

    def _check_secrets_availability(self, required_secrets: list) -> list:
        """Check if required secrets are available in the environment or files"""
        if not required_secrets:
            return []

        missing = []
        # Check environment variables
        # And check common secrets storage (e.g., usr/secrets.json)
        secrets_file = Path("usr/secrets.json")
        saved_secrets = {}
        if secrets_file.exists():
            try:
                with open(secrets_file) as f:
                    saved_secrets = json.load(f)
            except Exception:
                pass

        for secret in required_secrets:
            if secret not in os.environ and secret not in saved_secrets:
                # Special check for Gmail since we know it's stored in a specific place
                gmail_missing = secret == "GMAIL_OAUTH" and not self._check_gmail_config()  # pragma: allowlist secret
                if gmail_missing or secret != "GMAIL_OAUTH":  # pragma: allowlist secret
                    missing.append(secret)

        return missing

    def _check_gmail_config(self) -> bool:
        """Helper to check if Gmail is configured"""
        # This is a placeholder for actual Gmail config check
        # based on GMAIL_INTEGRATION_STATUS.md
        gmail_data_dir = Path("data/gmail_credentials")
        if gmail_data_dir.exists() and any(gmail_data_dir.iterdir()):
            return True
        return False

    def get_workflow_history(self, name: str) -> list:
        """Get history of a workflow versions"""
        return self.db.get_workflow_history(name)

    def rollback_workflow(self, name: str, version: str, changed_by: str = "system") -> dict:
        """Rollback to a previous version and audit"""
        if self.db.rollback_workflow(name, version, changed_by):
            return {"status": "success", "message": f"Rolled back {name} to version {version}"}
        return {"error": "Rollback failed. Version not found."}

    def get_audit_logs(self, limit: int = 50) -> list:
        """Get recent audit events across all executions"""
        return self.db.get_events_by_type("audit", limit)
