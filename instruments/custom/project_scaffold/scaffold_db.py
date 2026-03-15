"""
Project Scaffold Database Layer
Stores templates and generated project metadata
"""

import json
import sqlite3
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now


class ScaffoldDatabase:
    """SQLite database for managing project templates and generated projects"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Templates table - stores project template definitions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                language TEXT NOT NULL,
                framework TEXT,
                description TEXT,
                tags TEXT,
                variables TEXT,
                structure TEXT,
                source_path TEXT,
                builtin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Generated projects table - tracks scaffolded projects
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_projects (
                project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                customer_id INTEGER,
                name TEXT NOT NULL,
                output_path TEXT NOT NULL,
                variables_used TEXT,
                app_spec_path TEXT,
                status TEXT DEFAULT 'created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES templates(template_id)
            )
        """)

        # Project files table - tracks generated file manifest
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_files (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                file_path TEXT NOT NULL,
                file_type TEXT,
                template_source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES generated_projects(project_id)
            )
        """)

        # Template components table - reusable components for templates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS template_components (
                component_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                component_type TEXT NOT NULL,
                content TEXT,
                variables TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

        # Seed built-in templates
        self._seed_builtin_templates()

    def _seed_builtin_templates(self):
        """Seed built-in project templates"""
        builtin_templates = [
            {
                "name": "web_app/react",
                "type": "web_app",
                "language": "javascript",
                "framework": "react",
                "description": "React frontend with Vite, TailwindCSS, and React Router",
                "tags": ["frontend", "spa", "react", "vite"],
                "variables": {
                    "project_name": {"type": "string", "required": True},
                    "description": {"type": "string", "default": "A React application"},
                    "use_typescript": {"type": "boolean", "default": True},
                    "use_tailwind": {"type": "boolean", "default": True},
                },
            },
            {
                "name": "web_app/nextjs",
                "type": "web_app",
                "language": "typescript",
                "framework": "nextjs",
                "description": "Next.js full-stack app with App Router and TailwindCSS",
                "tags": ["fullstack", "ssr", "nextjs", "react"],
                "variables": {
                    "project_name": {"type": "string", "required": True},
                    "description": {"type": "string", "default": "A Next.js application"},
                    "use_src_dir": {"type": "boolean", "default": True},
                },
            },
            {
                "name": "api/fastapi",
                "type": "api",
                "language": "python",
                "framework": "fastapi",
                "description": "FastAPI REST API with SQLAlchemy, Pydantic, and async support",
                "tags": ["backend", "api", "python", "fastapi"],
                "variables": {
                    "project_name": {"type": "string", "required": True},
                    "description": {"type": "string", "default": "A FastAPI application"},
                    "use_sqlalchemy": {"type": "boolean", "default": True},
                    "use_alembic": {"type": "boolean", "default": True},
                    "database": {"type": "string", "default": "sqlite", "options": ["sqlite", "postgresql", "mysql"]},
                },
            },
            {
                "name": "api/express",
                "type": "api",
                "language": "javascript",
                "framework": "express",
                "description": "Express.js REST API with TypeScript support",
                "tags": ["backend", "api", "nodejs", "express"],
                "variables": {
                    "project_name": {"type": "string", "required": True},
                    "use_typescript": {"type": "boolean", "default": True},
                    "use_prisma": {"type": "boolean", "default": False},
                },
            },
            {
                "name": "cli/python",
                "type": "cli",
                "language": "python",
                "framework": "click",
                "description": "Python CLI application with Click and rich output",
                "tags": ["cli", "python", "click"],
                "variables": {
                    "project_name": {"type": "string", "required": True},
                    "description": {"type": "string", "default": "A CLI application"},
                    "use_rich": {"type": "boolean", "default": True},
                },
            },
            {
                "name": "microservice/python",
                "type": "microservice",
                "language": "python",
                "framework": "fastapi",
                "description": "Python microservice with FastAPI, Docker, and health checks",
                "tags": ["microservice", "docker", "python", "fastapi"],
                "variables": {
                    "service_name": {"type": "string", "required": True},
                    "description": {"type": "string", "default": "A microservice"},
                    "port": {"type": "integer", "default": 8000},
                },
            },
        ]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for template in builtin_templates:
            cursor.execute(
                """
                INSERT OR IGNORE INTO templates
                (name, type, language, framework, description, tags, variables, builtin)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
                (
                    template["name"],
                    template["type"],
                    template["language"],
                    template.get("framework"),
                    template["description"],
                    json.dumps(template.get("tags", [])),
                    json.dumps(template.get("variables", {})),
                ),
            )

        conn.commit()
        conn.close()

    # ========== Template Methods ==========

    def add_template(
        self,
        name: str,
        template_type: str,
        language: str,
        framework: str | None = None,
        description: str = "",
        tags: list | None = None,
        variables: dict | None = None,
        structure: dict | None = None,
        source_path: str | None = None,
    ) -> int:
        """Add a new template"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO templates
            (name, type, language, framework, description, tags, variables, structure, source_path, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                name,
                template_type,
                language,
                framework,
                description,
                json.dumps(tags or []),
                json.dumps(variables or {}),
                json.dumps(structure or {}),
                source_path,
                isoformat_z(utc_now()),
            ),
        )

        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return template_id

    def get_template(self, name: str | None = None, template_id: int | None = None) -> dict:
        """Get template by name or ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if template_id:
            cursor.execute("SELECT * FROM templates WHERE template_id = ?", (template_id,))
        elif name:
            cursor.execute("SELECT * FROM templates WHERE name = ?", (name,))
        else:
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_templates(
        self,
        template_type: str | None = None,
        language: str | None = None,
        framework: str | None = None,
        builtin_only: bool = False,
    ) -> list:
        """List templates with optional filters"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM templates WHERE 1=1"
        params = []

        if template_type:
            query += " AND type = ?"
            params.append(template_type)
        if language:
            query += " AND language = ?"
            params.append(language)
        if framework:
            query += " AND framework = ?"
            params.append(framework)
        if builtin_only:
            query += " AND builtin = 1"

        query += " ORDER BY type, name"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def delete_template(self, template_id: int) -> bool:
        """Delete a template (only non-builtin)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM templates WHERE template_id = ? AND builtin = 0", (template_id,))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return success

    # ========== Project Methods ==========

    def add_project(
        self,
        template_id: int,
        name: str,
        output_path: str,
        variables_used: dict | None = None,
        customer_id: int | None = None,
        app_spec_path: str | None = None,
    ) -> int:
        """Record a generated project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO generated_projects
            (template_id, customer_id, name, output_path, variables_used, app_spec_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (template_id, customer_id, name, output_path, json.dumps(variables_used or {}), app_spec_path),
        )

        project_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return project_id

    def get_project(self, project_id: int) -> dict:
        """Get project by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM generated_projects WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_projects(self, customer_id: int | None = None, template_id: int | None = None) -> list:
        """List generated projects"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM generated_projects WHERE 1=1"
        params = []

        if customer_id:
            query += " AND customer_id = ?"
            params.append(customer_id)
        if template_id:
            query += " AND template_id = ?"
            params.append(template_id)

        query += " ORDER BY created_at DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def update_project_status(self, project_id: int, status: str) -> bool:
        """Update project status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("UPDATE generated_projects SET status = ? WHERE project_id = ?", (status, project_id))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return success

    # ========== Project Files Methods ==========

    def add_project_file(
        self, project_id: int, file_path: str, file_type: str | None = None, template_source: str | None = None
    ) -> int:
        """Record a generated file"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO project_files (project_id, file_path, file_type, template_source)
            VALUES (?, ?, ?, ?)
        """,
            (project_id, file_path, file_type, template_source),
        )

        file_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return file_id

    def get_project_files(self, project_id: int) -> list:
        """Get all files for a project"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM project_files WHERE project_id = ?", (project_id,))
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    # ========== Component Methods ==========

    def add_component(self, name: str, component_type: str, content: str, variables: dict | None = None) -> int:
        """Add a reusable component"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO template_components
            (name, component_type, content, variables)
            VALUES (?, ?, ?, ?)
        """,
            (name, component_type, content, json.dumps(variables or {})),
        )

        component_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return component_id

    def get_component(self, name: str) -> dict:
        """Get component by name"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM template_components WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_components(self, component_type: str | None = None) -> list:
        """List components"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if component_type:
            cursor.execute("SELECT * FROM template_components WHERE component_type = ?", (component_type,))
        else:
            cursor.execute("SELECT * FROM template_components")

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row) -> dict:
        """Convert database row to dictionary"""
        result = dict(row)
        # Parse JSON fields
        for field in ["tags", "variables", "structure", "variables_used"]:
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except json.JSONDecodeError:
                    pass
        return result
