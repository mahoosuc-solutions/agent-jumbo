"""
Database module for Deployment Orchestrator tool
Stores deployment configurations, generated pipelines, and deployment history
"""

import json
import sqlite3
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now


class DeploymentOrchestratorDatabase:
    """SQLite database for deployment orchestration"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = self._connect()
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _init_db(self):
        """Initialize database schema"""
        with self._connect() as conn:
            conn.executescript("""
                -- Projects registered for deployment
                CREATE TABLE IF NOT EXISTS projects (
                    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    project_path TEXT NOT NULL,
                    project_type TEXT,
                    language TEXT,
                    framework TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                );

                -- CI/CD Pipelines
                CREATE TABLE IF NOT EXISTS pipelines (
                    pipeline_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    platform TEXT NOT NULL,
                    name TEXT,
                    config_path TEXT,
                    config_content TEXT,
                    status TEXT DEFAULT 'generated',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );

                -- Docker Configurations
                CREATE TABLE IF NOT EXISTS docker_configs (
                    config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    dockerfile_content TEXT,
                    compose_content TEXT,
                    dockerignore_content TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );

                -- Kubernetes Manifests
                CREATE TABLE IF NOT EXISTS k8s_manifests (
                    manifest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    manifest_type TEXT NOT NULL,
                    name TEXT,
                    content TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );

                -- Environments
                CREATE TABLE IF NOT EXISTS environments (
                    environment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    env_type TEXT DEFAULT 'staging',
                    config TEXT DEFAULT '{}',
                    secrets TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                );

                -- Deployments
                CREATE TABLE IF NOT EXISTS deployments (
                    deployment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    environment_id INTEGER,
                    version TEXT,
                    status TEXT DEFAULT 'pending',
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    logs TEXT,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (project_id) REFERENCES projects(project_id),
                    FOREIGN KEY (environment_id) REFERENCES environments(environment_id)
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_pipelines_project ON pipelines(project_id);
                CREATE INDEX IF NOT EXISTS idx_docker_project ON docker_configs(project_id);
                CREATE INDEX IF NOT EXISTS idx_k8s_project ON k8s_manifests(project_id);
                CREATE INDEX IF NOT EXISTS idx_environments_project ON environments(project_id);
                CREATE INDEX IF NOT EXISTS idx_deployments_project ON deployments(project_id);
            """)

    # ========== Project Operations ==========

    def register_project(
        self,
        name: str,
        project_path: str,
        project_type: str | None = None,
        language: str | None = None,
        framework: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Register a project for deployment"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO projects (name, project_path, project_type, language, framework, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (name, project_path, project_type, language, framework, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_project(self, project_id: int) -> dict:
        """Get project by ID"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def list_projects(self) -> list:
        """List all registered projects"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    # ========== Pipeline Operations ==========

    def save_pipeline(
        self,
        project_id: int,
        platform: str,
        name: str,
        config_path: str,
        config_content: str,
        metadata: dict | None = None,
    ) -> int:
        """Save a CI/CD pipeline configuration"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO pipelines (project_id, platform, name, config_path, config_content, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (project_id, platform, name, config_path, config_content, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_pipeline(self, pipeline_id: int) -> dict:
        """Get pipeline by ID"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM pipelines WHERE pipeline_id = ?", (pipeline_id,)).fetchone()

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def get_pipelines(self, project_id: int) -> list:
        """Get pipelines for a project"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM pipelines WHERE project_id = ? ORDER BY created_at DESC", (project_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    # ========== Docker Operations ==========

    def save_docker_config(
        self,
        project_id: int,
        dockerfile_content: str,
        compose_content: str | None = None,
        dockerignore_content: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Save Docker configuration"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO docker_configs
                (project_id, dockerfile_content, compose_content, dockerignore_content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (project_id, dockerfile_content, compose_content, dockerignore_content, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_docker_config(self, project_id: int) -> dict:
        """Get Docker config for a project"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM docker_configs WHERE project_id = ? ORDER BY created_at DESC LIMIT 1", (project_id,)
            ).fetchone()

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    # ========== Kubernetes Operations ==========

    def save_k8s_manifest(
        self, project_id: int, manifest_type: str, name: str, content: str, metadata: dict | None = None
    ) -> int:
        """Save Kubernetes manifest"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO k8s_manifests (project_id, manifest_type, name, content, metadata)
                VALUES (?, ?, ?, ?, ?)
            """,
                (project_id, manifest_type, name, content, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_k8s_manifests(self, project_id: int, manifest_type: str | None = None) -> list:
        """Get Kubernetes manifests for a project"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if manifest_type:
                rows = conn.execute(
                    """
                    SELECT * FROM k8s_manifests
                    WHERE project_id = ? AND manifest_type = ?
                    ORDER BY created_at DESC
                """,
                    (project_id, manifest_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM k8s_manifests WHERE project_id = ?
                    ORDER BY manifest_type, created_at DESC
                """,
                    (project_id,),
                ).fetchall()
            return [dict(row) for row in rows]

    # ========== Environment Operations ==========

    def create_environment(
        self,
        project_id: int,
        name: str,
        env_type: str = "staging",
        config: dict | None = None,
        secrets: dict | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Create deployment environment"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO environments (project_id, name, env_type, config, secrets, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    project_id,
                    name,
                    env_type,
                    json.dumps(config or {}),
                    json.dumps(secrets or {}),
                    json.dumps(metadata or {}),
                ),
            )
            return cursor.lastrowid

    def get_environment(self, environment_id: int) -> dict:
        """Get environment by ID"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM environments WHERE environment_id = ?", (environment_id,)).fetchone()

            if row:
                result = dict(row)
                result["config"] = json.loads(result.get("config", "{}"))
                result["secrets"] = json.loads(result.get("secrets", "{}"))
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def get_environments(self, project_id: int) -> list:
        """Get environments for a project"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM environments WHERE project_id = ? ORDER BY env_type", (project_id,)
            ).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["config"] = json.loads(r.get("config", "{}"))
                results.append(r)
            return results

    # ========== Deployment Operations ==========

    def create_deployment(
        self,
        project_id: int,
        environment_id: int | None = None,
        version: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Create a deployment record"""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO deployments (project_id, environment_id, version, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (project_id, environment_id, version, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def update_deployment_status(self, deployment_id: int, status: str, logs: str | None = None):
        """Update deployment status"""
        with self._connect() as conn:
            completed_at = isoformat_z(utc_now()) if status in ["completed", "failed"] else None
            conn.execute(
                """
                UPDATE deployments SET status = ?, completed_at = ?, logs = ?
                WHERE deployment_id = ?
            """,
                (status, completed_at, logs, deployment_id),
            )

    def get_deployment(self, deployment_id: int) -> dict:
        """Get deployment by ID"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM deployments WHERE deployment_id = ?", (deployment_id,)).fetchone()

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def get_deployments(self, project_id: int, limit: int = 10) -> list:
        """Get recent deployments for a project"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT d.*, e.name as environment_name
                FROM deployments d
                LEFT JOIN environments e ON d.environment_id = e.environment_id
                WHERE d.project_id = ?
                ORDER BY d.started_at DESC
                LIMIT ?
            """,
                (project_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_latest_deployment(self, project_id: int, environment_id: int | None = None) -> dict:
        """Get latest deployment for a project/environment"""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            if environment_id:
                row = conn.execute(
                    """
                    SELECT * FROM deployments
                    WHERE project_id = ? AND environment_id = ?
                    ORDER BY started_at DESC LIMIT 1
                """,
                    (project_id, environment_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM deployments
                    WHERE project_id = ?
                    ORDER BY started_at DESC LIMIT 1
                """,
                    (project_id,),
                ).fetchone()

            if row:
                return dict(row)
            return None
