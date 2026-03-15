"""
Skill Importer Database Layer
Stores imported Claude Code skills and their metadata
"""

import json
import sqlite3
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, utc_now


class SkillDatabase:
    """SQLite database for managing imported skills"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Skills table - stores imported skill metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                source_path TEXT,
                description TEXT,
                arguments TEXT,
                tool_requirements TEXT,
                content TEXT,
                frontmatter TEXT,
                plugin_name TEXT,
                category TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Skill executions table - tracks usage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skill_executions (
                execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id INTEGER,
                input_args TEXT,
                output TEXT,
                status TEXT,
                duration_ms REAL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        # Generated tools table - tracks dynamically created tools
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS generated_tools (
                tool_id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id INTEGER,
                tool_path TEXT,
                prompt_path TEXT,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
            )
        """)

        # Plugins table - stores imported Claude Code plugins
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS plugins (
                plugin_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                source_path TEXT,
                description TEXT,
                version TEXT,
                manifest TEXT,
                skills_count INTEGER DEFAULT 0,
                hooks_count INTEGER DEFAULT 0,
                agents_count INTEGER DEFAULT 0,
                mcp_servers_count INTEGER DEFAULT 0,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Hooks table - stores imported hooks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hooks (
                hook_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER,
                name TEXT NOT NULL,
                event TEXT NOT NULL,
                hook_type TEXT,
                content TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
            )
        """)

        # Agents table - stores imported agent definitions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                system_prompt TEXT,
                tools TEXT,
                model TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
            )
        """)

        # MCP servers table - stores MCP server configurations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mcp_servers (
                server_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plugin_id INTEGER,
                name TEXT NOT NULL,
                server_type TEXT,
                config TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plugin_id) REFERENCES plugins(plugin_id)
            )
        """)

        conn.commit()
        conn.close()

    def add_skill(
        self,
        name: str,
        source_path: str,
        description: str,
        arguments: dict,
        tool_requirements: list,
        content: str,
        frontmatter: dict,
        plugin_name: str | None = None,
        category: str | None = None,
    ) -> int:
        """Add a new imported skill"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO skills
            (name, source_path, description, arguments, tool_requirements,
             content, frontmatter, plugin_name, category, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                name,
                source_path,
                description,
                json.dumps(arguments),
                json.dumps(tool_requirements),
                content,
                json.dumps(frontmatter),
                plugin_name,
                category,
                isoformat_z(utc_now()),
            ),
        )

        skill_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return skill_id

    def get_skill(self, name: str | None = None, skill_id: int | None = None) -> dict:
        """Get skill by name or ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if skill_id:
            cursor.execute("SELECT * FROM skills WHERE skill_id = ?", (skill_id,))
        elif name:
            cursor.execute("SELECT * FROM skills WHERE name = ?", (name,))
        else:
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_skills(
        self, enabled_only: bool = True, category: str | None = None, plugin_name: str | None = None
    ) -> list:
        """List all imported skills with optional filters"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM skills WHERE 1=1"
        params = []

        if enabled_only:
            query += " AND enabled = 1"
        if category:
            query += " AND category = ?"
            params.append(category)
        if plugin_name:
            query += " AND plugin_name = ?"
            params.append(plugin_name)

        query += " ORDER BY name"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def update_skill(self, skill_id: int, **kwargs) -> bool:
        """Update skill fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build dynamic update query
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ["description", "content", "enabled", "category"]:
                fields.append(f"{key} = ?")
                values.append(value)
            elif key in ["arguments", "tool_requirements", "frontmatter"]:
                fields.append(f"{key} = ?")
                values.append(json.dumps(value))

        if not fields:
            return False

        fields.append("updated_at = ?")
        values.append(isoformat_z(utc_now()))
        values.append(skill_id)

        cursor.execute(  # nosec B608 - controlled query construction
            f"""
            UPDATE skills SET {", ".join(fields)} WHERE skill_id = ?
        """,
            values,
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def delete_skill(self, skill_id: int) -> bool:
        """Delete a skill"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM skills WHERE skill_id = ?", (skill_id,))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return success

    def record_execution(self, skill_id: int, input_args: dict, output: str, status: str, duration_ms: float) -> int:
        """Record a skill execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO skill_executions
            (skill_id, input_args, output, status, duration_ms)
            VALUES (?, ?, ?, ?, ?)
        """,
            (skill_id, json.dumps(input_args), output, status, duration_ms),
        )

        execution_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return execution_id

    def get_execution_stats(self, skill_id: int | None = None) -> dict:
        """Get execution statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if skill_id:
            cursor.execute(
                """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                       AVG(duration_ms) as avg_duration
                FROM skill_executions WHERE skill_id = ?
            """,
                (skill_id,),
            )
        else:
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success,
                       AVG(duration_ms) as avg_duration
                FROM skill_executions
            """)

        row = cursor.fetchone()
        conn.close()

        return {
            "total_executions": row[0] or 0,
            "successful": row[1] or 0,
            "avg_duration_ms": round(row[2], 2) if row[2] else 0,
        }

    def register_generated_tool(self, skill_id: int, tool_path: str, prompt_path: str) -> int:
        """Register a dynamically generated tool"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO generated_tools (skill_id, tool_path, prompt_path)
            VALUES (?, ?, ?)
        """,
            (skill_id, tool_path, prompt_path),
        )

        tool_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return tool_id

    def _row_to_dict(self, row) -> dict:
        """Convert database row to dictionary"""
        result = dict(row)
        # Parse JSON fields
        for field in ["arguments", "tool_requirements", "frontmatter", "manifest", "config", "tools"]:
            if result.get(field):
                try:
                    result[field] = json.loads(result[field])
                except json.JSONDecodeError:
                    pass
        return result

    # ========== Plugin methods ==========

    def add_plugin(self, name: str, source_path: str, description: str, version: str, manifest: dict) -> int:
        """Add a new imported plugin"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO plugins
            (name, source_path, description, version, manifest, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (name, source_path, description, version, json.dumps(manifest), isoformat_z(utc_now())),
        )

        plugin_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return plugin_id

    def get_plugin(self, name: str | None = None, plugin_id: int | None = None) -> dict:
        """Get plugin by name or ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if plugin_id:
            cursor.execute("SELECT * FROM plugins WHERE plugin_id = ?", (plugin_id,))
        elif name:
            cursor.execute("SELECT * FROM plugins WHERE name = ?", (name,))
        else:
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def list_plugins(self, enabled_only: bool = True) -> list:
        """List all imported plugins"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM plugins"
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY name"

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def update_plugin_counts(
        self, plugin_id: int, skills: int = 0, hooks: int = 0, agents: int = 0, mcp_servers: int = 0
    ) -> bool:
        """Update component counts for a plugin"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE plugins SET
                skills_count = ?,
                hooks_count = ?,
                agents_count = ?,
                mcp_servers_count = ?,
                updated_at = ?
            WHERE plugin_id = ?
        """,
            (skills, hooks, agents, mcp_servers, isoformat_z(utc_now()), plugin_id),
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def delete_plugin(self, plugin_id: int) -> bool:
        """Delete a plugin and all its components"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Delete associated components
        cursor.execute(
            "DELETE FROM skills WHERE plugin_name = (SELECT name FROM plugins WHERE plugin_id = ?)", (plugin_id,)
        )
        cursor.execute("DELETE FROM hooks WHERE plugin_id = ?", (plugin_id,))
        cursor.execute("DELETE FROM agents WHERE plugin_id = ?", (plugin_id,))
        cursor.execute("DELETE FROM mcp_servers WHERE plugin_id = ?", (plugin_id,))

        # Delete plugin
        cursor.execute("DELETE FROM plugins WHERE plugin_id = ?", (plugin_id,))
        success = cursor.rowcount > 0

        conn.commit()
        conn.close()
        return success

    # ========== Hook methods ==========

    def add_hook(self, plugin_id: int, name: str, event: str, hook_type: str, content: str) -> int:
        """Add an imported hook"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO hooks (plugin_id, name, event, hook_type, content)
            VALUES (?, ?, ?, ?, ?)
        """,
            (plugin_id, name, event, hook_type, content),
        )

        hook_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return hook_id

    def list_hooks(self, plugin_id: int | None = None, event: str | None = None) -> list:
        """List hooks with optional filters"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM hooks WHERE enabled = 1"
        params = []

        if plugin_id:
            query += " AND plugin_id = ?"
            params.append(plugin_id)
        if event:
            query += " AND event = ?"
            params.append(event)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    # ========== Agent methods ==========

    def add_agent(
        self, plugin_id: int, name: str, description: str, system_prompt: str, tools: list, model: str | None = None
    ) -> int:
        """Add an imported agent definition"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO agents (plugin_id, name, description, system_prompt, tools, model)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (plugin_id, name, description, system_prompt, json.dumps(tools), model),
        )

        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return agent_id

    def list_agents(self, plugin_id: int | None = None) -> list:
        """List imported agents"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM agents WHERE enabled = 1"
        params = []

        if plugin_id:
            query += " AND plugin_id = ?"
            params.append(plugin_id)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    # ========== MCP Server methods ==========

    def add_mcp_server(self, plugin_id: int, name: str, server_type: str, config: dict) -> int:
        """Add an MCP server configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO mcp_servers (plugin_id, name, server_type, config)
            VALUES (?, ?, ?, ?)
        """,
            (plugin_id, name, server_type, json.dumps(config)),
        )

        server_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return server_id

    def list_mcp_servers(self, plugin_id: int | None = None) -> list:
        """List MCP server configurations"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM mcp_servers WHERE enabled = 1"
        params = []

        if plugin_id:
            query += " AND plugin_id = ?"
            params.append(plugin_id)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]
