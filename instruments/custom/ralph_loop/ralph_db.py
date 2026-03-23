"""
Ralph Loop Database Layer

SQLite storage for Ralph loop state, iterations, and history.
"""

import json
import os
import sqlite3

from python.helpers.datetime_utils import isoformat_z, utc_now


class RalphLoopDatabase:
    """Database layer for Ralph Loop persistence."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_directory()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def _ensure_directory(self):
        """Ensure the database directory exists."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _init_db(self):
        """Initialize database schema."""
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS ralph_loops (
                    loop_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    prompt TEXT NOT NULL,
                    completion_promise TEXT,
                    max_iterations INTEGER DEFAULT 50,
                    current_iteration INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    agent_id TEXT,
                    workflow_execution_id INTEGER,
                    task_id TEXT,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    last_output TEXT,
                    context TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS ralph_iterations (
                    iteration_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loop_id INTEGER NOT NULL,
                    iteration_number INTEGER NOT NULL,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    output_summary TEXT,
                    files_modified TEXT DEFAULT '[]',
                    git_commit TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    FOREIGN KEY (loop_id) REFERENCES ralph_loops(loop_id)
                );

                CREATE INDEX IF NOT EXISTS idx_loops_status ON ralph_loops(status);
                CREATE INDEX IF NOT EXISTS idx_loops_agent ON ralph_loops(agent_id);
                CREATE INDEX IF NOT EXISTS idx_iterations_loop ON ralph_iterations(loop_id);
            """)

    def _row_to_dict(self, cursor, row) -> dict:
        """Convert a row to a dictionary."""
        if row is None:
            return None
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, row))

    # ==================== LOOP OPERATIONS ====================

    def create_loop(
        self,
        prompt: str,
        name: str | None = None,
        completion_promise: str | None = None,
        max_iterations: int = 50,
        agent_id: str | None = None,
        workflow_execution_id: int | None = None,
        task_id: str | None = None,
        context: dict | None = None,
    ) -> int:
        """Create a new Ralph loop."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ralph_loops
                (name, prompt, completion_promise, max_iterations, agent_id,
                 workflow_execution_id, task_id, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name or "Ralph Loop",
                    prompt,
                    completion_promise,
                    max_iterations,
                    agent_id,
                    workflow_execution_id,
                    task_id,
                    json.dumps(context or {}),
                ),
            )
            return cursor.lastrowid

    def get_loop(self, loop_id: int) -> dict | None:
        """Get a loop by ID."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM ralph_loops WHERE loop_id = ?", (loop_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result["context"] = json.loads(result.get("context", "{}"))
                return result
            return None

    def get_active_loop(self, agent_id: str) -> dict | None:
        """Get the active loop for an agent."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM ralph_loops
                WHERE agent_id = ? AND status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
            """,
                (agent_id,),
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result["context"] = json.loads(result.get("context", "{}"))
                return result
            return None

    def list_loops(self, status: str | None = None, agent_id: str | None = None, limit: int = 50) -> list:
        """List loops with optional filtering."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM ralph_loops WHERE 1=1"
            params = []

            if status:
                query += " AND status = ?"
                params.append(status)
            if agent_id:
                query += " AND agent_id = ?"
                params.append(agent_id)

            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result["context"] = json.loads(result.get("context", "{}"))
                results.append(result)
            return results

    def update_loop(
        self,
        loop_id: int,
        status: str | None = None,
        current_iteration: int | None = None,
        last_output: str | None = None,
        completed_at: str | None = None,
        context: dict | None = None,
    ):
        """Update loop fields."""
        updates = []
        params = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if current_iteration is not None:
            updates.append("current_iteration = ?")
            params.append(current_iteration)
        if last_output is not None:
            updates.append("last_output = ?")
            params.append(last_output)
        if completed_at is not None:
            updates.append("completed_at = ?")
            params.append(completed_at)
        if context is not None:
            updates.append("context = ?")
            params.append(json.dumps(context))

        if not updates:
            return

        params.append(loop_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE ralph_loops SET {', '.join(updates)} WHERE loop_id = ?",  # nosec B608 - controlled query construction
                params,
            )

    def increment_iteration(self, loop_id: int) -> int:
        """Increment the iteration counter and return new value."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ralph_loops
                SET current_iteration = current_iteration + 1
                WHERE loop_id = ?
            """,
                (loop_id,),
            )
            cursor = conn.execute("SELECT current_iteration FROM ralph_loops WHERE loop_id = ?", (loop_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    def complete_loop(self, loop_id: int, status: str = "completed"):
        """Mark a loop as completed."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ralph_loops
                SET status = ?, completed_at = ?
                WHERE loop_id = ?
            """,
                (status, isoformat_z(utc_now()), loop_id),
            )

    def delete_loop(self, loop_id: int):
        """Delete a loop and its iterations."""
        with self._connect() as conn:
            conn.execute("DELETE FROM ralph_iterations WHERE loop_id = ?", (loop_id,))
            conn.execute("DELETE FROM ralph_loops WHERE loop_id = ?", (loop_id,))

    # ==================== ITERATION OPERATIONS ====================

    def create_iteration(
        self,
        loop_id: int,
        iteration_number: int,
        output_summary: str | None = None,
        files_modified: list | None = None,
        git_commit: str | None = None,
        success: bool | None = None,
        error_message: str | None = None,
    ) -> int:
        """Record an iteration."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO ralph_iterations
                (loop_id, iteration_number, output_summary, files_modified,
                 git_commit, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    loop_id,
                    iteration_number,
                    output_summary,
                    json.dumps(files_modified or []),
                    git_commit,
                    success,
                    error_message,
                ),
            )
            return cursor.lastrowid

    def complete_iteration(
        self,
        iteration_id: int,
        output_summary: str | None = None,
        files_modified: list | None = None,
        git_commit: str | None = None,
        success: bool = True,
        error_message: str | None = None,
    ):
        """Complete an iteration with results."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE ralph_iterations
                SET completed_at = ?,
                    output_summary = COALESCE(?, output_summary),
                    files_modified = COALESCE(?, files_modified),
                    git_commit = COALESCE(?, git_commit),
                    success = ?,
                    error_message = ?
                WHERE iteration_id = ?
            """,
                (
                    isoformat_z(utc_now()),
                    output_summary,
                    json.dumps(files_modified) if files_modified else None,
                    git_commit,
                    success,
                    error_message,
                    iteration_id,
                ),
            )

    def get_iterations(self, loop_id: int) -> list:
        """Get all iterations for a loop."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM ralph_iterations
                WHERE loop_id = ?
                ORDER BY iteration_number ASC
            """,
                (loop_id,),
            )
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result["files_modified"] = json.loads(result.get("files_modified", "[]"))
                results.append(result)
            return results

    def get_latest_iteration(self, loop_id: int) -> dict | None:
        """Get the latest iteration for a loop."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM ralph_iterations
                WHERE loop_id = ?
                ORDER BY iteration_number DESC
                LIMIT 1
            """,
                (loop_id,),
            )
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result["files_modified"] = json.loads(result.get("files_modified", "[]"))
                return result
            return None

    # ==================== STATISTICS ====================

    def get_stats(self, agent_id: str | None = None) -> dict:
        """Get Ralph loop statistics."""
        with self._connect() as conn:
            agent_filter = " AND agent_id = ?" if agent_id else ""
            params = [agent_id] if agent_id else []

            # Total loops
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM ralph_loops WHERE 1=1{agent_filter}",  # nosec B608 - controlled query construction
                params,
            )
            total_loops = cursor.fetchone()[0]

            # Active loops (status = 'active')
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM ralph_loops WHERE status = 'active'{agent_filter}",  # nosec B608 - controlled query construction
                params,
            )
            active_loops = cursor.fetchone()[0]

            # Completed loops (status = 'completed')
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM ralph_loops WHERE status = 'completed'{agent_filter}",  # nosec B608 - controlled query construction
                params,
            )
            completed_loops = cursor.fetchone()[0]

            # Cancelled loops (status = 'cancelled')
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM ralph_loops WHERE status = 'cancelled'{agent_filter}",  # nosec B608 - controlled query construction
                params,
            )
            cancelled_loops = cursor.fetchone()[0]

            # Max iterations reached loops (status = 'max_iterations')
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM ralph_loops WHERE status = 'max_iterations'{agent_filter}",  # nosec B608 - controlled query construction
                params,
            )
            max_iter_loops = cursor.fetchone()[0]

            # Paused loops (status = 'paused')
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM ralph_loops WHERE status = 'paused'{agent_filter}",  # nosec B608 - controlled query construction
                params,
            )
            paused_loops = cursor.fetchone()[0]

            # Total iterations
            if agent_id:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM ralph_iterations i
                    JOIN ralph_loops l ON i.loop_id = l.loop_id
                    WHERE l.agent_id = ?
                """,
                    (agent_id,),
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM ralph_iterations")
            total_iterations = cursor.fetchone()[0]

            # Average iterations per completed loop
            if agent_id:
                cursor = conn.execute(
                    """
                    SELECT AVG(current_iteration) FROM ralph_loops
                    WHERE status = 'completed' AND agent_id = ?
                """,
                    (agent_id,),
                )
            else:
                cursor = conn.execute("""
                    SELECT AVG(current_iteration) FROM ralph_loops
                    WHERE status = 'completed'
                """)
            avg_iterations = cursor.fetchone()[0] or 0

            return {
                "total_loops": total_loops,
                "active_loops": active_loops,
                "completed_loops": completed_loops,
                "cancelled_loops": cancelled_loops,
                "max_iterations_loops": max_iter_loops,
                "paused_loops": paused_loops,
                "total_iterations": total_iterations,
                "avg_iterations_per_loop": round(avg_iterations, 1),
            }
