"""
Notion Integration Manager — business logic for Notion pages, spec sync, CRM sync.
"""

from typing import Any

from .notion_db import NotionDatabase


class NotionManager:
    """Orchestrates Notion API calls, caching, and cross-system sync."""

    def __init__(self, db_path: str, api_key: str | None = None):
        self.db = NotionDatabase(db_path)
        self._api_key = api_key

    def _get_client(self):
        from python.helpers.notion_client import NotionClient

        return NotionClient(api_key=self._api_key)

    # ── CRUD ─────────────────────────────────────────────────────────

    async def create_page(
        self,
        database_id: str,
        title: str,
        properties: dict[str, Any] | None = None,
        content_blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        result = await client.create_page(
            parent_database_id=database_id,
            title=title,
            properties=properties,
            content_blocks=content_blocks,
        )
        result["_title"] = title
        self.db.upsert_page(result)
        return result

    async def update_page(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
        archived: bool | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        result = await client.update_page(page_id=page_id, properties=properties, archived=archived)
        self.db.upsert_page(result)
        return result

    async def query_database(
        self,
        database_id: str,
        filter_obj: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        client = self._get_client()
        pages = await client.query_database(
            database_id=database_id,
            filter_obj=filter_obj,
            sorts=sorts,
            page_size=page_size,
        )
        for page in pages:
            self.db.upsert_page(page)
        return pages

    # ── Spec sync: Linear issues with spec label → Notion pages ─────

    async def sync_specs(
        self,
        notion_database_id: str,
        linear_api_key: str | None = None,
        linear_team_id: str | None = None,
        spec_label_name: str = "Spec",
    ) -> dict[str, Any]:
        """Sync Linear issues with the Spec label → Notion spec pages."""
        sync_id = self.db.start_sync("spec_sync")
        created = 0
        skipped = 0

        try:
            from python.helpers.linear_client import LinearClient

            linear = LinearClient(api_key=linear_api_key)
            notion = self._get_client()

            # Get issues with spec label
            gql = """
            query SpecIssues($filter: IssueFilter, $first: Int) {
                issues(filter: $filter, first: $first) {
                    nodes {
                        id identifier title description
                        labels { nodes { name } }
                        project { name }
                        state { name }
                    }
                }
            }
            """
            filter_var: dict[str, Any] = {
                "labels": {"name": {"eqIgnoreCase": spec_label_name}},
            }
            if linear_team_id:
                filter_var["team"] = {"id": {"eq": linear_team_id}}

            result = await linear.execute(gql, {"filter": filter_var, "first": 50})
            issues = result.get("issues", {}).get("nodes", [])

            for issue in issues:
                # Check if already synced
                existing = self.db.get_notion_id_for_linear(issue["id"], "spec")
                if existing:
                    skipped += 1
                    continue

                # Create Notion page with issue content
                [l["name"] for l in issue.get("labels", {}).get("nodes", [])]
                page = await notion.create_page(
                    parent_database_id=notion_database_id,
                    title=f"[{issue['identifier']}] {issue['title']}",
                    properties={
                        "Status": {"select": {"name": issue.get("state", {}).get("name", "Triage")}},
                    },
                    content_blocks=[
                        {
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {"content": issue.get("description", "") or "No description"},
                                    }
                                ]
                            },
                        }
                    ],
                )

                self.db.upsert_page(page)
                self.db.add_linear_mapping(
                    notion_page_id=page["id"],
                    linear_issue_id=issue["id"],
                    linear_identifier=issue.get("identifier", ""),
                    sync_type="spec",
                )
                created += 1

            self.db.complete_sync(sync_id, created)
            return {
                "success": True,
                "created": created,
                "skipped": skipped,
                "total_issues": len(issues),
            }

        except Exception as e:
            self.db.complete_sync(sync_id, created, error=str(e))
            return {"success": False, "error": str(e), "created": created}

    # ── CRM sync: customer_lifecycle → Notion contacts database ─────

    async def sync_crm(
        self,
        notion_database_id: str,
        lifecycle_db_path: str | None = None,
    ) -> dict[str, Any]:
        """Sync customer_lifecycle data → Notion contacts database."""
        sync_id = self.db.start_sync("crm_sync")
        created = 0
        skipped = 0

        try:
            from python.helpers import files

            if not lifecycle_db_path:
                lifecycle_db_path = files.get_abs_path(
                    "./instruments/custom/customer_lifecycle/data/customer_lifecycle.db"
                )

            from instruments.custom.customer_lifecycle.lifecycle_db import CustomerLifecycleDatabase

            lifecycle_db = CustomerLifecycleDatabase(lifecycle_db_path)
            notion = self._get_client()

            # Get all customers
            conn = lifecycle_db.get_connection()
            cursor = conn.execute("SELECT customer_id, name, company, email, phone, industry, stage FROM customers")
            cols = [d[0] for d in cursor.description]
            customers = [dict(zip(cols, row)) for row in cursor.fetchall()]
            conn.close()

            for customer in customers:
                existing = self.db.get_notion_id_for_customer(customer["customer_id"])
                if existing:
                    skipped += 1
                    continue

                # Create Notion page for customer
                page = await notion.create_page(
                    parent_database_id=notion_database_id,
                    title=customer.get("name", "Unknown"),
                    properties={
                        "Company": {"rich_text": [{"text": {"content": customer.get("company", "") or ""}}]},
                        "Email": {"email": customer.get("email", "") or ""},
                        "Stage": {"select": {"name": customer.get("stage", "lead")}},
                    },
                )

                self.db.upsert_page(page)
                self.db.add_crm_mapping(
                    notion_page_id=page["id"],
                    customer_id=customer["customer_id"],
                    customer_name=customer.get("name", ""),
                )
                created += 1

            self.db.complete_sync(sync_id, created)
            return {
                "success": True,
                "created": created,
                "skipped": skipped,
                "total_customers": len(customers),
            }

        except Exception as e:
            self.db.complete_sync(sync_id, created, error=str(e))
            return {"success": False, "error": str(e), "created": created}
