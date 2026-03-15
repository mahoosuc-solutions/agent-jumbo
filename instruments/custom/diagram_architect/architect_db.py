"""
Database module for Diagram Architect tool
Stores architecture analyses, generated diagrams, and component relationships
"""

import json
import sqlite3
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now


class DiagramArchitectDatabase:
    """SQLite database for architecture analysis and diagram storage"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Architecture analyses
                CREATE TABLE IF NOT EXISTS analyses (
                    analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_path TEXT NOT NULL,
                    project_name TEXT,
                    analysis_type TEXT DEFAULT 'full',
                    status TEXT DEFAULT 'pending',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    metadata TEXT DEFAULT '{}'
                );

                -- Detected components
                CREATE TABLE IF NOT EXISTS components (
                    component_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    file_path TEXT,
                    description TEXT,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id)
                );

                -- Component relationships
                CREATE TABLE IF NOT EXISTS relationships (
                    relationship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    source_component_id INTEGER NOT NULL,
                    target_component_id INTEGER NOT NULL,
                    relationship_type TEXT NOT NULL,
                    label TEXT,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id),
                    FOREIGN KEY (source_component_id) REFERENCES components(component_id),
                    FOREIGN KEY (target_component_id) REFERENCES components(component_id)
                );

                -- Generated diagrams
                CREATE TABLE IF NOT EXISTS diagrams (
                    diagram_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER,
                    diagram_type TEXT NOT NULL,
                    title TEXT,
                    mermaid_code TEXT,
                    svg_path TEXT,
                    png_path TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id)
                );

                -- External integrations detected
                CREATE TABLE IF NOT EXISTS integrations (
                    integration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    integration_type TEXT NOT NULL,
                    endpoint TEXT,
                    protocol TEXT,
                    detected_in TEXT,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id)
                );

                -- Data flows
                CREATE TABLE IF NOT EXISTS data_flows (
                    flow_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    data_type TEXT,
                    flow_type TEXT,
                    description TEXT,
                    properties TEXT DEFAULT '{}',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (analysis_id) REFERENCES analyses(analysis_id)
                );

                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_components_analysis ON components(analysis_id);
                CREATE INDEX IF NOT EXISTS idx_relationships_analysis ON relationships(analysis_id);
                CREATE INDEX IF NOT EXISTS idx_diagrams_analysis ON diagrams(analysis_id);
                CREATE INDEX IF NOT EXISTS idx_integrations_analysis ON integrations(analysis_id);
                CREATE INDEX IF NOT EXISTS idx_data_flows_analysis ON data_flows(analysis_id);
            """)

    # ========== Analysis Operations ==========

    def create_analysis(
        self,
        project_path: str,
        project_name: str | None = None,
        analysis_type: str = "full",
        metadata: dict | None = None,
    ) -> int:
        """Create a new architecture analysis"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO analyses (project_path, project_name, analysis_type, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (project_path, project_name or Path(project_path).name, analysis_type, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_analysis(self, analysis_id: int) -> dict:
        """Get analysis by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM analyses WHERE analysis_id = ?", (analysis_id,)).fetchone()

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))

                # Get counts
                result["components_count"] = conn.execute(
                    "SELECT COUNT(*) FROM components WHERE analysis_id = ?", (analysis_id,)
                ).fetchone()[0]
                result["relationships_count"] = conn.execute(
                    "SELECT COUNT(*) FROM relationships WHERE analysis_id = ?", (analysis_id,)
                ).fetchone()[0]
                result["diagrams_count"] = conn.execute(
                    "SELECT COUNT(*) FROM diagrams WHERE analysis_id = ?", (analysis_id,)
                ).fetchone()[0]

                return result
            return None

    def list_analyses(self, project_path: str | None = None) -> list:
        """List all analyses"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if project_path:
                rows = conn.execute(
                    "SELECT * FROM analyses WHERE project_path = ? ORDER BY created_at DESC", (project_path,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM analyses ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]

    def update_analysis_status(self, analysis_id: int, status: str):
        """Update analysis status"""
        with sqlite3.connect(self.db_path) as conn:
            completed_at = isoformat_z(utc_now()) if status == "completed" else None
            conn.execute(
                """
                UPDATE analyses SET status = ?, completed_at = ?
                WHERE analysis_id = ?
            """,
                (status, completed_at, analysis_id),
            )

    # ========== Component Operations ==========

    def add_component(
        self,
        analysis_id: int,
        name: str,
        component_type: str,
        file_path: str | None = None,
        description: str | None = None,
        properties: dict | None = None,
    ) -> int:
        """Add a detected component"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO components (analysis_id, name, component_type, file_path, description, properties)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (analysis_id, name, component_type, file_path, description, json.dumps(properties or {})),
            )
            return cursor.lastrowid

    def get_components(self, analysis_id: int, component_type: str | None = None) -> list:
        """Get components for an analysis"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if component_type:
                rows = conn.execute(
                    """
                    SELECT * FROM components
                    WHERE analysis_id = ? AND component_type = ?
                    ORDER BY name
                """,
                    (analysis_id, component_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM components
                    WHERE analysis_id = ?
                    ORDER BY component_type, name
                """,
                    (analysis_id,),
                ).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["properties"] = json.loads(r.get("properties", "{}"))
                results.append(r)
            return results

    # ========== Relationship Operations ==========

    def add_relationship(
        self,
        analysis_id: int,
        source_id: int,
        target_id: int,
        relationship_type: str,
        label: str | None = None,
        properties: dict | None = None,
    ) -> int:
        """Add a component relationship"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO relationships
                (analysis_id, source_component_id, target_component_id, relationship_type, label, properties)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (analysis_id, source_id, target_id, relationship_type, label, json.dumps(properties or {})),
            )
            return cursor.lastrowid

    def get_relationships(self, analysis_id: int) -> list:
        """Get relationships for an analysis with component names"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT r.*,
                       s.name as source_name, s.component_type as source_type,
                       t.name as target_name, t.component_type as target_type
                FROM relationships r
                JOIN components s ON r.source_component_id = s.component_id
                JOIN components t ON r.target_component_id = t.component_id
                WHERE r.analysis_id = ?
            """,
                (analysis_id,),
            ).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["properties"] = json.loads(r.get("properties", "{}"))
                results.append(r)
            return results

    # ========== Integration Operations ==========

    def add_integration(
        self,
        analysis_id: int,
        name: str,
        integration_type: str,
        endpoint: str | None = None,
        protocol: str | None = None,
        detected_in: str | None = None,
        properties: dict | None = None,
    ) -> int:
        """Add a detected external integration"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO integrations
                (analysis_id, name, integration_type, endpoint, protocol, detected_in, properties)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (analysis_id, name, integration_type, endpoint, protocol, detected_in, json.dumps(properties or {})),
            )
            return cursor.lastrowid

    def get_integrations(self, analysis_id: int) -> list:
        """Get integrations for an analysis"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM integrations WHERE analysis_id = ?", (analysis_id,)).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["properties"] = json.loads(r.get("properties", "{}"))
                results.append(r)
            return results

    # ========== Data Flow Operations ==========

    def add_data_flow(
        self,
        analysis_id: int,
        name: str,
        source: str,
        destination: str,
        data_type: str | None = None,
        flow_type: str | None = None,
        description: str | None = None,
        properties: dict | None = None,
    ) -> int:
        """Add a data flow"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO data_flows
                (analysis_id, name, source, destination, data_type, flow_type, description, properties)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    analysis_id,
                    name,
                    source,
                    destination,
                    data_type,
                    flow_type,
                    description,
                    json.dumps(properties or {}),
                ),
            )
            return cursor.lastrowid

    def get_data_flows(self, analysis_id: int) -> list:
        """Get data flows for an analysis"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM data_flows WHERE analysis_id = ?", (analysis_id,)).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["properties"] = json.loads(r.get("properties", "{}"))
                results.append(r)
            return results

    # ========== Diagram Operations ==========

    def save_diagram(
        self,
        diagram_type: str,
        title: str,
        mermaid_code: str,
        analysis_id: int | None = None,
        svg_path: str | None = None,
        png_path: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Save a generated diagram"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO diagrams
                (analysis_id, diagram_type, title, mermaid_code, svg_path, png_path, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (analysis_id, diagram_type, title, mermaid_code, svg_path, png_path, json.dumps(metadata or {})),
            )
            return cursor.lastrowid

    def get_diagram(self, diagram_id: int) -> dict:
        """Get a diagram by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM diagrams WHERE diagram_id = ?", (diagram_id,)).fetchone()

            if row:
                result = dict(row)
                result["metadata"] = json.loads(result.get("metadata", "{}"))
                return result
            return None

    def get_diagrams(self, analysis_id: int | None = None, diagram_type: str | None = None) -> list:
        """Get diagrams with optional filters"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM diagrams WHERE 1=1"
            params = []

            if analysis_id:
                query += " AND analysis_id = ?"
                params.append(analysis_id)
            if diagram_type:
                query += " AND diagram_type = ?"
                params.append(diagram_type)

            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()

            results = []
            for row in rows:
                r = dict(row)
                r["metadata"] = json.loads(r.get("metadata", "{}"))
                results.append(r)
            return results
