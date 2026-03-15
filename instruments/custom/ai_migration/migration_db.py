"""
AI Migration Database Layer
Stores business processes, tasks, workflows, and migration roadmaps
"""

import json
import sqlite3
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now


class MigrationDatabase:
    """SQLite database for AI migration workflow management"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Migration projects - top-level business assessment
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migration_projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                business_name TEXT NOT NULL,
                industry TEXT,
                company_size TEXT,
                current_tech_stack TEXT,
                pain_points TEXT,
                goals TEXT,
                budget_range TEXT,
                timeline TEXT,
                status TEXT DEFAULT 'assessment',
                assessment_score INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Business processes - individual processes to analyze
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_processes (
                process_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                department TEXT,
                owner TEXT,
                frequency TEXT,
                volume_per_period INTEGER,
                current_time_hours REAL,
                current_cost REAL,
                pain_points TEXT,
                dependencies TEXT,
                inputs TEXT,
                outputs TEXT,
                systems_used TEXT,
                automation_score INTEGER,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'documented',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES migration_projects(project_id)
            )
        """)

        # Process tasks - granular tasks within processes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                task_type TEXT,
                current_owner TEXT,
                time_minutes REAL,
                complexity TEXT,
                data_inputs TEXT,
                data_outputs TEXT,
                tools_used TEXT,
                decision_points TEXT,
                error_rate REAL,
                automation_score INTEGER,
                automation_category TEXT,
                proposed_owner TEXT,
                ai_tools_suggested TEXT,
                estimated_savings_minutes REAL,
                implementation_effort TEXT,
                sequence_order INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (process_id) REFERENCES business_processes(process_id)
            )
        """)

        # Optimized workflows - designed human-AI workflows
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS optimized_workflows (
                workflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                workflow_type TEXT,
                steps TEXT,
                human_touchpoints INTEGER,
                ai_touchpoints INTEGER,
                estimated_time_hours REAL,
                estimated_cost REAL,
                automation_percentage REAL,
                quality_impact TEXT,
                risk_level TEXT,
                implementation_phases TEXT,
                status TEXT DEFAULT 'designed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (process_id) REFERENCES business_processes(process_id)
            )
        """)

        # Migration roadmaps - implementation plans
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migration_roadmaps (
                roadmap_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                approach TEXT,
                phases TEXT,
                quick_wins TEXT,
                total_investment REAL,
                projected_savings_year1 REAL,
                projected_savings_year3 REAL,
                projected_savings_year5 REAL,
                payback_months INTEGER,
                roi_percentage REAL,
                risks TEXT,
                dependencies TEXT,
                success_metrics TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES migration_projects(project_id)
            )
        """)

        # ROI projections - detailed financial analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roi_projections (
                projection_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                roadmap_id INTEGER,
                scenario TEXT,
                assumptions TEXT,
                implementation_cost REAL,
                ongoing_cost_annual REAL,
                labor_savings_annual REAL,
                efficiency_gains_annual REAL,
                error_reduction_savings REAL,
                other_savings REAL,
                total_benefits_year1 REAL,
                total_benefits_year3 REAL,
                total_benefits_year5 REAL,
                net_present_value REAL,
                internal_rate_of_return REAL,
                payback_period_months INTEGER,
                confidence_level TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES migration_projects(project_id),
                FOREIGN KEY (roadmap_id) REFERENCES migration_roadmaps(roadmap_id)
            )
        """)

        # Quick wins - easy automation opportunities
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quick_wins (
                quick_win_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                current_state TEXT,
                proposed_solution TEXT,
                effort_days INTEGER,
                estimated_savings REAL,
                risk_level TEXT,
                prerequisites TEXT,
                status TEXT DEFAULT 'identified',
                priority_score INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES migration_projects(project_id),
                FOREIGN KEY (task_id) REFERENCES process_tasks(task_id)
            )
        """)

        conn.commit()
        conn.close()

    # ========== Migration Project Methods ==========

    def create_project(
        self, business_name: str, customer_id: int | None = None, industry: str | None = None, **kwargs
    ) -> int:
        """Create a new migration project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO migration_projects
            (business_name, customer_id, industry, company_size, current_tech_stack,
             pain_points, goals, budget_range, timeline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                business_name,
                customer_id,
                industry,
                kwargs.get("company_size"),
                json.dumps(kwargs.get("current_tech_stack", [])),
                json.dumps(kwargs.get("pain_points", [])),
                json.dumps(kwargs.get("goals", [])),
                kwargs.get("budget_range"),
                kwargs.get("timeline"),
            ),
        )

        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return project_id

    def get_project(self, project_id: int) -> dict | None:
        """Get project by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM migration_projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_projects(self, customer_id: int | None = None, status: str | None = None) -> list[dict]:
        """List migration projects"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM migration_projects WHERE 1=1"
        params = []

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def update_project(self, project_id: int, **kwargs) -> bool:
        """Update project fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ["status", "assessment_score", "industry", "company_size", "budget_range", "timeline"]:
                fields.append(f"{key} = ?")
                values.append(value)
            elif key in ["pain_points", "goals", "current_tech_stack"]:
                fields.append(f"{key} = ?")
                values.append(json.dumps(value))

        if not fields:
            return False

        fields.append("updated_at = ?")
        values.append(isoformat_z(utc_now()))
        values.append(project_id)

        cursor.execute(  # nosec B608 - controlled query construction
            f"""
            UPDATE migration_projects SET {", ".join(fields)} WHERE project_id = ?
        """,
            values,
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    # ========== Business Process Methods ==========

    def add_process(self, project_id: int, name: str, **kwargs) -> int:
        """Add a business process"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO business_processes
            (project_id, name, description, department, owner, frequency,
             volume_per_period, current_time_hours, current_cost, pain_points,
             dependencies, inputs, outputs, systems_used, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                project_id,
                name,
                kwargs.get("description"),
                kwargs.get("department"),
                kwargs.get("owner"),
                kwargs.get("frequency"),
                kwargs.get("volume_per_period"),
                kwargs.get("current_time_hours"),
                kwargs.get("current_cost"),
                json.dumps(kwargs.get("pain_points", [])),
                json.dumps(kwargs.get("dependencies", [])),
                json.dumps(kwargs.get("inputs", [])),
                json.dumps(kwargs.get("outputs", [])),
                json.dumps(kwargs.get("systems_used", [])),
                kwargs.get("priority", "medium"),
            ),
        )

        process_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return process_id

    def get_process(self, process_id: int) -> dict | None:
        """Get process by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM business_processes WHERE process_id = ?", (process_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_processes(self, project_id: int, status: str | None = None) -> list[dict]:
        """List processes for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM business_processes WHERE project_id = ?"
        params = [project_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY priority DESC, name"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def update_process(self, process_id: int, **kwargs) -> bool:
        """Update process fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        fields = []
        values = []
        simple_fields = [
            "name",
            "description",
            "department",
            "owner",
            "frequency",
            "volume_per_period",
            "current_time_hours",
            "current_cost",
            "automation_score",
            "priority",
            "status",
        ]
        json_fields = ["pain_points", "dependencies", "inputs", "outputs", "systems_used"]

        for key, value in kwargs.items():
            if key in simple_fields:
                fields.append(f"{key} = ?")
                values.append(value)
            elif key in json_fields:
                fields.append(f"{key} = ?")
                values.append(json.dumps(value))

        if not fields:
            return False

        values.append(process_id)
        cursor.execute(  # nosec B608 - controlled query construction
            f"""
            UPDATE business_processes SET {", ".join(fields)} WHERE process_id = ?
        """,
            values,
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    # ========== Process Task Methods ==========

    def add_task(self, process_id: int, name: str, **kwargs) -> int:
        """Add a task to a process"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO process_tasks
            (process_id, name, description, task_type, current_owner, time_minutes,
             complexity, data_inputs, data_outputs, tools_used, decision_points,
             error_rate, sequence_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                process_id,
                name,
                kwargs.get("description"),
                kwargs.get("task_type"),
                kwargs.get("current_owner"),
                kwargs.get("time_minutes"),
                kwargs.get("complexity", "medium"),
                json.dumps(kwargs.get("data_inputs", [])),
                json.dumps(kwargs.get("data_outputs", [])),
                json.dumps(kwargs.get("tools_used", [])),
                json.dumps(kwargs.get("decision_points", [])),
                kwargs.get("error_rate"),
                kwargs.get("sequence_order", 0),
            ),
        )

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id

    def get_task(self, task_id: int) -> dict | None:
        """Get task by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM process_tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_tasks(self, process_id: int) -> list[dict]:
        """List tasks for a process"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM process_tasks WHERE process_id = ?
            ORDER BY sequence_order, task_id
        """,
            (process_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def update_task(self, task_id: int, **kwargs) -> bool:
        """Update task fields including automation analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        fields = []
        values = []
        simple_fields = [
            "name",
            "description",
            "task_type",
            "current_owner",
            "time_minutes",
            "complexity",
            "error_rate",
            "automation_score",
            "automation_category",
            "proposed_owner",
            "estimated_savings_minutes",
            "implementation_effort",
            "sequence_order",
        ]
        json_fields = ["data_inputs", "data_outputs", "tools_used", "decision_points", "ai_tools_suggested"]

        for key, value in kwargs.items():
            if key in simple_fields:
                fields.append(f"{key} = ?")
                values.append(value)
            elif key in json_fields:
                fields.append(f"{key} = ?")
                values.append(json.dumps(value))

        if not fields:
            return False

        values.append(task_id)
        cursor.execute(  # nosec B608 - controlled query construction
            f"""
            UPDATE process_tasks SET {", ".join(fields)} WHERE task_id = ?
        """,
            values,
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    # ========== Workflow Methods ==========

    def add_workflow(self, process_id: int, name: str, steps: list[dict], **kwargs) -> int:
        """Add an optimized workflow design"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO optimized_workflows
            (process_id, name, description, workflow_type, steps, human_touchpoints,
             ai_touchpoints, estimated_time_hours, estimated_cost,
             automation_percentage, quality_impact, risk_level, implementation_phases)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                process_id,
                name,
                kwargs.get("description"),
                kwargs.get("workflow_type", "hybrid"),
                json.dumps(steps),
                kwargs.get("human_touchpoints", 0),
                kwargs.get("ai_touchpoints", 0),
                kwargs.get("estimated_time_hours"),
                kwargs.get("estimated_cost"),
                kwargs.get("automation_percentage"),
                kwargs.get("quality_impact"),
                kwargs.get("risk_level", "medium"),
                json.dumps(kwargs.get("implementation_phases", [])),
            ),
        )

        workflow_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return workflow_id

    def get_workflow(self, workflow_id: int) -> dict | None:
        """Get workflow by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM optimized_workflows WHERE workflow_id = ?", (workflow_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_workflows(self, process_id: int | None = None, project_id: int | None = None) -> list[dict]:
        """List workflows"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if process_id:
            cursor.execute(
                """
                SELECT * FROM optimized_workflows WHERE process_id = ?
            """,
                (process_id,),
            )
        elif project_id:
            cursor.execute(
                """
                SELECT w.* FROM optimized_workflows w
                JOIN business_processes p ON w.process_id = p.process_id
                WHERE p.project_id = ?
            """,
                (project_id,),
            )
        else:
            cursor.execute("SELECT * FROM optimized_workflows")

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    # ========== Roadmap Methods ==========

    def add_roadmap(self, project_id: int, name: str, phases: list[dict], **kwargs) -> int:
        """Add a migration roadmap"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO migration_roadmaps
            (project_id, name, approach, phases, quick_wins, total_investment,
             projected_savings_year1, projected_savings_year3, projected_savings_year5,
             payback_months, roi_percentage, risks, dependencies, success_metrics)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                project_id,
                name,
                kwargs.get("approach"),
                json.dumps(phases),
                json.dumps(kwargs.get("quick_wins", [])),
                kwargs.get("total_investment"),
                kwargs.get("projected_savings_year1"),
                kwargs.get("projected_savings_year3"),
                kwargs.get("projected_savings_year5"),
                kwargs.get("payback_months"),
                kwargs.get("roi_percentage"),
                json.dumps(kwargs.get("risks", [])),
                json.dumps(kwargs.get("dependencies", [])),
                json.dumps(kwargs.get("success_metrics", [])),
            ),
        )

        roadmap_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return roadmap_id

    def get_roadmap(self, roadmap_id: int) -> dict | None:
        """Get roadmap by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM migration_roadmaps WHERE roadmap_id = ?", (roadmap_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_roadmaps(self, project_id: int) -> list[dict]:
        """List roadmaps for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM migration_roadmaps WHERE project_id = ?
            ORDER BY created_at DESC
        """,
            (project_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    # ========== ROI Projection Methods ==========

    def add_roi_projection(self, project_id: int, scenario: str, **kwargs) -> int:
        """Add ROI projection"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO roi_projections
            (project_id, roadmap_id, scenario, assumptions, implementation_cost,
             ongoing_cost_annual, labor_savings_annual, efficiency_gains_annual,
             error_reduction_savings, other_savings, total_benefits_year1,
             total_benefits_year3, total_benefits_year5, net_present_value,
             internal_rate_of_return, payback_period_months, confidence_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                project_id,
                kwargs.get("roadmap_id"),
                scenario,
                json.dumps(kwargs.get("assumptions", {})),
                kwargs.get("implementation_cost"),
                kwargs.get("ongoing_cost_annual"),
                kwargs.get("labor_savings_annual"),
                kwargs.get("efficiency_gains_annual"),
                kwargs.get("error_reduction_savings"),
                kwargs.get("other_savings"),
                kwargs.get("total_benefits_year1"),
                kwargs.get("total_benefits_year3"),
                kwargs.get("total_benefits_year5"),
                kwargs.get("net_present_value"),
                kwargs.get("internal_rate_of_return"),
                kwargs.get("payback_period_months"),
                kwargs.get("confidence_level", "medium"),
            ),
        )

        projection_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return projection_id

    def list_roi_projections(self, project_id: int) -> list[dict]:
        """List ROI projections for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM roi_projections WHERE project_id = ?
            ORDER BY scenario
        """,
            (project_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    # ========== Quick Wins Methods ==========

    def add_quick_win(self, project_id: int, name: str, **kwargs) -> int:
        """Add a quick win opportunity"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO quick_wins
            (project_id, task_id, name, description, current_state, proposed_solution,
             effort_days, estimated_savings, risk_level, prerequisites, priority_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                project_id,
                kwargs.get("task_id"),
                name,
                kwargs.get("description"),
                kwargs.get("current_state"),
                kwargs.get("proposed_solution"),
                kwargs.get("effort_days"),
                kwargs.get("estimated_savings"),
                kwargs.get("risk_level", "low"),
                json.dumps(kwargs.get("prerequisites", [])),
                kwargs.get("priority_score"),
            ),
        )

        quick_win_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return quick_win_id

    def list_quick_wins(self, project_id: int, status: str | None = None) -> list[dict]:
        """List quick wins for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM quick_wins WHERE project_id = ?"
        params = [project_id]

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY priority_score DESC, effort_days ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row) -> dict:
        """Convert database row to dictionary"""
        result = dict(row)
        json_fields = [
            "pain_points",
            "goals",
            "current_tech_stack",
            "dependencies",
            "inputs",
            "outputs",
            "systems_used",
            "data_inputs",
            "data_outputs",
            "tools_used",
            "decision_points",
            "ai_tools_suggested",
            "steps",
            "implementation_phases",
            "phases",
            "quick_wins",
            "risks",
            "success_metrics",
            "assumptions",
            "prerequisites",
        ]

        for field in json_fields:
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except (json.JSONDecodeError, TypeError):
                    pass

        return result
