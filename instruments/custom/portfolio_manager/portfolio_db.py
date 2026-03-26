"""
Portfolio Manager Database Schema and Operations
SQLite backend for managing code projects and product portfolio
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python.helpers import files
from python.helpers.db_manager import DatabaseManager, get_timestamp


class PortfolioDatabase:
    """Database operations for Portfolio Manager"""

    SCHEMA = """
    -- Projects table: Core project information
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        path TEXT UNIQUE NOT NULL,
        description TEXT,
        language TEXT,
        framework TEXT,
        version TEXT,
        license TEXT,
        status TEXT DEFAULT 'draft',  -- draft, ready, listed, sold
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        last_scanned_at TEXT
    );

    -- Project metadata: Detected features and stats
    CREATE TABLE IF NOT EXISTS project_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        UNIQUE(project_id, key)
    );

    -- Products table: Productized versions of projects
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        tagline TEXT,
        description TEXT,
        category TEXT,
        price REAL DEFAULT 0,
        price_model TEXT DEFAULT 'one-time',  -- one-time, subscription, freemium
        demo_url TEXT,
        docs_url TEXT,
        sale_readiness_score INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
    );

    -- Product features: Key selling points
    CREATE TABLE IF NOT EXISTS product_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        feature TEXT NOT NULL,
        priority INTEGER DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );

    -- Sales pipeline: Track potential and completed sales
    CREATE TABLE IF NOT EXISTS sales_pipeline (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        customer_name TEXT,
        customer_email TEXT,
        stage TEXT DEFAULT 'lead',  -- lead, qualified, proposal, negotiation, closed-won, closed-lost
        value REAL DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        closed_at TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    );

    -- Documentation status: Track docs for each project
    CREATE TABLE IF NOT EXISTS documentation (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,  -- readme, api, tutorial, changelog, contributing
        exists_flag INTEGER DEFAULT 0,
        quality_score INTEGER DEFAULT 0,  -- 0-100
        last_checked_at TEXT,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        UNIQUE(project_id, doc_type)
    );

    -- Tags for categorization
    CREATE TABLE IF NOT EXISTS project_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
        UNIQUE(project_id, tag)
    );

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
    CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
    CREATE INDEX IF NOT EXISTS idx_sales_stage ON sales_pipeline(stage);
    """

    def __init__(self, data_dir: str | None = None):
        resolved_data_dir = data_dir
        if not resolved_data_dir:
            resolved_data_dir = "/aj/data" if _is_dockerized() else files.get_abs_path("tmp", "portfolio_data")
        self.db = DatabaseManager("portfolio.db", resolved_data_dir)
        self._init_schema()


def _is_dockerized() -> bool:
    return bool(os.getenv("DOCKERIZED")) or Path("/.dockerenv").exists()

    def _init_schema(self):
        """Initialize database schema"""
        with self.db.cursor() as cur:
            cur.executescript(self.SCHEMA)

    # Project operations
    def add_project(self, name: str, path: str, **kwargs) -> int:
        """Add a new project"""
        now = get_timestamp()
        data = {
            "name": name,
            "path": path,
            "description": kwargs.get("description"),
            "language": kwargs.get("language"),
            "framework": kwargs.get("framework"),
            "version": kwargs.get("version"),
            "license": kwargs.get("license"),
            "status": kwargs.get("status", "draft"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("projects", data)

    def get_project(self, project_id: int) -> dict | None:
        """Get project by ID"""
        return self.db.fetch_one("SELECT * FROM projects WHERE id = ?", (project_id,))

    def get_project_by_path(self, path: str) -> dict | None:
        """Get project by path"""
        return self.db.fetch_one("SELECT * FROM projects WHERE path = ?", (path,))

    def list_projects(self, status: str | None = None) -> list[dict]:
        """List all projects, optionally filtered by status"""
        if status:
            return self.db.fetch_all("SELECT * FROM projects WHERE status = ? ORDER BY updated_at DESC", (status,))
        return self.db.fetch_all("SELECT * FROM projects ORDER BY updated_at DESC")

    def get_projects(
        self,
        status: str | None = None,
        language: str | None = None,
        min_sale_readiness: int | None = None,
    ) -> list[dict]:
        """
        Backward-compatible project listing with lightweight metadata joins.

        This keeps older callers (tools/API) working while newer code can still
        use `list_projects` directly.
        """
        projects = self.list_projects(status=status)
        result: list[dict] = []

        for project in projects:
            metadata = self.get_metadata(project["id"])
            project = dict(project)
            project["sale_readiness"] = int(metadata.get("sale_readiness_score", 0) or 0)

            if language and project.get("language") != language:
                continue
            if min_sale_readiness is not None and project["sale_readiness"] < min_sale_readiness:
                continue

            result.append(project)

        return result

    def update_project(self, project_id: int, **kwargs) -> int:
        """Update project fields"""
        kwargs["updated_at"] = get_timestamp()
        return self.db.update("projects", kwargs, "id = ?", (project_id,))

    def delete_project(self, project_id: int) -> int:
        """Delete project and related data"""
        return self.db.delete("projects", "id = ?", (project_id,))

    # Metadata operations
    def set_metadata(self, project_id: int, key: str, value: Any):
        """Set or update project metadata"""
        value_str = json.dumps(value) if not isinstance(value, str) else value
        existing = self.db.fetch_one(
            "SELECT id FROM project_metadata WHERE project_id = ? AND key = ?", (project_id, key)
        )
        if existing:
            self.db.update("project_metadata", {"value": value_str}, "project_id = ? AND key = ?", (project_id, key))
        else:
            self.db.insert("project_metadata", {"project_id": project_id, "key": key, "value": value_str})

    def get_metadata(self, project_id: int) -> dict[str, Any]:
        """Get all metadata for a project"""
        rows = self.db.fetch_all("SELECT key, value FROM project_metadata WHERE project_id = ?", (project_id,))
        result = {}
        for row in rows:
            try:
                result[row["key"]] = json.loads(row["value"])
            except (json.JSONDecodeError, TypeError):
                result[row["key"]] = row["value"]
        return result

    # Product operations
    def create_product(self, project_id: int, name: str, **kwargs) -> int:
        """Create a product from a project"""
        now = get_timestamp()
        data = {
            "project_id": project_id,
            "name": name,
            "tagline": kwargs.get("tagline"),
            "description": kwargs.get("description"),
            "category": kwargs.get("category"),
            "price": kwargs.get("price", 0),
            "price_model": kwargs.get("price_model", "one-time"),
            "demo_url": kwargs.get("demo_url"),
            "docs_url": kwargs.get("docs_url"),
            "sale_readiness_score": kwargs.get("sale_readiness_score", 0),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("products", data)

    def get_product(self, product_id: int) -> dict | None:
        """Get product by ID with project info"""
        return self.db.fetch_one(
            """
            SELECT p.*, pr.name as project_name, pr.path as project_path
            FROM products p
            JOIN projects pr ON p.project_id = pr.id
            WHERE p.id = ?
        """,
            (product_id,),
        )

    def list_products(self, category: str | None = None) -> list[dict]:
        """List all products"""
        if category:
            return self.db.fetch_all("SELECT * FROM products WHERE category = ? ORDER BY updated_at DESC", (category,))
        return self.db.fetch_all("SELECT * FROM products ORDER BY updated_at DESC")

    def get_products(
        self,
        project_id: int | None = None,
        category: str | None = None,
    ) -> list[dict]:
        """Backward-compatible product retrieval helper."""
        if project_id is not None:
            return self.db.fetch_all(
                "SELECT * FROM products WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,),
            )
        return self.list_products(category=category)

    def update_product(self, product_id: int, **kwargs) -> int:
        """Update product fields"""
        kwargs["updated_at"] = get_timestamp()
        return self.db.update("products", kwargs, "id = ?", (product_id,))

    def add_product_feature(self, product_id: int, feature: str, priority: int = 0) -> int:
        """Add a feature to a product"""
        return self.db.insert("product_features", {"product_id": product_id, "feature": feature, "priority": priority})

    def get_product_features(self, product_id: int) -> list[dict]:
        """Get all features for a product"""
        return self.db.fetch_all(
            "SELECT * FROM product_features WHERE product_id = ? ORDER BY priority DESC", (product_id,)
        )

    # Sales pipeline operations
    def add_lead(self, product_id: int, customer_name: str, **kwargs) -> int:
        """Add a sales lead"""
        now = get_timestamp()
        data = {
            "product_id": product_id,
            "customer_name": customer_name,
            "customer_email": kwargs.get("customer_email"),
            "stage": kwargs.get("stage", "lead"),
            "value": kwargs.get("value", 0),
            "notes": kwargs.get("notes"),
            "created_at": now,
            "updated_at": now,
        }
        return self.db.insert("sales_pipeline", data)

    def update_lead_stage(self, lead_id: int, stage: str, notes: str | None = None) -> int:
        """Update lead stage"""
        data = {"stage": stage, "updated_at": get_timestamp()}
        if stage.startswith("closed"):
            data["closed_at"] = get_timestamp()
        if notes:
            data["notes"] = notes
        return self.db.update("sales_pipeline", data, "id = ?", (lead_id,))

    def get_pipeline_summary(self) -> dict[str, Any]:
        """Get sales pipeline summary"""
        stages = self.db.fetch_all("""
            SELECT stage, COUNT(*) as count, SUM(value) as total_value
            FROM sales_pipeline
            GROUP BY stage
        """)
        return {row["stage"]: {"count": row["count"], "value": row["total_value"]} for row in stages}

    # Documentation tracking
    def update_documentation(self, project_id: int, doc_type: str, exists: bool, quality_score: int = 0):
        """Update documentation status"""
        existing = self.db.fetch_one(
            "SELECT id FROM documentation WHERE project_id = ? AND doc_type = ?", (project_id, doc_type)
        )
        data = {"exists_flag": 1 if exists else 0, "quality_score": quality_score, "last_checked_at": get_timestamp()}
        if existing:
            self.db.update("documentation", data, "project_id = ? AND doc_type = ?", (project_id, doc_type))
        else:
            data["project_id"] = project_id
            data["doc_type"] = doc_type
            self.db.insert("documentation", data)

    def get_documentation_status(self, project_id: int) -> list[dict]:
        """Get documentation status for a project"""
        return self.db.fetch_all("SELECT * FROM documentation WHERE project_id = ?", (project_id,))

    # Tags
    def add_tag(self, project_id: int, tag: str) -> int:
        """Add a tag to a project"""
        return self.db.insert("project_tags", {"project_id": project_id, "tag": tag})

    def get_tags(self, project_id: int) -> list[str]:
        """Get all tags for a project"""
        rows = self.db.fetch_all("SELECT tag FROM project_tags WHERE project_id = ?", (project_id,))
        return [row["tag"] for row in rows]

    def find_by_tag(self, tag: str) -> list[dict]:
        """Find projects by tag"""
        return self.db.fetch_all(
            """
            SELECT p.* FROM projects p
            JOIN project_tags t ON p.id = t.project_id
            WHERE t.tag = ?
        """,
            (tag,),
        )

    # Analytics
    def get_portfolio_stats(self) -> dict[str, Any]:
        """Get portfolio statistics"""
        project_counts = self.db.fetch_one("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) as draft,
                SUM(CASE WHEN status = 'ready' THEN 1 ELSE 0 END) as ready,
                SUM(CASE WHEN status = 'listed' THEN 1 ELSE 0 END) as listed,
                SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) as sold
            FROM projects
        """)

        product_counts = self.db.fetch_one("""
            SELECT COUNT(*) as total, AVG(sale_readiness_score) as avg_readiness
            FROM products
        """)

        revenue = self.db.fetch_one("""
            SELECT SUM(value) as total_revenue
            FROM sales_pipeline
            WHERE stage = 'closed-won'
        """)

        return {
            "projects": dict(project_counts) if project_counts else {},
            "products": dict(product_counts) if product_counts else {},
            "revenue": revenue["total_revenue"] if revenue and revenue["total_revenue"] else 0,
        }

    def close(self):
        """Close database connection"""
        self.db.close()
