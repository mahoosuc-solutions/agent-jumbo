"""
Virtual Team Orchestrator
Coordinates specialized AI agents for collaborative software development
"""

import os
from datetime import datetime

from .team_db import VirtualTeamDatabase


class VirtualTeamOrchestrator:
    """Orchestrates virtual team of specialized AI agents"""

    # Standard agent roles
    AGENT_ROLES = {
        "architect": {
            "specialization": "system_design",
            "expertise": ["architecture_patterns", "scalability", "cloud_design", "security"],
            "tools": ["diagram_tools", "documentation", "code_review"],
        },
        "developer": {
            "specialization": "software_engineering",
            "expertise": ["backend", "frontend", "api_design", "testing"],
            "tools": ["code_generation", "debugging", "refactoring"],
        },
        "dba": {
            "specialization": "database_engineering",
            "expertise": ["schema_design", "query_optimization", "migrations", "indexing"],
            "tools": ["database_tools", "performance_monitoring"],
        },
        "qa": {
            "specialization": "quality_assurance",
            "expertise": ["test_automation", "manual_testing", "performance_testing", "security_testing"],
            "tools": ["testing_frameworks", "bug_tracking"],
        },
        "devops": {
            "specialization": "infrastructure",
            "expertise": ["ci_cd", "containerization", "orchestration", "monitoring"],
            "tools": ["docker", "kubernetes", "terraform", "ci_cd_pipelines"],
        },
        "security": {
            "specialization": "cybersecurity",
            "expertise": ["threat_modeling", "penetration_testing", "compliance", "encryption"],
            "tools": ["security_scanners", "audit_tools"],
        },
        "pm": {
            "specialization": "project_management",
            "expertise": ["agile", "planning", "stakeholder_management", "risk_management"],
            "tools": ["project_tracking", "reporting"],
        },
    }

    # Standard workflow templates
    WORKFLOW_TEMPLATES = {
        "full_stack_development": {
            "tasks": [
                {"role": "architect", "task_type": "architecture_design", "parallel_group": None},
                {"role": "dba", "task_type": "schema_design", "parallel_group": 1},
                {"role": "developer", "task_type": "backend_development", "parallel_group": 1},
                {"role": "developer", "task_type": "frontend_development", "parallel_group": 1},
                {"role": "qa", "task_type": "test_development", "parallel_group": 2},
                {"role": "security", "task_type": "security_review", "parallel_group": 2},
                {"role": "devops", "task_type": "deployment_setup", "parallel_group": None},
            ]
        },
        "api_development": {
            "tasks": [
                {"role": "architect", "task_type": "api_design", "parallel_group": None},
                {"role": "developer", "task_type": "implementation", "parallel_group": None},
                {"role": "qa", "task_type": "api_testing", "parallel_group": 1},
                {"role": "security", "task_type": "security_testing", "parallel_group": 1},
                {"role": "devops", "task_type": "deployment", "parallel_group": None},
            ]
        },
        "database_migration": {
            "tasks": [
                {"role": "dba", "task_type": "migration_planning", "parallel_group": None},
                {"role": "dba", "task_type": "schema_migration", "parallel_group": None},
                {"role": "developer", "task_type": "code_updates", "parallel_group": None},
                {"role": "qa", "task_type": "validation_testing", "parallel_group": None},
                {"role": "devops", "task_type": "rollback_plan", "parallel_group": None},
            ]
        },
    }

    def __init__(self, db_path: str = "data/virtual_team.db"):
        self.db = VirtualTeamDatabase(db_path)
        self.initialize_standard_agents()

    def initialize_standard_agents(self):
        """Register standard agent roles if not already registered"""
        existing_agents = self.db.list_agents()
        existing_roles = {agent["agent_role"] for agent in existing_agents}

        for role, config in self.AGENT_ROLES.items():
            if role not in existing_roles:
                self.db.register_agent(
                    agent_name=f"{role.upper()} Agent",
                    agent_role=role,
                    specialization=config["specialization"],
                    expertise_areas=config["expertise"],
                    tools_available=config["tools"],
                )

    # Project management
    def create_project(
        self,
        project_name: str,
        description: str | None = None,
        workflow_template: str | None = None,
        status: str = "active",
        metadata: dict | None = None,
    ) -> dict:
        """Create a new project in the virtual team database"""
        project_id = self.db.create_project(
            project_name=project_name,
            description=description,
            workflow_template=workflow_template,
            status=status,
            metadata=metadata,
        )
        project = self.db.get_project(project_id)
        return project or {"project_id": project_id, "project_name": project_name}

    # Task routing and assignment
    def route_task(
        self,
        task_name: str,
        task_type: str,
        description: str | None = None,
        context: dict | None = None,
        priority: str = "medium",
        complexity: str | None = None,
    ) -> dict:
        """Automatically route task to best-suited agent"""

        # Determine required role based on task type
        required_role = self._determine_required_role(task_type, context)

        if not required_role:
            return {"error": f"Could not determine agent role for task type: {task_type}"}

        # Create task
        task_id = self.db.create_task(
            task_name=task_name,
            task_type=task_type,
            description=description,
            required_role=required_role,
            priority=priority,
            complexity=complexity,
            context_data=context,
            created_by="VirtualTeamOrchestrator",
        )

        # Find agent with required role
        agent = self.db.get_agent_by_role(required_role)

        if not agent:
            return {
                "task_id": task_id,
                "status": "pending",
                "message": f"Task created but no {required_role} agent available",
                "required_role": required_role,
            }

        # Assign task
        assignment_id = self.db.assign_task(
            task_id=task_id, agent_id=agent["agent_id"], assigned_by="VirtualTeamOrchestrator"
        )

        return {
            "task_id": task_id,
            "assignment_id": assignment_id,
            "assigned_to": agent["agent_name"],
            "agent_role": agent["agent_role"],
            "status": "assigned",
            "message": f"Task assigned to {agent['agent_name']}",
        }

    def delegate_to_specialist(
        self,
        task_name: str,
        specialist_role: str,
        description: str | None = None,
        context: dict | None = None,
        priority: str = "medium",
    ) -> dict:
        """Explicitly delegate task to specific role"""

        # Verify role exists
        if specialist_role not in self.AGENT_ROLES:
            return {
                "error": f"Unknown specialist role: {specialist_role}. Valid roles: {list(self.AGENT_ROLES.keys())}"
            }

        # Create task
        task_id = self.db.create_task(
            task_name=task_name,
            task_type=f"{specialist_role}_task",
            description=description,
            required_role=specialist_role,
            priority=priority,
            context_data=context,
            created_by="VirtualTeamOrchestrator",
        )

        # Find specialist agent
        agent = self.db.get_agent_by_role(specialist_role)

        if not agent:
            return {
                "task_id": task_id,
                "status": "pending",
                "message": f"No {specialist_role} agent available",
                "required_role": specialist_role,
            }

        # Assign
        assignment_id = self.db.assign_task(
            task_id=task_id, agent_id=agent["agent_id"], assigned_by="VirtualTeamOrchestrator"
        )

        return {
            "task_id": task_id,
            "assignment_id": assignment_id,
            "assigned_to": agent["agent_name"],
            "agent_role": agent["agent_role"],
            "status": "assigned",
        }

    # Workflow orchestration
    def start_workflow(
        self,
        workflow_name: str,
        workflow_type: str = "custom",
        customer_id: int | None = None,
        project_id: int | None = None,
        template: str | None = None,
        custom_tasks: list[dict] | None = None,
    ) -> dict:
        """Start multi-agent workflow"""

        # Use template or custom tasks
        if template and template in self.WORKFLOW_TEMPLATES:
            task_sequence = self.WORKFLOW_TEMPLATES[template]["tasks"]
        elif custom_tasks:
            task_sequence = custom_tasks
        else:
            return {"error": "Must provide either template name or custom_tasks"}

        # Create workflow
        workflow_id = self.db.create_workflow(
            workflow_name=workflow_name,
            workflow_type=workflow_type,
            task_sequence=task_sequence,
            customer_id=customer_id,
            project_id=project_id,
        )

        # Create and assign tasks
        created_tasks = []
        for idx, task_spec in enumerate(task_sequence):
            task_result = self.route_task(
                task_name=f"{workflow_name} - {task_spec['task_type']}",
                task_type=task_spec["task_type"],
                context={
                    "workflow_id": workflow_id,
                    "sequence_order": idx,
                    "parallel_group": task_spec.get("parallel_group"),
                },
            )

            if "task_id" in task_result:
                # Link task to workflow
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO workflow_tasks (workflow_id, task_id, sequence_order, parallel_group)
                    VALUES (?, ?, ?, ?)
                """,
                    (workflow_id, task_result["task_id"], idx, task_spec.get("parallel_group")),
                )
                conn.commit()
                conn.close()

                created_tasks.append(task_result)

        # Update workflow status
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE workflows SET status = 'in_progress', started_at = CURRENT_TIMESTAMP
            WHERE workflow_id = ?
        """,
            (workflow_id,),
        )
        conn.commit()
        conn.close()

        return {
            "workflow_id": workflow_id,
            "workflow_name": workflow_name,
            "tasks_created": len(created_tasks),
            "tasks": created_tasks,
            "status": "in_progress",
        }

    def get_workflow_progress(self, workflow_id: int) -> dict:
        """Get workflow progress and status"""
        return self.db.get_workflow_status(workflow_id)

    # Team coordination
    def coordinate_parallel_tasks(self, task_specs: list[dict]) -> dict:
        """Coordinate multiple tasks to run in parallel"""

        assignments = []
        for spec in task_specs:
            result = self.route_task(
                task_name=spec.get("task_name"),
                task_type=spec.get("task_type"),
                description=spec.get("description"),
                context=spec.get("context"),
                priority=spec.get("priority", "medium"),
            )
            assignments.append(result)

        return {"parallel_tasks": len(assignments), "assignments": assignments, "coordination_mode": "parallel"}

    def escalate_task(self, task_id: int, escalation_reason: str, target_role: str | None = None) -> dict:
        """Escalate task to different agent or higher tier"""

        task = self.db.get_task(task_id)
        if not task:
            return {"error": "Task not found"}

        # If no target role, escalate to architect
        if not target_role:
            target_role = "architect"

        # Find new agent
        new_agent = self.db.get_agent_by_role(target_role)
        if not new_agent:
            return {"error": f"No {target_role} agent available for escalation"}

        # Create new assignment
        assignment_id = self.db.assign_task(task_id=task_id, agent_id=new_agent["agent_id"], assigned_by="escalation")

        # Update priority
        self.db.update_task_status(task_id, "escalated")

        return {
            "task_id": task_id,
            "escalated_to": new_agent["agent_name"],
            "reason": escalation_reason,
            "new_assignment_id": assignment_id,
        }

    # Task monitoring
    def get_task_queue(self, role: str | None = None) -> dict:
        """Get pending tasks for a role or all roles"""

        pending = self.db.get_pending_tasks(role=role, limit=20)

        # Group by role
        by_role = {}
        for task in pending:
            required_role = task.get("required_role", "unassigned")
            if required_role not in by_role:
                by_role[required_role] = []
            by_role[required_role].append(task)

        return {"total_pending": len(pending), "by_role": by_role, "tasks": pending}

    def get_agent_workload(self, agent_id: int | None = None, role: str | None = None) -> dict:
        """Get current workload for agent or role"""

        conn = self.db.get_connection()
        cursor = conn.cursor()

        if agent_id:
            query = """
                SELECT t.status, COUNT(*)
                FROM task_assignments a
                JOIN tasks t ON a.task_id = t.task_id
                WHERE a.agent_id = ? AND a.status != 'completed'
                GROUP BY t.status
            """
            cursor.execute(query, (agent_id,))
        elif role:
            query = """
                SELECT t.status, COUNT(*)
                FROM task_assignments a
                JOIN tasks t ON a.task_id = t.task_id
                JOIN agents ag ON a.agent_id = ag.agent_id
                WHERE ag.agent_role = ? AND a.status != 'completed'
                GROUP BY t.status
            """
            cursor.execute(query, (role,))
        else:
            conn.close()
            return {"error": "Must provide agent_id or role"}

        workload = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        return {"agent_id": agent_id, "role": role, "workload": workload, "total_active_tasks": sum(workload.values())}

    # Analytics
    def get_team_dashboard(self) -> dict:
        """Get team-wide analytics dashboard"""

        team_metrics = self.db.get_team_metrics()

        # Get workload by role
        workload_by_role = {}
        for role in self.AGENT_ROLES:
            workload = self.get_agent_workload(role=role)
            if workload.get("total_active_tasks", 0) > 0:
                workload_by_role[role] = workload["total_active_tasks"]

        # Get pending queue
        queue = self.get_task_queue()

        return {
            **team_metrics,
            "workload_by_role": workload_by_role,
            "pending_queue_size": queue["total_pending"],
            "available_roles": list(self.AGENT_ROLES.keys()),
        }

    # Helper methods
    def _determine_required_role(self, task_type: str, context: dict | None = None) -> str | None:
        """Determine which agent role should handle task type"""

        # Task type to role mapping
        task_role_map = {
            "architecture_design": "architect",
            "system_design": "architect",
            "api_design": "architect",
            "backend_development": "developer",
            "frontend_development": "developer",
            "implementation": "developer",
            "code_review": "developer",
            "schema_design": "dba",
            "database_optimization": "dba",
            "migration_planning": "dba",
            "test_development": "qa",
            "testing": "qa",
            "quality_assurance": "qa",
            "deployment_setup": "devops",
            "ci_cd_setup": "devops",
            "infrastructure": "devops",
            "security_review": "security",
            "security_testing": "security",
            "threat_modeling": "security",
            "project_planning": "pm",
            "stakeholder_management": "pm",
        }

        return task_role_map.get(task_type)

    def get_available_workflows(self) -> list[str]:
        """Get list of available workflow templates"""
        return list(self.WORKFLOW_TEMPLATES.keys())

    def get_available_roles(self) -> dict:
        """Get all available agent roles with capabilities"""
        return self.AGENT_ROLES

    # Email Notification Methods
    async def send_task_assignment_notification(
        self, task_id: int, email_tool, stakeholder_email: str | None = None
    ) -> dict:
        """Send email notification for task assignment"""
        task = self.db.get_task(task_id)
        if not task:
            return {"error": "Task not found"}

        # Get agent details
        assigned_to = task.get("assigned_to")
        agent = self.db.get_agent(assigned_to) if assigned_to else None
        if not agent:
            return {"error": "Assigned agent not found"}

        # Build notification email
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}

        body = f"""<h2>New Task Assignment</h2>

<p><strong>Task:</strong> {task["task_name"]}</p>
<p><strong>Type:</strong> {task["task_type"].replace("_", " ").title()}</p>
<p><strong>Priority:</strong> {priority_emoji.get(task["priority"], "⚪")} {task["priority"].upper()}</p>
<p><strong>Status:</strong> {task["status"].replace("_", " ").title()}</p>
<p><strong>Assigned To:</strong> {agent["agent_role"].title()} Agent</p>

{f"<p><strong>Due Date:</strong> {task['due_date']}</p>" if task.get("due_date") else ""}

{f"<h3>Description</h3><p>{task['description']}</p>" if task.get("description") else ""}

{f"<h3>Requirements</h3><pre>{task['requirements']}</pre>" if task.get("requirements") else ""}

<p><em>This is an automated notification from Virtual Team Orchestrator.</em></p>"""

        # Determine recipient
        recipient = stakeholder_email or os.getenv("TEAM_NOTIFICATION_EMAIL") or os.getenv("GMAIL_FROM_EMAIL")

        if not recipient:
            return {"error": "No notification email configured"}

        result = await email_tool.execute(
            action="send",
            to=recipient,
            subject=f"Task Assignment: {task['task_name']} [{task['priority'].upper()}]",
            body=body,
            html=True,
            from_name="Virtual Team Orchestrator",
        )

        # Log notification
        self.db.log_team_activity(
            activity_type="notification",
            description=f"Task assignment notification sent: {task['task_name']}",
            metadata={"task_id": task_id, "recipient": recipient},
        )

        return result

    async def send_daily_digest(self, email_tool, recipient: str | None = None) -> dict:
        """Send daily digest of team activity and status"""
        # Get active projects
        projects = self.db.list_projects()
        active_projects = [p for p in projects if p["status"] == "active"]

        # Get task statistics
        all_tasks = []
        for project in active_projects:
            tasks = self.db.list_project_tasks(project["project_id"])
            all_tasks.extend(tasks)

        # Calculate statistics
        stats = {
            "total_tasks": len(all_tasks),
            "completed": len([t for t in all_tasks if t["status"] == "completed"]),
            "in_progress": len([t for t in all_tasks if t["status"] == "in_progress"]),
            "pending": len([t for t in all_tasks if t["status"] == "pending"]),
            "blocked": len([t for t in all_tasks if t["status"] == "blocked"]),
            "high_priority": len([t for t in all_tasks if t["priority"] == "high"]),
        }

        # Build digest email
        body = f"""<h2>Virtual Team Daily Digest</h2>
<p><em>{datetime.now().strftime("%A, %B %d, %Y")}</em></p>

<h3>📊 Overview</h3>
<ul>
  <li><strong>Active Projects:</strong> {len(active_projects)}</li>
  <li><strong>Total Tasks:</strong> {stats["total_tasks"]}</li>
  <li><strong>Completed Today:</strong> {stats["completed"]} ✅</li>
  <li><strong>In Progress:</strong> {stats["in_progress"]} 🔄</li>
  <li><strong>Pending:</strong> {stats["pending"]} ⏳</li>
  <li><strong>Blocked:</strong> {stats["blocked"]} 🚫</li>
  <li><strong>High Priority:</strong> {stats["high_priority"]} 🔴</li>
</ul>

<h3>🚀 Active Projects</h3>"""

        for project in active_projects[:5]:  # Top 5 projects
            project_tasks = [t for t in all_tasks if t.get("project_id") == project["project_id"]]
            body += f"""
<h4>{project["project_name"]}</h4>
<ul>
  <li>Status: {project["status"].replace("_", " ").title()}</li>
  <li>Tasks: {len(project_tasks)} total, {len([t for t in project_tasks if t["status"] == "completed"])} completed</li>
  <li>Team Size: {len(self.db.get_project_team(project["project_id"]))} agents</li>
</ul>"""

        # Top priority items
        high_priority_tasks = [t for t in all_tasks if t["priority"] == "high" and t["status"] != "completed"][:5]

        if high_priority_tasks:
            body += """
<h3>🔥 High Priority Items</h3>
<ol>"""
            for task in high_priority_tasks:
                body += f"""
  <li>{task["task_name"]} - {task["status"].replace("_", " ").title()}</li>"""

            body += """
</ol>"""

        body += """
<hr>
<p><em>This is an automated daily digest from Virtual Team Orchestrator.</em></p>"""

        # Determine recipient
        recipient = recipient or os.getenv("TEAM_NOTIFICATION_EMAIL") or os.getenv("GMAIL_FROM_EMAIL")

        if not recipient:
            return {"error": "No notification email configured"}

        result = await email_tool.execute(
            action="send",
            to=recipient,
            subject=f"Virtual Team Daily Digest - {datetime.now().strftime('%m/%d/%Y')}",
            body=body,
            html=True,
            from_name="Virtual Team Orchestrator",
        )

        # Log notification
        self.db.log_team_activity(
            activity_type="digest",
            description="Daily digest sent",
            metadata={"recipient": recipient, "projects": len(active_projects), "tasks": stats["total_tasks"]},
        )

        return result

    async def send_project_status_update(
        self, project_id: int, email_tool, recipients: list[str] | None = None
    ) -> dict:
        """Send project status update to stakeholders"""
        project = self.db.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        # Get project tasks and team
        tasks = self.db.list_project_tasks(project_id)
        team = self.db.get_project_team(project_id)

        # Calculate progress
        completed_tasks = len([t for t in tasks if t["status"] == "completed"])
        total_tasks = len(tasks)
        progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Build status update
        body = f"""<h2>Project Status Update</h2>

<h3>{project["project_name"]}</h3>
<p><strong>Status:</strong> {project["status"].replace("_", " ").title()}</p>
<p><strong>Progress:</strong> {progress:.1f}% ({completed_tasks}/{total_tasks} tasks completed)</p>

{f"<p><strong>Description:</strong> {project['description']}</p>" if project.get("description") else ""}

<h3>📈 Task Breakdown</h3>
<ul>
  <li>Completed: {len([t for t in tasks if t["status"] == "completed"])} ✅</li>
  <li>In Progress: {len([t for t in tasks if t["status"] == "in_progress"])} 🔄</li>
  <li>Pending: {len([t for t in tasks if t["status"] == "pending"])} ⏳</li>
  <li>Blocked: {len([t for t in tasks if t["status"] == "blocked"])} 🚫</li>
</ul>

<h3>👥 Team</h3>
<p>{len(team)} specialized agents assigned</p>

<hr>
<p><em>This is an automated project update from Virtual Team Orchestrator.</em></p>"""

        # Determine recipients
        if not recipients:
            recipients = [os.getenv("TEAM_NOTIFICATION_EMAIL") or os.getenv("GMAIL_FROM_EMAIL")]

        recipients = [r for r in recipients if r]  # Filter None values

        if not recipients:
            return {"error": "No recipients configured"}

        result = await email_tool.execute(
            action="send",
            to=recipients,
            subject=f"Project Update: {project['project_name']} - {progress:.0f}% Complete",
            body=body,
            html=True,
            from_name="Virtual Team Orchestrator",
        )

        # Log notification
        self.db.log_team_activity(
            activity_type="status_update",
            description=f"Project status update sent: {project['project_name']}",
            metadata={"project_id": project_id, "recipients": recipients, "progress": progress},
        )

        return result
