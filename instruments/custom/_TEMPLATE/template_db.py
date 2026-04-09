"""
Template Database - SQLite storage for template instrument
Replace 'Template' with your instrument name throughout this file.
"""

import json
import os
import sqlite3


class TemplateDatabase:
    """
    Database operations for template instrument.

    Follows Agent Mahoo conventions:
    - Constructor takes db_path parameter
    - Uses WAL mode for better concurrency
    - Row factory for dict-like access
    - Auto-creates tables on init
    """

    def __init__(self, db_path: str):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with proper settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        cursor = conn.cursor()

        # Main items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT DEFAULT 'default',
                definition TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE(name)
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_category
            ON items(category)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_items_active
            ON items(is_active)
        """)

        conn.commit()
        conn.close()

    # ========== CRUD Operations ==========

    def save_item(self, name: str, category: str, definition: dict) -> str:
        """
        Save a new item.

        Args:
            name: Item name
            category: Item category
            definition: Full item definition as dict

        Returns:
            item_id as string
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO items (name, category, definition)
            VALUES (?, ?, ?)
        """,
            (name, category, json.dumps(definition)),
        )

        item_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return str(item_id)

    def get_item(self, item_id: str | None = None, name: str | None = None) -> dict | None:
        """
        Get item by ID or name.

        Args:
            item_id: Item ID
            name: Item name

        Returns:
            Item dict or None
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        if item_id:
            cursor.execute("SELECT * FROM items WHERE item_id = ? AND is_active = TRUE", (item_id,))
        elif name:
            cursor.execute("SELECT * FROM items WHERE name = ? AND is_active = TRUE", (name,))
        else:
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_dict(row)
        return None

    def update_item(self, item_id: str, updates: dict) -> bool:
        """
        Update an item.

        Args:
            item_id: Item ID
            updates: Dict of fields to update

        Returns:
            True if updated, False if not found
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        # Build dynamic update query
        set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
        values = []

        for key, value in updates.items():
            if key in ("name", "category"):
                set_clauses.append(f"{key} = ?")
                values.append(value)
            elif key in ("settings", "metadata", "definition"):
                # For JSON fields, we need to update the definition
                existing = self.get_item(item_id=item_id)
                if existing:
                    definition = existing.get("definition", {})
                    if isinstance(definition, str):
                        definition = json.loads(definition)
                    definition[key] = value
                    set_clauses.append("definition = ?")
                    values.append(json.dumps(definition))

        values.append(item_id)

        cursor.execute(  # nosec B608 - controlled query construction
            f"""
            UPDATE items
            SET {", ".join(set_clauses)}
            WHERE item_id = ?
        """,
            values,
        )

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return updated

    def delete_item(self, item_id: str, hard_delete: bool = False) -> bool:
        """
        Delete an item (soft delete by default).

        Args:
            item_id: Item ID
            hard_delete: If True, permanently delete

        Returns:
            True if deleted, False if not found
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        if hard_delete:
            cursor.execute("DELETE FROM items WHERE item_id = ?", (item_id,))
        else:
            cursor.execute("UPDATE items SET is_active = FALSE WHERE item_id = ?", (item_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def list_items(
        self, category: str | None = None, limit: int = 100, offset: int = 0, include_inactive: bool = False
    ) -> list[dict]:
        """
        List items with filtering.

        Args:
            category: Filter by category
            limit: Max items to return
            offset: Pagination offset
            include_inactive: Include soft-deleted items

        Returns:
            List of item dicts
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        query = "SELECT * FROM items WHERE 1=1"
        params = []

        if not include_inactive:
            query += " AND is_active = TRUE"

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_dict(row) for row in rows]

    def count_items(self, category: str | None = None) -> int:
        """
        Count items.

        Args:
            category: Filter by category

        Returns:
            Count of items
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        query = "SELECT COUNT(*) FROM items WHERE is_active = TRUE"
        params = []

        if category:
            query += " AND category = ?"
            params.append(category)

        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()

        return count

    def get_stats(self) -> dict:
        """
        Get database statistics.

        Returns:
            Stats dict
        """
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_items,
                COUNT(CASE WHEN is_active THEN 1 END) as active_items,
                COUNT(DISTINCT category) as categories
            FROM items
        """)

        row = cursor.fetchone()
        conn.close()

        return {"total_items": row["total_items"], "active_items": row["active_items"], "categories": row["categories"]}

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """Convert sqlite Row to dict with parsed JSON."""
        result = dict(row)

        # Parse JSON fields
        if "definition" in result and isinstance(result["definition"], str):
            try:
                result["definition"] = json.loads(result["definition"])
            except json.JSONDecodeError:
                pass

        # Convert item_id to string for consistency
        if "item_id" in result:
            result["item_id"] = str(result["item_id"])

        return result
