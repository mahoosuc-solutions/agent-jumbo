"""
API endpoint for Workflow Engine operations.
Handles workflow CRUD, execution management, and visualization.
"""

from python.helpers.api import ApiHandler, Request, Response


class WorkflowEngineApi(ApiHandler):
    """API handler for workflow engine operations."""

    async def process(self, input: dict, request: Request) -> dict | Response:
        action = input.get("action", "")

        try:
            # Import the workflow manager
            from instruments.custom.workflow_engine.workflow_manager import (
                WorkflowEngineManager,
            )
            from instruments.custom.workflow_engine.workflow_visualizer import (
                WorkflowVisualizer,
            )

            # Initialize manager and visualizer
            manager = WorkflowEngineManager()
            visualizer = WorkflowVisualizer()

            # Route to appropriate handler
            if action == "list_workflows":
                workflows = manager.list_workflows()
                return {"success": True, "workflows": workflows}

            elif action == "get_workflow":
                workflow_id = input.get("workflow_id")
                name = input.get("name")
                workflow = manager.get_workflow(workflow_id=workflow_id, name=name)
                if workflow and "error" not in workflow:
                    return {"success": True, "workflow": workflow}
                return {
                    "success": False,
                    "error": workflow.get("error", "Workflow not found") if workflow else "Workflow not found",
                }

            elif action == "visualize_workflow":
                workflow_id = input.get("workflow_id")
                name = input.get("name")
                execution_id = input.get("execution_id")

                workflow = manager.get_workflow(workflow_id=workflow_id, name=name)
                if not workflow or "error" in workflow:
                    return {
                        "success": False,
                        "error": workflow.get("error", "Workflow not found") if workflow else "Workflow not found",
                    }

                # Get execution status if provided
                execution_status = None
                if execution_id:
                    execution_status = manager.get_execution_status(execution_id)

                diagram = visualizer.generate_workflow_diagram(workflow, execution_status)
                return {"success": True, "diagram": diagram}

            elif action == "list_executions":
                workflow_id = input.get("workflow_id")
                executions = manager.list_executions(workflow_id=workflow_id)
                return {"success": True, "executions": executions}

            elif action == "get_status":
                execution_id = input.get("execution_id")
                if not execution_id:
                    return {"success": False, "error": "execution_id required"}

                status = manager.get_execution_status(execution_id)
                execution = manager.get_execution(execution_id)
                return {
                    "success": True,
                    "execution": execution,
                    "status": status,
                }

            elif action == "recover_execution":
                execution_id = input.get("execution_id")
                if not execution_id:
                    return {"success": False, "error": "execution_id required"}
                status = manager.recover_execution(execution_id)
                return {"success": "error" not in status, "status": status, "error": status.get("error")}

            elif action == "restart_from_checkpoint":
                execution_id = input.get("execution_id")
                checkpoint_id = input.get("checkpoint_id")
                if not execution_id or not checkpoint_id:
                    return {"success": False, "error": "execution_id and checkpoint_id required"}
                status = manager.restart_from_checkpoint(execution_id, checkpoint_id)
                return {"success": "error" not in status, "status": status, "error": status.get("error")}

            elif action == "list_checkpoints":
                execution_id = input.get("execution_id")
                if not execution_id:
                    return {"success": False, "error": "execution_id required"}
                checkpoints = manager.list_execution_checkpoints(execution_id)
                return {"success": True, "checkpoints": checkpoints}

            elif action == "visualize_tasks":
                workflow_id = input.get("workflow_id")
                stage_id = input.get("stage_id")
                execution_id = input.get("execution_id")

                workflow = manager.get_workflow(workflow_id=workflow_id)
                if not workflow:
                    return {"success": False, "error": "Workflow not found"}

                # Find the stage
                stages = workflow.get("definition", workflow).get("stages", [])
                stage = next((s for s in stages if s.get("id") == stage_id), None)
                if not stage:
                    return {"success": False, "error": "Stage not found"}

                # Get task status if execution provided
                task_status = None
                if execution_id:
                    status = manager.get_execution_status(execution_id)
                    if status:
                        for sd in status.get("stage_details", []):
                            if sd.get("stage_id") == stage_id:
                                task_status = sd.get("tasks", [])
                                break

                diagram = visualizer.generate_task_diagram(stage, task_status)
                return {"success": True, "diagram": diagram}

            else:
                return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            return {"success": False, "error": str(e)}
