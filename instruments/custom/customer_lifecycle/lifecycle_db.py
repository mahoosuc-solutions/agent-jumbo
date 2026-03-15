"""
Customer Lifecycle Database Schema
Manages end-to-end customer journey from lead to delivery to support
"""

import json
import sqlite3
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now


class CustomerLifecycleDatabase:
    """Database for managing customer lifecycle stages"""

    def __init__(self, db_path: str = "data/customer_lifecycle.db"):
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

        # Customers/Leads table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                company TEXT,
                email TEXT,
                phone TEXT,
                industry TEXT,
                company_size TEXT,
                stage TEXT DEFAULT 'lead',
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Requirements gathering sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requirements (
                requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                session_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                interviewer TEXT,
                raw_transcript TEXT,
                structured_requirements TEXT,
                pain_points TEXT,
                success_criteria TEXT,
                constraints TEXT,
                timeline_expectations TEXT,
                budget_range TEXT,
                status TEXT DEFAULT 'draft',
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """)

        # Solution designs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solutions (
                solution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                requirement_id INTEGER,
                solution_name TEXT NOT NULL,
                architecture_type TEXT,
                tech_stack TEXT,
                architecture_diagram_path TEXT,
                components TEXT,
                integrations TEXT,
                estimated_complexity TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                status TEXT DEFAULT 'draft',
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id)
            )
        """)

        # Proposals
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS proposals (
                proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                solution_id INTEGER,
                proposal_number TEXT UNIQUE,
                title TEXT NOT NULL,
                executive_summary TEXT,
                scope_of_work TEXT,
                deliverables TEXT,
                timeline_weeks INTEGER,
                milestones TEXT,
                pricing_model TEXT,
                total_cost REAL,
                payment_terms TEXT,
                assumptions TEXT,
                exclusions TEXT,
                valid_until DATE,
                status TEXT DEFAULT 'draft',
                sent_date TIMESTAMP,
                accepted_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (solution_id) REFERENCES solutions(solution_id)
            )
        """)

        # Contracts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                proposal_id INTEGER,
                contract_number TEXT UNIQUE,
                contract_type TEXT,
                start_date DATE,
                end_date DATE,
                renewal_terms TEXT,
                total_value REAL,
                payment_schedule TEXT,
                sla_terms TEXT,
                support_level TEXT,
                status TEXT DEFAULT 'active',
                signed_date TIMESTAMP,
                document_path TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (proposal_id) REFERENCES proposals(proposal_id)
            )
        """)

        # Projects (links to portfolio)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                contract_id INTEGER,
                portfolio_project_id INTEGER,
                project_name TEXT NOT NULL,
                project_type TEXT,
                start_date DATE,
                target_date DATE,
                completed_date DATE,
                status TEXT DEFAULT 'planning',
                health_status TEXT DEFAULT 'green',
                current_phase TEXT,
                completion_percentage INTEGER DEFAULT 0,
                team_assigned TEXT,
                repository_url TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
            )
        """)

        # Support tickets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                contract_id INTEGER,
                ticket_number TEXT UNIQUE,
                subject TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'medium',
                category TEXT,
                status TEXT DEFAULT 'open',
                assigned_to TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                resolution TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
            )
        """)

        # Customer interactions/touchpoints
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                interaction_type TEXT,
                interaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subject TEXT,
                notes TEXT,
                sentiment TEXT,
                next_steps TEXT,
                follow_up_date DATE,
                recorded_by TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            )
        """)

        conn.commit()
        conn.close()

    # Customer management
    def add_customer(
        self,
        name: str,
        company: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        industry: str | None = None,
        company_size: str | None = None,
        source: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Add new customer/lead"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO customers (name, company, email, phone, industry, company_size, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (name, company, email, phone, industry, company_size, source, json.dumps(metadata) if metadata else None),
        )

        customer_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return customer_id

    def update_customer_stage(self, customer_id: int, stage: str) -> bool:
        """Update customer lifecycle stage (lead, prospect, customer, churned)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE customers
            SET stage = ?, updated_at = CURRENT_TIMESTAMP
            WHERE customer_id = ?
        """,
            (stage, customer_id),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_customer(self, customer_id: int) -> dict | None:
        """Get customer details"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            cols = [desc[0] for desc in cursor.description]
            customer = dict(zip(cols, row))
            if customer.get("metadata"):
                customer["metadata"] = json.loads(customer["metadata"])
            return customer
        return None

    # Requirements management
    def add_requirements(
        self,
        customer_id: int,
        raw_transcript: str | None = None,
        structured_requirements: str | None = None,
        pain_points: str | None = None,
        success_criteria: str | None = None,
        constraints: str | None = None,
        timeline_expectations: str | None = None,
        budget_range: str | None = None,
        interviewer: str | None = None,
    ) -> int:
        """Record requirements gathering session"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO requirements
            (customer_id, interviewer, raw_transcript, structured_requirements,
             pain_points, success_criteria, constraints, timeline_expectations, budget_range)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                customer_id,
                interviewer,
                raw_transcript,
                structured_requirements,
                pain_points,
                success_criteria,
                constraints,
                timeline_expectations,
                budget_range,
            ),
        )

        req_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return req_id

    def get_customer_requirements(self, customer_id: int) -> list[dict]:
        """Get all requirements for a customer"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM requirements
            WHERE customer_id = ?
            ORDER BY session_date DESC
        """,
            (customer_id,),
        )

        rows = cursor.fetchall()
        cols = [desc[0] for desc in cursor.description]
        conn.close()

        return [dict(zip(cols, row)) for row in rows]

    # Solution design
    def add_solution(
        self,
        customer_id: int,
        solution_name: str,
        architecture_type: str | None = None,
        tech_stack: list[str] | None = None,
        components: list[str] | None = None,
        requirement_id: int | None = None,
        created_by: str | None = None,
    ) -> int:
        """Create solution design"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO solutions
            (customer_id, requirement_id, solution_name, architecture_type,
             tech_stack, components, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                customer_id,
                requirement_id,
                solution_name,
                architecture_type,
                json.dumps(tech_stack) if tech_stack else None,
                json.dumps(components) if components else None,
                created_by,
            ),
        )

        solution_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return solution_id

    # Proposal generation
    def create_proposal(
        self,
        customer_id: int,
        title: str,
        solution_id: int | None = None,
        scope_of_work: str | None = None,
        deliverables: list[str] | None = None,
        timeline_weeks: int | None = None,
        total_cost: float | None = None,
        pricing_model: str | None = None,
        valid_until: str | None = None,
    ) -> int:
        """Create customer proposal"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Generate proposal number
        cursor.execute("SELECT COUNT(*) FROM proposals WHERE customer_id = ?", (customer_id,))
        count = cursor.fetchone()[0]
        proposal_number = f"PROP-{customer_id:04d}-{count + 1:03d}"

        cursor.execute(
            """
            INSERT INTO proposals
            (customer_id, solution_id, proposal_number, title, scope_of_work,
             deliverables, timeline_weeks, total_cost, pricing_model, valid_until)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                customer_id,
                solution_id,
                proposal_number,
                title,
                scope_of_work,
                json.dumps(deliverables) if deliverables else None,
                timeline_weeks,
                total_cost,
                pricing_model,
                valid_until,
            ),
        )

        proposal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return proposal_id

    def update_proposal_status(self, proposal_id: int, status: str) -> bool:
        """Update proposal status (draft, sent, accepted, rejected)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        update_fields = {"status": status}
        if status == "sent":
            update_fields["sent_date"] = isoformat_z(utc_now())
        elif status == "accepted":
            update_fields["accepted_date"] = isoformat_z(utc_now())

        set_clause = ", ".join([f"{k} = ?" for k in update_fields])
        values = [*list(update_fields.values()), proposal_id]

        cursor.execute(f"UPDATE proposals SET {set_clause} WHERE proposal_id = ?", values)  # nosec B608 - controlled query construction

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    # Customer lifecycle analytics
    def get_pipeline_summary(self) -> dict:
        """Get sales pipeline summary"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                stage,
                COUNT(*) as count,
                COUNT(CASE WHEN company IS NOT NULL THEN 1 END) as companies
            FROM customers
            GROUP BY stage
        """)

        stages = {}
        for row in cursor.fetchall():
            stages[row[0]] = {"count": row[1], "companies": row[2]}

        cursor.execute("""
            SELECT
                status,
                COUNT(*) as count,
                SUM(total_cost) as total_value
            FROM proposals
            GROUP BY status
        """)

        proposals = {}
        for row in cursor.fetchall():
            proposals[row[0]] = {"count": row[1], "total_value": row[2] or 0}

        conn.close()

        return {"customers_by_stage": stages, "proposals_by_status": proposals}

    def get_customer_360(self, customer_id: int) -> dict:
        """Get complete customer view"""
        customer = self.get_customer(customer_id)
        if not customer:
            return None

        conn = self.get_connection()
        cursor = conn.cursor()

        # Get requirements
        cursor.execute("SELECT COUNT(*) FROM requirements WHERE customer_id = ?", (customer_id,))
        requirements_count = cursor.fetchone()[0]

        # Get solutions
        cursor.execute("SELECT COUNT(*) FROM solutions WHERE customer_id = ?", (customer_id,))
        solutions_count = cursor.fetchone()[0]

        # Get proposals
        cursor.execute(
            """
            SELECT status, COUNT(*), SUM(total_cost)
            FROM proposals
            WHERE customer_id = ?
            GROUP BY status
        """,
            (customer_id,),
        )
        proposals = {row[0]: {"count": row[1], "value": row[2]} for row in cursor.fetchall()}

        # Get active projects
        cursor.execute(
            """
            SELECT COUNT(*), AVG(completion_percentage)
            FROM customer_projects
            WHERE customer_id = ? AND status != 'completed'
        """,
            (customer_id,),
        )
        project_data = cursor.fetchone()

        # Get open tickets
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM support_tickets
            WHERE customer_id = ? AND status != 'closed'
        """,
            (customer_id,),
        )
        open_tickets = cursor.fetchone()[0]

        conn.close()

        return {
            **customer,
            "requirements_sessions": requirements_count,
            "solutions_designed": solutions_count,
            "proposals": proposals,
            "active_projects": project_data[0] if project_data else 0,
            "avg_project_completion": project_data[1] if project_data else 0,
            "open_support_tickets": open_tickets,
        }
