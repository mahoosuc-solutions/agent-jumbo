"""
Template Manager - Business logic for the template instrument
Replace 'Template' with your instrument name throughout this file.
"""

import json
from pathlib import Path

import jsonschema

from python.helpers.datetime_utils import isoformat_z, utc_now

from .template_db import TemplateDatabase


class TemplateManager:
    """
    Manager for template operations.

    Follows Agent Mahoo instrument conventions:
    - Constructor takes db_path for testability
    - Methods return structured dicts with 'status'/'error' keys
    - Schema validation for inputs
    - Separation from database layer
    """

    def __init__(self, db_path: str):
        """
        Initialize the template manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db = TemplateDatabase(db_path)
        self._schema_cache: dict[str, dict] = {}
        self._load_schemas()

    def _load_schemas(self) -> None:
        """Load JSON schemas for validation from schemas/ directory."""
        schema_dir = Path(__file__).parent / "schemas"
        if not schema_dir.exists():
            return

        for schema_file in schema_dir.glob("*.schema.json"):
            with open(schema_file) as f:
                schema_name = schema_file.stem.replace(".schema", "")
                self._schema_cache[schema_name] = json.load(f)

    def _validate(self, data: dict, schema_name: str) -> dict:
        """
        Validate data against a named schema.

        Args:
            data: Data to validate
            schema_name: Name of schema (without .schema.json)

        Returns:
            {"valid": True} or {"valid": False, "errors": [...]}
        """
        if schema_name not in self._schema_cache:
            return {"valid": True}  # No schema = skip validation

        try:
            jsonschema.validate(data, self._schema_cache[schema_name])
            return {"valid": True, "errors": []}
        except jsonschema.ValidationError as e:
            return {"valid": False, "errors": [str(e.message)]}

    # ========== CRUD Operations ==========

    def create_item(
        self, name: str, category: str = "default", settings: dict | None = None, metadata: dict | None = None
    ) -> dict:
        """
        Create a new item.

        Args:
            name: Item name (required)
            category: Item category
            settings: Optional configuration settings
            metadata: Optional additional metadata

        Returns:
            {"item_id": str, "status": "created"} or {"error": str}
        """
        # Validate input
        if not name or not name.strip():
            return {"error": "Name is required"}

        # Build definition
        definition = {
            "name": name.strip(),
            "category": category,
            "settings": settings or {},
            "metadata": metadata or {},
            "created_at": isoformat_z(utc_now()),
        }

        # Validate against schema if available
        validation = self._validate(definition, "item")
        if not validation.get("valid", True):
            return {"error": f"Validation failed: {validation['errors']}"}

        # Persist
        try:
            item_id = self.db.save_item(name=name, category=category, definition=definition)
            return {"item_id": item_id, "name": name, "status": "created"}
        except Exception as e:
            return {"error": f"Database error: {e!s}"}

    def get_item(self, item_id: str | None = None, name: str | None = None) -> dict:
        """
        Retrieve an item by ID or name.

        Args:
            item_id: Item ID (preferred)
            name: Item name (alternative lookup)

        Returns:
            Item data or {"error": str}
        """
        if not item_id and not name:
            return {"error": "Either item_id or name is required"}

        try:
            item = self.db.get_item(item_id=item_id, name=name)
            if not item:
                return {"error": "Item not found"}
            return item
        except Exception as e:
            return {"error": f"Database error: {e!s}"}

    def update_item(
        self,
        item_id: str,
        name: str | None = None,
        category: str | None = None,
        settings: dict | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """
        Update an existing item.

        Args:
            item_id: Item ID (required)
            name: New name (optional)
            category: New category (optional)
            settings: New settings (optional, merges with existing)
            metadata: New metadata (optional, merges with existing)

        Returns:
            {"status": "updated"} or {"error": str}
        """
        if not item_id:
            return {"error": "item_id is required"}

        # Get existing item
        existing = self.get_item(item_id=item_id)
        if "error" in existing:
            return existing

        # Merge updates
        updates = {}
        if name:
            updates["name"] = name
        if category:
            updates["category"] = category
        if settings:
            updates["settings"] = {**existing.get("settings", {}), **settings}
        if metadata:
            updates["metadata"] = {**existing.get("metadata", {}), **metadata}

        if not updates:
            return {"error": "No updates provided"}

        try:
            self.db.update_item(item_id, updates)
            return {"item_id": item_id, "status": "updated"}
        except Exception as e:
            return {"error": f"Database error: {e!s}"}

    def delete_item(self, item_id: str) -> dict:
        """
        Delete an item.

        Args:
            item_id: Item ID to delete

        Returns:
            {"status": "deleted"} or {"error": str}
        """
        if not item_id:
            return {"error": "item_id is required"}

        try:
            deleted = self.db.delete_item(item_id)
            if deleted:
                return {"item_id": item_id, "status": "deleted"}
            return {"error": "Item not found"}
        except Exception as e:
            return {"error": f"Database error: {e!s}"}

    def list_items(self, category: str | None = None, limit: int = 100, offset: int = 0) -> dict:
        """
        List items with optional filtering.

        Args:
            category: Filter by category
            limit: Maximum items to return
            offset: Pagination offset

        Returns:
            {"items": [...], "total": int} or {"error": str}
        """
        try:
            items = self.db.list_items(category=category, limit=limit, offset=offset)
            total = self.db.count_items(category=category)
            return {"items": items, "total": total, "limit": limit, "offset": offset}
        except Exception as e:
            return {"error": f"Database error: {e!s}"}

    # ========== Statistics ==========

    def get_stats(self) -> dict:
        """
        Get instrument statistics.

        Returns:
            Statistics dict with counts and metrics
        """
        try:
            return self.db.get_stats()
        except Exception as e:
            return {"error": f"Database error: {e!s}"}
