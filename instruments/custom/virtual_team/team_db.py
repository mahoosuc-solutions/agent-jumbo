"""
Virtual Team Orchestrator Database Schema
Manages AI agent teams, task delegation, and collaborative workflows
"""

import json
import sqlite3
from pathlib import Path
from typing import Any


class VirtualTeamDatabase:
    """Database for managing virtual team of specialized AI agents"""

    def __init__(self, db_path: str = "data/virtual_team.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """Initialize all tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Agent profiles/roles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT NOT NULL UNIQUE,
                agent_role TEXT NOT NULL,
                specialization TEXT,
                expertise_areas TEXT,
                tools_available TEXT,
                model_config TEXT,
                performance_tier TEXT DEFAULT 'standard',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Task queue
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT NOT NULL,
                task_type TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                complexity TEXT,
                required_role TEXT,
                required_expertise TEXT,
                context_data TEXT,
                input_artifacts TEXT,
                expected_outputs TEXT,
                dependencies TEXT,
                assigned_to INTEGER,
                due_date TEXT,
                requirements TEXT,
                customer_id INTEGER,
                project_id INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT
            )
        """)

        self._ensure_column(cursor, "tasks", "assigned_to", "INTEGER")
        self._ensure_column(cursor, "tasks", "due_date", "TEXT")
        self._ensure_column(cursor, "tasks", "requirements", "TEXT")

        # Task assignments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_assignments (
                assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                agent_id INTEGER NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                assigned_by TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status TEXT DEFAULT 'assigned',
                progress_percentage INTEGER DEFAULT 0,
                estimated_hours REAL,
                actual_hours REAL,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)

        # Task results/deliverables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                assignment_id INTEGER NOT NULL,
                result_type TEXT,
                output_data TEXT,
                output_artifacts TEXT,
                quality_score REAL,
                review_status TEXT DEFAULT 'pending',
                reviewer_agent_id INTEGER,
                review_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                FOREIGN KEY (assignment_id) REFERENCES task_assignments(assignment_id),
                FOREIGN KEY (reviewer_agent_id) REFERENCES agents(agent_id)
            )
        """)

        # Workflows (multi-task processes)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_name TEXT NOT NULL,
                workflow_type TEXT,
                description TEXT,
                task_sequence TEXT,
                customer_id INTEGER,
                project_id INTEGER,
                status TEXT DEFAULT 'planning',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Projects (portfolio management)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                description TEXT,
                workflow_template TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Workflow task relationships
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_tasks (
                workflow_task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                sequence_order INTEGER,
                is_parallel BOOLEAN DEFAULT 0,
                parallel_group INTEGER,
                FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id),
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            )
        """)

        # Agent collaboration sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS collaboration_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT,
                session_type TEXT,
                task_id INTEGER,
                workflow_id INTEGER,
                participating_agents TEXT,
                session_data TEXT,
                decisions_made TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id),
                FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
            )
        """)

        # Agent performance metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                metric_date DATE DEFAULT CURRENT_DATE,
                tasks_completed INTEGER DEFAULT 0,
                avg_quality_score REAL,
                avg_completion_time REAL,
                expertise_utilization REAL,
                collaboration_score REAL,
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)

        # Knowledge sharing/learnings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_knowledge (
                knowledge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_type TEXT,
                title TEXT NOT NULL,
                content TEXT,
                source_task_id INTEGER,
                source_agent_id INTEGER,
                tags TEXT,
                relevance_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_task_id) REFERENCES tasks(task_id),
                FOREIGN KEY (source_agent_id) REFERENCES agents(agent_id)
            )
        """)

        # Team activity log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_activity (
                activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_type TEXT NOT NULL,
                description TEXT,
                metadata TEXT,
                project_id INTEGER,
                task_id INTEGER,
                agent_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def _ensure_column(self, cursor, table: str, column: str, column_type: str):
        """Add a missing column to a table for lightweight migrations."""
        cursor.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cursor.fetchall()}
        if column not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    # Agent management
    def register_agent(
        self,
        agent_name: str,
        agent_role: str,
        specialization: str | None = None,
        expertise_areas: list[str] | None = None,
        tools_available: list[str] | None = None,
        performance_tier: str = "standard",
        metadata: dict | None = None,
    ) -> int:
        """Register new virtual agent"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO agents
            (agent_name, agent_role, specialization, expertise_areas,
             tools_available, performance_tier, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                agent_name,
                agent_role,
                specialization,
                json.dumps(expertise_areas) if expertise_areas else None,
                json.dumps(tools_available) if tools_available else None,
                performance_tier,
                json.dumps(metadata) if metadata else None,
            ),
        )

        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return agent_id

    def get_agent_by_role(self, role: str, specialization: str | None = None) -> dict | None:
        """Find agent by role and optional specialization"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if specialization:
            cursor.execute(
                """
                SELECT * FROM agents
                WHERE agent_role = ? AND specialization = ? AND status = 'active'
                LIMIT 1
            """,
                (role, specialization),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM agents
                WHERE agent_role = ? AND status = 'active'
                LIMIT 1
            """,
                (role,),
            )

        row = cursor.fetchone()
        conn.close()

        if row:
            cols = [desc[0] for desc in cursor.description]
            agent = dict(zip(cols, row))
            if agent.get("expertise_areas"):
                agent["expertise_areas"] = json.loads(agent["expertise_areas"])
            if agent.get("tools_available"):
                agent["tools_available"] = json.loads(agent["tools_available"])
            return agent
        return None

    def list_agents(self, role: str | None = None, status: str = "active") -> list[dict]:
        """List all agents with optional filters"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM agents WHERE status = ?"
        params = [status]

        if role:
            query += " AND agent_role = ?"
            params.append(role)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        conn.close()

        agents = []
        for row in rows:
            agent = dict(zip(cols, row))
            if agent.get("expertise_areas"):
                agent["expertise_areas"] = json.loads(agent["expertise_areas"])
            agents.append(agent)

        return agents

    # Task management
    def create_task(
        self,
        task_name: str,
        task_type: str,
        description: str | None = None,
        required_role: str | None = None,
        required_expertise: list[str] | None = None,
        priority: str = "medium",
        complexity: str | None = None,
        context_data: dict | None = None,
        customer_id: int | None = None,
        project_id: int | None = None,
        created_by: str | None = None,
        assigned_to: int | None = None,
        due_date: str | None = None,
        requirements: str | None = None,
    ) -> int:
        """Create new task"""
        conn = self.get_connection()
        cursor = conn.cursor()

        status = "assigned" if assigned_to else "pending"
        cursor.execute(
            """
            INSERT INTO tasks
            (task_name, task_type, description, required_role, required_expertise,
             priority, complexity, context_data, assigned_to, due_date, requirements,
             customer_id, project_id, status, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                task_name,
                task_type,
                description,
                required_role,
                json.dumps(required_expertise) if required_expertise else None,
                priority,
                complexity,
                json.dumps(context_data) if context_data else None,
                assigned_to,
                due_date,
                requirements,
                customer_id,
                project_id,
                status,
                created_by,
            ),
        )

        task_id = cursor.lastrowid

        if assigned_to:
            cursor.execute(
                """
                INSERT INTO task_assignments
                (task_id, agent_id, assigned_by, status)
                VALUES (?, ?, ?, ?)
            """,
                (task_id, assigned_to, created_by, "assigned"),
            )

        conn.commit()
        conn.close()
        return task_id

    def assign_task(
        self, task_id: int, agent_id: int, estimated_hours: float | None = None, assigned_by: str | None = None
    ) -> int:
        """Assign task to agent"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Update task status
        cursor.execute("UPDATE tasks SET status = 'assigned', assigned_to = ? WHERE task_id = ?", (agent_id, task_id))

        # Create assignment
        cursor.execute(
            """
            INSERT INTO task_assignments
            (task_id, agent_id, assigned_by, estimated_hours)
            VALUES (?, ?, ?, ?)
        """,
            (task_id, agent_id, assigned_by, estimated_hours),
        )

        assignment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return assignment_id

    def update_task_status(self, task_id: int, status: str, progress_percentage: int | None = None) -> bool:
        """Update task status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if progress_percentage is not None:
            cursor.execute(
                """
                UPDATE tasks SET status = ? WHERE task_id = ?
            """,
                (status, task_id),
            )

            cursor.execute(
                """
                UPDATE task_assignments
                SET status = ?, progress_percentage = ?
                WHERE task_id = ? AND status != 'completed'
            """,
                (status, progress_percentage, task_id),
            )
        else:
            cursor.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (status, task_id))

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_task(self, task_id: int) -> dict | None:
        """Get task details"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()

        if row:
            cols = [desc[0] for desc in cursor.description]
            task = dict(zip(cols, row))

            # Get assignment if exists
            cursor.execute(
                """
                SELECT a.*, ag.agent_name, ag.agent_role
                FROM task_assignments a
                JOIN agents ag ON a.agent_id = ag.agent_id
                WHERE a.task_id = ?
                ORDER BY a.assigned_at DESC LIMIT 1
            """,
                (task_id,),
            )

            assignment_row = cursor.fetchone()
            if assignment_row:
                assignment_cols = [desc[0] for desc in cursor.description]
                task["assignment"] = dict(zip(assignment_cols, assignment_row))
                if not task.get("assigned_to"):
                    task["assigned_to"] = task["assignment"].get("agent_id")

            conn.close()
            return task

        conn.close()
        return None

    # Project management
    def create_project(
        self,
        project_name: str,
        description: str | None = None,
        workflow_template: str | None = None,
        status: str = "active",
        metadata: dict | None = None,
    ) -> int:
        """Create a new project record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO projects
            (project_name, description, workflow_template, status, metadata)
            VALUES (?, ?, ?, ?, ?)
        """,
            (project_name, description, workflow_template, status, json.dumps(metadata) if metadata else None),
        )
        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return project_id

    def list_projects(self, status: str | None = None) -> list[dict]:
        """List projects with optional status filter"""
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM projects"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        conn.close()
        return [dict(zip(cols, row)) for row in rows]

    def get_project(self, project_id: int) -> dict | None:
        """Get project details"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        cols = [desc[0] for desc in cursor.description]
        project = dict(zip(cols, row))
        conn.close()
        return project

    def list_project_tasks(self, project_id: int) -> list[dict]:
        """List tasks for a project"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE project_id = ?", (project_id,))
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        conn.close()
        return [dict(zip(cols, row)) for row in rows]

    def get_project_team(self, project_id: int) -> list[dict]:
        """Get agents associated with tasks in a project"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT DISTINCT ag.*
            FROM task_assignments ta
            JOIN tasks t ON ta.task_id = t.task_id
            JOIN agents ag ON ta.agent_id = ag.agent_id
            WHERE t.project_id = ?
        """,
            (project_id,),
        )
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        conn.close()
        return [dict(zip(cols, row)) for row in rows]

    # Activity logging
    def log_team_activity(
        self,
        activity_type: str,
        description: str,
        metadata: dict | None = None,
        project_id: int | None = None,
        task_id: int | None = None,
        agent_id: int | None = None,
    ) -> int:
        """Log a team activity event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO team_activity
            (activity_type, description, metadata, project_id, task_id, agent_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (activity_type, description, json.dumps(metadata) if metadata else None, project_id, task_id, agent_id),
        )
        activity_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return activity_id

    def get_agent(self, agent_id: int) -> dict | None:
        """Get agent by id"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        cols = [desc[0] for desc in cursor.description]
        agent = dict(zip(cols, row))
        if agent.get("expertise_areas"):
            agent["expertise_areas"] = json.loads(agent["expertise_areas"])
        if agent.get("tools_available"):
            agent["tools_available"] = json.loads(agent["tools_available"])
        conn.close()
        return agent

    def get_pending_tasks(self, role: str | None = None, limit: int = 10) -> list[dict]:
        """Get pending tasks optionally filtered by required role"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM tasks WHERE status = 'pending'"
        params = []

        if role:
            query += " AND required_role = ?"
            params.append(role)

        query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        conn.close()

        return [dict(zip(cols, row)) for row in rows]

    # Workflow management
    def create_workflow(
        self,
        workflow_name: str,
        workflow_type: str,
        task_sequence: list[dict],
        customer_id: int | None = None,
        project_id: int | None = None,
        description: str | None = None,
    ) -> int:
        """Create workflow with task sequence"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO workflows
            (workflow_name, workflow_type, description, task_sequence,
             customer_id, project_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (workflow_name, workflow_type, description, json.dumps(task_sequence), customer_id, project_id),
        )

        workflow_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return workflow_id

    def get_workflow_status(self, workflow_id: int) -> dict:
        """Get workflow progress status"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM workflows WHERE workflow_id = ?", (workflow_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        cols = [desc[0] for desc in cursor.description]
        workflow = dict(zip(cols, row))

        # Get task statuses
        cursor.execute(
            """
            SELECT t.task_id, t.task_name, t.status, wt.sequence_order
            FROM workflow_tasks wt
            JOIN tasks t ON wt.task_id = t.task_id
            WHERE wt.workflow_id = ?
            ORDER BY wt.sequence_order
        """,
            (workflow_id,),
        )

        tasks = []
        for task_row in cursor.fetchall():
            task_cols = [desc[0] for desc in cursor.description]
            tasks.append(dict(zip(task_cols, task_row)))

        workflow["tasks"] = tasks

        # Calculate progress
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t["status"] == "completed")
        workflow["progress_percentage"] = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        conn.close()
        return workflow

    # Team analytics
    def get_team_metrics(self) -> dict:
        """Get overall team performance metrics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Active agents
        cursor.execute("SELECT COUNT(*) FROM agents WHERE status = 'active'")
        active_agents = cursor.fetchone()[0]

        # Task stats
        cursor.execute("""
            SELECT status, COUNT(*)
            FROM tasks
            GROUP BY status
        """)
        task_stats = {row[0]: row[1] for row in cursor.fetchall()}

        # Recent completions
        cursor.execute("""
            SELECT COUNT(*)
            FROM tasks
            WHERE status = 'completed'
            AND datetime(created_at) > datetime('now', '-7 days')
        """)
        recent_completions = cursor.fetchone()[0]

        conn.close()

        return {"active_agents": active_agents, "task_stats": task_stats, "recent_completions_7d": recent_completions}
