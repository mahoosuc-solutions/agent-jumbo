"""
Database module for Sales Generator tool
Stores proposals, demos, ROI calculations, and case studies
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now


class SalesGeneratorDatabase:
    """SQLite database for sales materials storage"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """Get a connection with WAL mode and busy timeout"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        """Initialize database schema"""
        with self._connect() as conn:
            conn.executescript("""
                -- Proposals
                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    customer_name TEXT,
                    title TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    solution_summary TEXT,
                    pricing_total REAL,
                    valid_until TEXT,
                    content TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Proposal line items
                CREATE TABLE IF NOT EXISTS proposal_items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    quantity INTEGER DEFAULT 1,
                    unit_price REAL,
                    total_price REAL,
                    item_type TEXT DEFAULT 'service',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (proposal_id) REFERENCES proposals(proposal_id)
                );

                -- Demos
                CREATE TABLE IF NOT EXISTS demos (
                    demo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    customer_name TEXT,
                    title TEXT NOT NULL,
                    demo_type TEXT DEFAULT 'interactive',
                    status TEXT DEFAULT 'draft',
                    content TEXT,
                    features TEXT DEFAULT '[]',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- ROI Calculations
                CREATE TABLE IF NOT EXISTS roi_calculations (
                    roi_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    customer_name TEXT,
                    title TEXT NOT NULL,
                    current_costs TEXT DEFAULT '{}',
                    projected_savings TEXT DEFAULT '{}',
                    implementation_costs TEXT DEFAULT '{}',
                    payback_months INTEGER,
                    roi_percentage REAL,
                    npv REAL,
                    projections TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Case Studies
                CREATE TABLE IF NOT EXISTS case_studies (
                    case_study_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    customer_name TEXT,
                    project_name TEXT NOT NULL,
                    industry TEXT,
                    challenge TEXT,
                    solution TEXT,
                    results TEXT,
                    metrics TEXT DEFAULT '{}',
                    testimonial TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Portfolio Showcases
                CREATE TABLE IF NOT EXISTS showcases (
                    showcase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    projects TEXT DEFAULT '[]',
                    target_industry TEXT,
                    content TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Business Cases
                CREATE TABLE IF NOT EXISTS business_cases (
                    case_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    customer_name TEXT,
                    title TEXT NOT NULL,
                    executive_summary TEXT,
                    problem_statement TEXT,
                    proposed_solution TEXT,
                    benefits TEXT DEFAULT '[]',
                    risks TEXT DEFAULT '[]',
                    timeline TEXT,
                    investment_required REAL,
                    roi_analysis TEXT DEFAULT '{}',
                    recommendation TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Comparisons
                CREATE TABLE IF NOT EXISTS comparisons (
                    comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    our_solution TEXT NOT NULL,
                    competitors TEXT DEFAULT '[]',
                    criteria TEXT DEFAULT '[]',
                    analysis TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_proposals_customer ON proposals(customer_id);
                CREATE INDEX IF NOT EXISTS idx_demos_customer ON demos(customer_id);
                CREATE INDEX IF NOT EXISTS idx_roi_customer ON roi_calculations(customer_id);
                CREATE INDEX IF NOT EXISTS idx_case_studies_customer ON case_studies(customer_id);
            """)

    # ========== Proposal Operations ==========

    def create_proposal(
        self,
        title: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        solution_summary: str | None = None,
        valid_days: int = 30,
        metadata: dict | None = None,
    ) -> int:
        """Create a new proposal"""
        valid_until = (datetime.now() + timedelta(days=valid_days)).isoformat()

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO proposals
                (customer_id, customer_name, title, solution_summary, valid_until, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (customer_id, customer_name, title, solution_summary, valid_until, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def add_proposal_item(
        self,
        proposal_id: int,
        name: str,
        description: str | None = None,
        quantity: int = 1,
        unit_price: float = 0,
        item_type: str = "service",
    ) -> int:
        """Add line item to proposal"""
        total_price = quantity * unit_price
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO proposal_items
                (proposal_id, name, description, quantity, unit_price, total_price, item_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (proposal_id, name, description, quantity, unit_price, total_price, item_type),
            )

            # Update proposal total
            conn.execute(
                """
                UPDATE proposals SET pricing_total = (
                    SELECT SUM(total_price) FROM proposal_items WHERE proposal_id = ?
                ), updated_at = ? WHERE proposal_id = ?
            """,
                (proposal_id, isoformat_z(utc_now()), proposal_id),
            )

            return cursor.lastrowid

    def get_proposal(self, proposal_id: int) -> dict:
        """Get proposal with line items"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM proposals WHERE proposal_id = ?", (proposal_id,)).fetchone()

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))

                # Get line items
                items = conn.execute(
                    "SELECT * FROM proposal_items WHERE proposal_id = ? ORDER BY item_id", (proposal_id,)
                ).fetchall()
                result["items"] = [dict(i) for i in items]

                return result
            return None

    def list_proposals(self, customer_id: int | None = None, status: str | None = None) -> list:
        """List proposals with optional filters"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM proposals WHERE 1=1"
            params = []

            if customer_id:
                query += " AND customer_id = ?"
                params.append(customer_id)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def update_proposal_status(self, proposal_id: int, status: str):
        """Update proposal status"""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE proposals SET status = ?, updated_at = ?
                WHERE proposal_id = ?
            """,
                (status, isoformat_z(utc_now()), proposal_id),
            )

    def update_proposal_content(self, proposal_id: int, content: str):
        """Update proposal content"""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE proposals SET content = ?, updated_at = ?
                WHERE proposal_id = ?
            """,
                (content, isoformat_z(utc_now()), proposal_id),
            )

    # ========== Demo Operations ==========

    def create_demo(
        self,
        title: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        demo_type: str = "interactive",
        features: list | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Create a new demo"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO demos
                (customer_id, customer_name, title, demo_type, features, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (customer_id, customer_name, title, demo_type, json.dumps(features or []), json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_demo(self, demo_id: int) -> dict:
        """Get demo by ID"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM demos WHERE demo_id = ?", (demo_id,)).fetchone()

            if row:
                result = dict(row)
                result["features"] = json.loads(result.get("features", "[]"))
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def update_demo_content(self, demo_id: int, content: str):
        """Update demo content"""
        with self._connect() as conn:
            conn.execute("UPDATE demos SET content = ? WHERE demo_id = ?", (content, demo_id))

    def list_demos(self, customer_id: int | None = None) -> list:
        """List demos"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if customer_id:
                rows = conn.execute(
                    "SELECT * FROM demos WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM demos ORDER BY created_at DESC").fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["features"] = json.loads(r.get("features", "[]"))
                results.append(r)
            return results

    # ========== ROI Operations ==========

    def create_roi_calculation(
        self,
        title: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        current_costs: dict | None = None,
        projected_savings: dict | None = None,
        implementation_costs: dict | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Create ROI calculation"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO roi_calculations
                (customer_id, customer_name, title, current_costs, projected_savings,
                 implementation_costs, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    customer_id,
                    customer_name,
                    title,
                    json.dumps(current_costs or {}),
                    json.dumps(projected_savings or {}),
                    json.dumps(implementation_costs or {}),
                    json.dumps(metadata or {}),
                ),
            )
            return cursor.lastrowid

    def update_roi_results(
        self, roi_id: int, payback_months: int, roi_percentage: float, npv: float, projections: dict
    ):
        """Update ROI calculation results"""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE roi_calculations SET
                payback_months = ?, roi_percentage = ?, npv = ?, projections = ?
                WHERE roi_id = ?
            """,
                (payback_months, roi_percentage, npv, json.dumps(projections), roi_id),
            )

    def get_roi_calculation(self, roi_id: int) -> dict:
        """Get ROI calculation"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM roi_calculations WHERE roi_id = ?", (roi_id,)).fetchone()

            if row:
                result = dict(row)
                result["current_costs"] = json.loads(result.get("current_costs", "{}"))
                result["projected_savings"] = json.loads(result.get("projected_savings", "{}"))
                result["implementation_costs"] = json.loads(result.get("implementation_costs", "{}"))
                result["projections"] = json.loads(result.get("projections", "{}"))
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def list_roi_calculations(self, customer_id: int | None = None) -> list:
        """List ROI calculations"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if customer_id:
                rows = conn.execute(
                    "SELECT * FROM roi_calculations WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM roi_calculations ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    # ========== Case Study Operations ==========

    def create_case_study(
        self,
        project_name: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        industry: str | None = None,
        challenge: str | None = None,
        solution: str | None = None,
        results: str | None = None,
        metrics: dict | None = None,
        testimonial: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Create case study"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO case_studies
                (customer_id, customer_name, project_name, industry, challenge,
                 solution, results, metrics, testimonial, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    customer_id,
                    customer_name,
                    project_name,
                    industry,
                    challenge,
                    solution,
                    results,
                    json.dumps(metrics or {}),
                    testimonial,
                    json.dumps(metadata or {}),
                ),
            )
            return cursor.lastrowid

    def get_case_study(self, case_study_id: int) -> dict:
        """Get case study"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM case_studies WHERE case_study_id = ?", (case_study_id,)).fetchone()

            if row:
                result = dict(row)
                result["metrics"] = json.loads(result.get("metrics", "{}"))
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def list_case_studies(self, industry: str | None = None, status: str | None = None) -> list:
        """List case studies"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM case_studies WHERE 1=1"
            params = []

            if industry:
                query += " AND industry = ?"
                params.append(industry)
            if status:
                query += " AND status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["metrics"] = json.loads(r.get("metrics", "{}"))
                results.append(r)
            return results

    # ========== Business Case Operations ==========

    def create_business_case(
        self,
        title: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        executive_summary: str | None = None,
        problem_statement: str | None = None,
        proposed_solution: str | None = None,
        benefits: list | None = None,
        risks: list | None = None,
        timeline: str | None = None,
        investment_required: float | None = None,
        recommendation: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Create business case"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO business_cases
                (customer_id, customer_name, title, executive_summary, problem_statement,
                 proposed_solution, benefits, risks, timeline, investment_required,
                 recommendation, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    customer_id,
                    customer_name,
                    title,
                    executive_summary,
                    problem_statement,
                    proposed_solution,
                    json.dumps(benefits or []),
                    json.dumps(risks or []),
                    timeline,
                    investment_required,
                    recommendation,
                    json.dumps(metadata or {}),
                ),
            )
            return cursor.lastrowid

    def get_business_case(self, case_id: int) -> dict:
        """Get business case"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM business_cases WHERE case_id = ?", (case_id,)).fetchone()

            if row:
                result = dict(row)
                result["benefits"] = json.loads(result.get("benefits", "[]"))
                result["risks"] = json.loads(result.get("risks", "[]"))
                result["roi_analysis"] = json.loads(result.get("roi_analysis", "{}"))
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def list_business_cases(self, customer_id: int | None = None) -> list:
        """List business cases"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if customer_id:
                rows = conn.execute(
                    "SELECT * FROM business_cases WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM business_cases ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    # ========== Showcase Operations ==========

    def create_showcase(
        self,
        title: str,
        description: str | None = None,
        projects: list | None = None,
        target_industry: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Create portfolio showcase"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO showcases
                (title, description, projects, target_industry, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (title, description, json.dumps(projects or []), target_industry, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_showcase(self, showcase_id: int) -> dict:
        """Get showcase"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM showcases WHERE showcase_id = ?", (showcase_id,)).fetchone()

            if row:
                result = dict(row)
                result["projects"] = json.loads(result.get("projects", "[]"))
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def update_showcase_content(self, showcase_id: int, content: str):
        """Update showcase content"""
        with self._connect() as conn:
            conn.execute("UPDATE showcases SET content = ? WHERE showcase_id = ?", (content, showcase_id))

    def list_showcases(self, target_industry: str | None = None) -> list:
        """List showcases"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if target_industry:
                rows = conn.execute(
                    "SELECT * FROM showcases WHERE target_industry = ? ORDER BY created_at DESC", (target_industry,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM showcases ORDER BY created_at DESC").fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["projects"] = json.loads(r.get("projects", "[]"))
                results.append(r)
            return results

    # ========== Comparison Operations ==========

    def create_comparison(
        self,
        title: str,
        our_solution: str,
        competitors: list | None = None,
        criteria: list | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Create competitive comparison"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO comparisons
                (title, our_solution, competitors, criteria, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    title,
                    our_solution,
                    json.dumps(competitors or []),
                    json.dumps(criteria or []),
                    json.dumps(metadata or {}),
                ),
            )
            return cursor.lastrowid

    def update_comparison_analysis(self, comparison_id: int, analysis: str):
        """Update comparison analysis"""
        with self._connect() as conn:
            conn.execute("UPDATE comparisons SET analysis = ? WHERE comparison_id = ?", (analysis, comparison_id))

    def get_comparison(self, comparison_id: int) -> dict:
        """Get comparison"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM comparisons WHERE comparison_id = ?", (comparison_id,)).fetchone()

            if row:
                result = dict(row)
                result["competitors"] = json.loads(result.get("competitors", "[]"))
                result["criteria"] = json.loads(result.get("criteria", "[]"))
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def list_comparisons(self) -> list:
        """List comparisons"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM comparisons ORDER BY created_at DESC").fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["competitors"] = json.loads(r.get("competitors", "[]"))
                r["criteria"] = json.loads(r.get("criteria", "[]"))
                results.append(r)
            return results
